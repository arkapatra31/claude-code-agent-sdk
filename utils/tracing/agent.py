import asyncio
import functools
import logging
import time
from datetime import datetime, timezone

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from db.audit import log_event

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _extract_usage(result_msg) -> tuple[int | None, int | None, int | None]:
    usage = getattr(result_msg, "usage", None)
    if not usage:
        return None, None, None
    if isinstance(usage, dict):
        get = usage.get
    else:
        get = lambda k, d=None: getattr(usage, k, d)  # noqa: E731
    inp = get("input_tokens")
    out = get("output_tokens")
    total = inp + out if inp is not None and out is not None else None
    return inp, out, total


class _Trace:
    def __init__(self):
        self.ts_start_iso: str = _now_iso()
        self.t_start: float = time.perf_counter()
        self.t_first: float | None = None
        self.tools_called: list[dict] = []
        self.response_blocks: list[dict] = []
        self.result_msg: ResultMessage | None = None
        self.session_id: str | None = None
        self.status: str = "ok"
        self.error_text: str | None = None

    def observe(self, sdk_msg) -> None:
        if self.t_first is None:
            self.t_first = time.perf_counter()
        sid = getattr(sdk_msg, "session_id", None)
        if sid and not self.session_id:
            self.session_id = sid
        if isinstance(sdk_msg, AssistantMessage):
            for block in sdk_msg.content:
                if isinstance(block, ToolUseBlock):
                    self.tools_called.append({"name": block.name, "input": block.input})
                elif isinstance(block, TextBlock):
                    self.response_blocks.append({"type": "text", "content": block.text})
        elif isinstance(sdk_msg, ResultMessage):
            self.result_msg = sdk_msg


def _persist(trace: _Trace, *, model: str | None, prompt: str) -> None:
    t_end = time.perf_counter()
    latency_ms = int((trace.t_first - trace.t_start) * 1000) if trace.t_first else None
    duration_ms = int((t_end - trace.t_start) * 1000)
    in_tok, out_tok, total_tok = (
        _extract_usage(trace.result_msg) if trace.result_msg else (None, None, None)
    )
    try:
        log_event(
            session_id=trace.session_id or "unknown",
            event_type=f"agent_query.{trace.status}",
            model=model,
            ts_start=trace.ts_start_iso,
            ts_end=_now_iso(),
            latency_ms=latency_ms,
            duration_ms=duration_ms,
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=total_tok,
            tools_called=trace.tools_called or None,
            request=prompt,
            response={
                "blocks": trace.response_blocks,
                "result": getattr(trace.result_msg, "result", None),
                "stop_reason": getattr(trace.result_msg, "stop_reason", None),
                "cost_usd": getattr(trace.result_msg, "total_cost_usd", None),
                "error": trace.error_text,
            },
        )
    except Exception:
        logger.exception("audit log_event failed")


def trace_agent_stream(fn):
    """Decorator for an async generator that yields Claude SDK messages.

    The wrapped call MUST be invoked with these keyword arguments, which the
    decorator consumes for audit context (NOT forwarded to `fn`):
        model: str | None
        prompt: str  (also forwarded to `fn` so it can issue the query)

    `session_id` is captured automatically from any SDK message that exposes it.

    Usage:
        @trace_agent_stream
        async def run_turn(sdk_client, *, prompt):
            await sdk_client.query(prompt)
            async for msg in sdk_client.receive_response():
                yield msg
    """

    @functools.wraps(fn)
    async def wrapper(*args, model: str | None, prompt: str, **kwargs):
        trace = _Trace()
        try:
            async for msg in fn(*args, prompt=prompt, **kwargs):
                trace.observe(msg)
                yield msg
        except asyncio.CancelledError:
            trace.status = "interrupted"
            raise
        except Exception as exc:
            trace.status = "error"
            trace.error_text = str(exc)
            raise
        finally:
            _persist(trace, model=model, prompt=prompt)

    return wrapper
