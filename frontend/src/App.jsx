import { useState } from "react";
import Chat from "./Chat.jsx";
import Traces from "./Traces.jsx";

const TABS = [
  { id: "chat", label: "Chat" },
  { id: "traces", label: "Traces" },
];

export default function App() {
  const [tab, setTab] = useState("chat");
  const [connected, setConnected] = useState(false);

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <span className="dot" />
          <h1>CLAUDE.AGENT</h1>
          <span className="sub">{"// fastapi · ws · sqlite"}</span>
        </div>

        <div className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? "active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className={`status-pill ${connected ? "ok" : ""}`}>
          <span className="led" />
          {connected ? "online" : "offline"}
        </div>
      </div>

      <div className="panel">
        <div className="tab-pane" style={{ display: tab === "chat" ? "flex" : "none" }}>
          <Chat onConnectedChange={setConnected} />
        </div>
        {tab === "traces" && <Traces />}
      </div>
    </div>
  );
}
