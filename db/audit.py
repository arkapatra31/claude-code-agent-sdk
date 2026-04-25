import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "audit.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT    NOT NULL,
    event_type      TEXT    NOT NULL,
    model           TEXT,
    ts_start        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    ts_end          TEXT,
    latency_ms      INTEGER,
    duration_ms     INTEGER,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    total_tokens    INTEGER,
    tools_called    TEXT,
    request         TEXT,
    response        TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_events(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts_start ON audit_events(ts_start);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(_SCHEMA)


def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def log_event(
    *,
    session_id: str,
    event_type: str,
    model: str | None = None,
    ts_start: str | None = None,
    ts_end: str | None = None,
    latency_ms: int | None = None,
    duration_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    tools_called: Any = None,
    request: Any = None,
    response: Any = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO audit_events (
                session_id, event_type, model,
                ts_start, ts_end,
                latency_ms, duration_ms,
                input_tokens, output_tokens, total_tokens,
                tools_called, request, response
            ) VALUES (
                ?, ?, ?,
                COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                session_id,
                event_type,
                model,
                ts_start,
                ts_end,
                latency_ms,
                duration_ms,
                input_tokens,
                output_tokens,
                total_tokens,
                _to_json(tools_called),
                _to_json(request),
                _to_json(response),
            ),
        )
        return cur.lastrowid
