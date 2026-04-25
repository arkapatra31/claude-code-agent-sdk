import { useCallback, useEffect, useState } from "react";

export default function Traces() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filterSid, setFilterSid] = useState("");
  const [activeSid, setActiveSid] = useState("");
  const [expanded, setExpanded] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = activeSid
        ? `/api/trace-by-sid/${encodeURIComponent(activeSid)}`
        : `/api/traces?limit=200`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items ?? []);
      setTotal(data.total ?? data.items?.length ?? 0);
    } catch (e) {
      setError(String(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [activeSid]);

  useEffect(() => {
    load();
  }, [load]);

  function applyFilter() {
    setActiveSid(filterSid.trim());
    setExpanded(null);
  }

  function clearFilter() {
    setFilterSid("");
    setActiveSid("");
    setExpanded(null);
  }

  return (
    <div className="traces">
      <div className="traces-toolbar">
        <input
          value={filterSid}
          onChange={(e) => setFilterSid(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && applyFilter()}
          placeholder="filter by session_id…"
        />
        <button onClick={applyFilter}>Filter</button>
        <button onClick={clearFilter}>Clear</button>
        <button onClick={load} disabled={loading}>
          {loading ? "…" : "Refresh"}
        </button>
        <span style={{ color: "var(--fg-mute)", fontSize: 11 }}>
          {activeSid ? `sid=${activeSid}` : `latest · ${total} total`}
        </span>
      </div>

      {error && <div className="empty">[error] {error}</div>}

      {!error && items.length === 0 && !loading && (
        <div className="empty">// no traces</div>
      )}

      {items.length > 0 && (
        <table className="trace-table">
          <thead>
            <tr>
              <th style={{ width: 50 }}>id</th>
              <th>ts_start</th>
              <th>session</th>
              <th>event</th>
              <th>model</th>
              <th className="num">latency</th>
              <th className="num">duration</th>
              <th className="num">in</th>
              <th className="num">out</th>
              <th className="num">total</th>
              <th className="num">tools</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <Row
                key={row.id}
                row={row}
                expanded={expanded === row.id}
                onToggle={() => setExpanded(expanded === row.id ? null : row.id)}
                onSidClick={(sid) => {
                  setFilterSid(sid);
                  setActiveSid(sid);
                  setExpanded(null);
                }}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Row({ row, expanded, onToggle, onSidClick }) {
  const status = row.event_type?.split(".")[1] ?? "ok";
  const toolCount = Array.isArray(row.tools_called) ? row.tools_called.length : 0;
  const sidShort = row.session_id?.slice(0, 8) ?? "";

  return (
    <>
      <tr className={expanded ? "expanded" : ""} onClick={onToggle} style={{ cursor: "pointer" }}>
        <td className="num">{row.id}</td>
        <td>{formatTs(row.ts_start)}</td>
        <td
          className="sid"
          title={row.session_id}
          onClick={(e) => {
            e.stopPropagation();
            onSidClick(row.session_id);
          }}
        >
          {sidShort}
        </td>
        <td>
          <span className={`evt-pill ${status}`}>{row.event_type}</span>
        </td>
        <td>{row.model ?? "—"}</td>
        <td className="num">{fmtMs(row.latency_ms)}</td>
        <td className="num">{fmtMs(row.duration_ms)}</td>
        <td className="num">{row.input_tokens ?? "—"}</td>
        <td className="num">{row.output_tokens ?? "—"}</td>
        <td className="num">{row.total_tokens ?? "—"}</td>
        <td className="num">{toolCount || "—"}</td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={11} className="trace-detail">
            <h4>request</h4>
            <pre>{prettify(row.request)}</pre>
            <h4>tools_called</h4>
            <pre>{prettify(row.tools_called) || "—"}</pre>
            <h4>response</h4>
            <pre>{prettify(row.response)}</pre>
          </td>
        </tr>
      )}
    </>
  );
}

function fmtMs(v) {
  if (v == null) return "—";
  if (v < 1000) return `${v}ms`;
  return `${(v / 1000).toFixed(2)}s`;
}

function formatTs(ts) {
  if (!ts) return "—";
  return ts.replace("T", " ").replace("Z", "").slice(0, 23);
}

function prettify(v) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}
