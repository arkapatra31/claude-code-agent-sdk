import json
import logging

from fastapi import APIRouter, HTTPException, Query

from db.audit import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["traces"])

_JSON_COLS = ("tools_called", "request", "response")


def _row_to_dict(row) -> dict:
    d = dict(row)
    for k in _JSON_COLS:
        raw = d.get(k)
        if not raw:
            continue
        try:
            d[k] = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            pass
    return d


@router.get("/traces")
async def list_traces(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    event_type: str | None = None,
):
    sql = "SELECT * FROM audit_events"
    params: list = []
    if event_type:
        sql += " WHERE event_type = ?"
        params.append(event_type)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]

    return {"total": total, "items": [_row_to_dict(r) for r in rows]}


@router.get("/trace-by-sid/{session_id}")
async def trace_by_sid(session_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_events WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="no traces for session_id")

    return {"session_id": session_id, "items": [_row_to_dict(r) for r in rows]}
