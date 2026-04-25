import { useEffect, useRef, useState } from "react";

const WS_URL = `${
  globalThis.location.protocol === "https:" ? "wss" : "ws"
}://${globalThis.location.host}/api/chat/ws`;

let _localIdSeq = 0;
const newLocalId = () => `c${++_localIdSeq}`;

function previewWords(text, n = 12) {
  const words = (text ?? "").trim().split(/\s+/).slice(0, n);
  const truncated = words.join(" ");
  return truncated + (truncated.length < (text ?? "").trim().length ? "…" : "");
}

export default function Chat({ onConnectedChange }) {
  const [chats, setChats] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [liveId, setLiveId] = useState(null);
  const [wsEpoch, setWsEpoch] = useState(0);
  const [resumeSid, setResumeSid] = useState(null);

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [pendingPerm, setPendingPerm] = useState(null);

  const wsRef = useRef(null);
  const liveIdRef = useRef(null);
  const resumeSidRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    liveIdRef.current = liveId;
  }, [liveId]);

  useEffect(() => {
    resumeSidRef.current = resumeSid;
  }, [resumeSid]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/traces?limit=500");
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;

        const bySid = new Map();
        for (const item of [...(data.items ?? [])].reverse()) {
          const sid = item.session_id;
          if (!sid || sid === "unknown") continue;
          if (!bySid.has(sid)) {
            bySid.set(sid, {
              id: newLocalId(),
              sessionId: sid,
              firstPrompt: typeof item.request === "string" ? item.request : "",
              messages: [],
              hydrated: false,
            });
          }
        }

        const ordered = [...bySid.values()].reverse();
        setChats((prev) => {
          const liveSids = new Set(
            prev.filter((c) => c.sessionId).map((c) => c.sessionId)
          );
          return [...prev, ...ordered.filter((c) => !liveSids.has(c.sessionId))];
        });
      } catch (err) {
        console.error("failed to load past chats", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    onConnectedChange?.(connected);
  }, [connected, onConnectedChange]);

  useEffect(() => {
    let cancelled = false;
    let ws = null;
    let reconnectTimer = null;
    let retry = 0;

    const open = () => {
      if (cancelled) return;
      const sid = resumeSidRef.current;
      const url = sid ? `${WS_URL}?resume=${encodeURIComponent(sid)}` : WS_URL;
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        retry = 0;
        setConnected(true);
      };
      ws.onclose = () => {
        setConnected(false);
        setBusy(false);
        if (cancelled) return;
        const delay = Math.min(1000 * 2 ** retry, 8000);
        retry += 1;
        reconnectTimer = setTimeout(open, delay);
      };
      ws.onerror = () => setConnected(false);
      ws.onmessage = (evt) => {
        try {
          applyEvent(JSON.parse(evt.data));
        } catch (err) {
          console.error("bad message", err, evt.data);
        }
      };
    };

    const initial = setTimeout(open, 0);

    return () => {
      cancelled = true;
      clearTimeout(initial);
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [wsEpoch]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chats, activeId]);

  function mutateChat(chatId, fn) {
    if (!chatId) return;
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== chatId) return c;
        const next = { ...c, messages: [...c.messages] };
        fn(next);
        return next;
      })
    );
  }

  function mutateLastAssistant(chatId, fn) {
    mutateChat(chatId, (chat) => {
      const last = { ...chat.messages[chat.messages.length - 1] };
      last.blocks = [...(last.blocks ?? [])];
      last.meta = { ...(last.meta ?? {}) };
      fn(last);
      chat.messages[chat.messages.length - 1] = last;
    });
  }

  function applyEvent(payload) {
    const chatId = liveIdRef.current;

    if (payload.type === "session") {
      if (chatId) {
        setChats((prev) =>
          prev.map((c) => (c.id === chatId ? { ...c, sessionId: payload.session_id } : c))
        );
        setResumeSid(payload.session_id);
        resumeSidRef.current = payload.session_id;
      }
      return;
    }

    if (payload.type === "permission_request") {
      setPendingPerm({
        request_id: payload.request_id,
        tool: payload.tool,
        input: payload.input,
      });
      return;
    }

    if (payload.type === "done" || payload.type === "interrupted") {
      setBusy(false);
      if (payload.type === "interrupted" && chatId) {
        mutateLastAssistant(chatId, (m) =>
          m.blocks.push({ type: "text", content: "— interrupted —" })
        );
      }
      return;
    }

    if (!chatId) return;

    if (payload.type === "assistant") {
      mutateLastAssistant(chatId, (m) => m.blocks.push(...payload.blocks));
    } else if (payload.type === "result") {
      mutateLastAssistant(chatId, (m) => {
        if (payload.result) m.blocks.push({ type: "text", content: payload.result });
        m.meta.cost = payload.cost;
        m.meta.stop_reason = payload.stop_reason;
      });
    } else if (payload.type === "error") {
      mutateLastAssistant(chatId, (m) =>
        m.blocks.push({ type: "text", content: `[error] ${payload.message}` })
      );
      setBusy(false);
    }
  }

  async function hydrateChat(chat) {
    if (chat.hydrated || !chat.sessionId) return;
    try {
      const res = await fetch(
        `/api/trace-by-sid/${encodeURIComponent(chat.sessionId)}`
      );
      if (!res.ok) return;
      const data = await res.json();
      const messages = [];
      for (const row of data.items ?? []) {
        if (row.request) {
          messages.push({ role: "user", content: row.request });
        }
        const blocks = row.response?.blocks ?? [];
        const finalText = row.response?.result;
        const assistantBlocks = [...blocks];
        if (finalText) assistantBlocks.push({ type: "text", content: finalText });
        for (const tc of row.tools_called ?? []) {
          assistantBlocks.push({ type: "tool_use", name: tc.name, input: tc.input });
        }
        messages.push({
          role: "assistant",
          blocks: assistantBlocks,
          meta: { cost: row.response?.cost_usd, stop_reason: row.response?.stop_reason },
        });
      }
      setChats((prev) =>
        prev.map((c) => (c.id === chat.id ? { ...c, messages, hydrated: true } : c))
      );
    } catch (err) {
      console.error("failed to hydrate chat", err);
    }
  }

  function selectChat(chat) {
    setActiveId(chat.id);
    if (!chat.hydrated && chat.id !== liveId) hydrateChat(chat);
    if (chat.sessionId && chat.id !== liveId) {
      setResumeSid(chat.sessionId);
      resumeSidRef.current = chat.sessionId;
      setLiveId(chat.id);
      liveIdRef.current = chat.id;
      setBusy(false);
      setWsEpoch((n) => n + 1);
    }
  }

  function startNewChat() {
    setLiveId(null);
    liveIdRef.current = null;
    setActiveId(null);
    setResumeSid(null);
    resumeSidRef.current = null;
    setBusy(false);
    setWsEpoch((n) => n + 1);
  }

  function send() {
    const prompt = input.trim();
    const ws = wsRef.current;
    if (!prompt || busy || !ws || ws.readyState !== WebSocket.OPEN) return;

    let chatId = liveId;
    if (!chatId) {
      chatId = newLocalId();
      const newChat = {
        id: chatId,
        sessionId: null,
        firstPrompt: prompt,
        messages: [],
      };
      setChats((prev) => [newChat, ...prev]);
      setLiveId(chatId);
      liveIdRef.current = chatId;
    }
    setActiveId(chatId);

    mutateChat(chatId, (c) => {
      c.messages.push({ role: "user", content: prompt });
      c.messages.push({ role: "assistant", blocks: [], meta: {} });
    });

    setInput("");
    setBusy(true);
    ws.send(JSON.stringify({ type: "prompt", prompt }));
  }

  function respondPermission(allow) {
    const perm = pendingPerm;
    const ws = wsRef.current;
    if (!perm || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(
      JSON.stringify({
        type: "permission_response",
        request_id: perm.request_id,
        allow,
      })
    );
    setPendingPerm(null);
  }

  function interrupt() {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "interrupt" }));
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  const activeChat = chats.find((c) => c.id === activeId) ?? null;
  const showLive = busy && activeId === liveId;
  const lastAssistant = activeChat?.messages?.[activeChat.messages.length - 1];
  const lastTool =
    lastAssistant?.role === "assistant"
      ? [...(lastAssistant.blocks ?? [])]
          .reverse()
          .find((b) => b.type === "tool_use")
      : null;

  return (
    <div className="chat-layout">
      <aside className="chat-sidebar">
        <div className="chat-sidebar-head">
          <span>chats</span>
          <button onClick={startNewChat}>+ New</button>
        </div>
        <div className="chat-list">
          {chats.length === 0 && <div className="chat-empty">// no chats yet</div>}
          {chats.map((c) => (
            <div
              key={c.id}
              className={`chat-item ${c.id === activeId ? "active" : ""} ${
                c.id === liveId ? "live" : ""
              }`}
              onClick={() => selectChat(c)}
            >
              <div className="preview">{previewWords(c.firstPrompt)}</div>
              <div className="sid">{c.sessionId ?? "session: pending…"}</div>
            </div>
          ))}
        </div>
      </aside>

      <section className={`chat-main ${!activeChat ? "centered" : ""}`}>
        <div className="chat-scroll">
          {!activeChat && <EmptyStage connected={connected} />}
          {activeChat && (
            <div className="chat">
              <div className="messages">
                {activeChat.messages.map((m, i) => (
                  <Message key={i} msg={m} />
                ))}
                {showLive && <LiveIndicator tool={lastTool} />}
                <div ref={scrollRef} />
              </div>
            </div>
          )}
        </div>

        <div className="composer">
          <div className="composer-inner">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="› ask claude…"
              disabled={!connected}
            />
            {busy ? (
              <button className="stop" onClick={interrupt}>
                Stop
              </button>
            ) : (
              <button onClick={send} disabled={!connected || !input.trim()}>
                Send
              </button>
            )}
          </div>
        </div>
      </section>

      {pendingPerm && (
        <PermissionModal
          tool={pendingPerm.tool}
          input={pendingPerm.input}
          onAllow={() => respondPermission(true)}
          onDeny={() => respondPermission(false)}
        />
      )}
    </div>
  );
}

function PermissionModal({ tool, input, onAllow, onDeny }) {
  return (
    <div className="perm-overlay" role="dialog" aria-modal="true">
      <div className="perm-modal">
        <div className="perm-head">tool permission</div>
        <div className="perm-body">
          <div className="perm-row">
            <span className="perm-key">tool</span>
            <span className="perm-val">{tool}</span>
          </div>
          <div className="perm-row">
            <span className="perm-key">input</span>
            <pre className="perm-input">{JSON.stringify(input, null, 2)}</pre>
          </div>
        </div>
        <div className="perm-actions">
          <button className="perm-deny" onClick={onDeny}>
            Deny
          </button>
          <button className="perm-allow" onClick={onAllow}>
            Allow
          </button>
        </div>
      </div>
    </div>
  );
}

function LiveIndicator({ tool }) {
  return (
    <div className="live-indicator">
      <span className="dots">
        <span />
        <span />
        <span />
      </span>
      <span className="label">
        {tool ? (
          <>
            invoking <span className="tool">{tool.name}</span>
          </>
        ) : (
          "thinking"
        )}
      </span>
    </div>
  );
}

function EmptyStage({ connected }) {
  return (
    <div className="empty-stage">
      <div className="radar">
        <div className="ring" />
        <div className="ring" />
        <div className="ring" />
        <div className="scan" />
        <div className="core" />
      </div>
      <div className="label">
        claude.agent
        <span className="cursor" />
      </div>
      <div className="meta">
        {connected ? "ready · awaiting input" : "establishing socket…"}
      </div>
      <div className="ticker">
        <span>fastapi</span>
        <span>websocket</span>
        <span>sqlite</span>
        <span>tracing</span>
      </div>
    </div>
  );
}

function Message({ msg }) {
  if (msg.role === "user") {
    return (
      <div className="msg user">
        <div className="msg-head">user</div>
        <div className="msg-body">{msg.content}</div>
      </div>
    );
  }
  return (
    <div className="msg assistant">
      <div className="msg-head">assistant</div>
      <div className="msg-body">
        {(msg.blocks ?? []).map((b, i) =>
          b.type === "text" ? (
            <div key={i}>{b.content}</div>
          ) : (
            <details key={i} className="tool">
              <summary>tool · {b.name}</summary>
              <pre>{JSON.stringify(b.input, null, 2)}</pre>
            </details>
          )
        )}
        {msg.meta?.cost != null && (
          <div className="meta">
            cost ${Number(msg.meta.cost).toFixed(6)} · stop:{" "}
            {msg.meta.stop_reason}
          </div>
        )}
      </div>
    </div>
  );
}
