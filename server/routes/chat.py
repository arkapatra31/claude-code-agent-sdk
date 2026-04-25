import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from adk_client.claude import ClaudeCodeAgentClient
from utils.tracing import trace_agent_stream

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _serialize(sdk_msg) -> dict | None:
    if isinstance(sdk_msg, AssistantMessage):
        blocks = []
        for block in sdk_msg.content:
            if isinstance(block, TextBlock):
                blocks.append({"type": "text", "content": block.text})
            elif isinstance(block, ToolUseBlock):
                blocks.append(
                    {"type": "tool_use", "name": block.name, "input": block.input}
                )
        return {"type": "assistant", "blocks": blocks}

    if isinstance(sdk_msg, ResultMessage):
        return {
            "type": "result",
            "result": sdk_msg.result,
            "cost": sdk_msg.total_cost_usd,
            "stop_reason": sdk_msg.stop_reason,
        }

    return None


async def _send(ws: WebSocket, payload: dict) -> None:
    await ws.send_text(json.dumps(payload))


class PermissionBroker:
    """Bridges SDK can_use_tool requests over the WebSocket to the FE."""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self._pending: dict[str, asyncio.Future] = {}

    async def request(self, tool_name: str, tool_input: dict) -> dict:
        req_id = uuid.uuid4().hex
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[req_id] = fut
        try:
            await _send(
                self.ws,
                {
                    "type": "permission_request",
                    "request_id": req_id,
                    "tool": tool_name,
                    "input": tool_input,
                },
            )
            return await fut
        finally:
            self._pending.pop(req_id, None)

    def resolve(self, req_id: str, decision: dict) -> None:
        fut = self._pending.get(req_id)
        if fut and not fut.done():
            fut.set_result(decision)

    def cancel_all(self) -> None:
        for fut in self._pending.values():
            if not fut.done():
                fut.set_result({"allow": False, "message": "session ended"})
        self._pending.clear()


@trace_agent_stream
async def _agent_turn(sdk_client, *, prompt: str):
    await sdk_client.query(prompt)
    async for msg in sdk_client.receive_response():
        yield msg


async def _stream_turn(ws: WebSocket, agent: ClaudeCodeAgentClient, prompt: str):
    sdk_client = await agent.ensure_connected()
    sid_seen: str | None = None
    async for sdk_msg in _agent_turn(
        sdk_client, model=agent.options.model, prompt=prompt
    ):
        sid = getattr(sdk_msg, "session_id", None)
        if sid and sid != sid_seen:
            sid_seen = sid
            await _send(ws, {"type": "session", "session_id": sid})
        payload = _serialize(sdk_msg)
        if payload is not None:
            await _send(ws, payload)


async def _run_prompt(ws: WebSocket, agent: ClaudeCodeAgentClient, prompt: str):
    try:
        await _stream_turn(ws, agent, prompt)
        await _send(ws, {"type": "done"})
    except asyncio.CancelledError:
        try:
            await agent.client.interrupt()
        except Exception:
            logger.exception("interrupt failed")
        await _send(ws, {"type": "interrupted"})
        raise
    except Exception as exc:
        logger.exception("agent run failed")
        await _send(ws, {"type": "error", "message": str(exc)})


def _is_running(task: asyncio.Task | None) -> bool:
    return task is not None and not task.done()


async def _handle_prompt(
    ws: WebSocket,
    agent: ClaudeCodeAgentClient,
    msg: dict,
    run_task: asyncio.Task | None,
) -> asyncio.Task | None:
    if _is_running(run_task):
        await _send(ws, {"type": "error", "message": "run already in progress"})
        return run_task

    prompt = (msg.get("prompt") or "").strip()
    if not prompt:
        await _send(ws, {"type": "error", "message": "empty prompt"})
        return run_task

    return asyncio.create_task(_run_prompt(ws, agent, prompt))


async def _handle_message(
    ws: WebSocket,
    agent: ClaudeCodeAgentClient,
    broker: PermissionBroker,
    raw: str,
    run_task: asyncio.Task | None,
) -> asyncio.Task | None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await _send(ws, {"type": "error", "message": "invalid json"})
        return run_task

    mtype = msg.get("type")

    if mtype == "prompt":
        return await _handle_prompt(ws, agent, msg, run_task)

    if mtype == "interrupt":
        if _is_running(run_task):
            run_task.cancel()
        return run_task

    if mtype == "permission_response":
        broker.resolve(
            msg.get("request_id", ""),
            {
                "allow": bool(msg.get("allow")),
                "message": msg.get("message"),
                "input": msg.get("input"),
            },
        )
        return run_task

    await _send(ws, {"type": "error", "message": f"unknown type: {mtype}"})
    return run_task


@router.websocket("/chat/ws")
async def chat_ws(ws: WebSocket):
    resume = ws.query_params.get("resume")
    await ws.accept()
    broker = PermissionBroker(ws)
    agent = ClaudeCodeAgentClient(resume=resume, on_permission_request=broker.request)
    run_task: asyncio.Task | None = None

    try:
        while True:
            raw = await ws.receive_text()
            run_task = await _handle_message(ws, agent, broker, raw, run_task)
    except WebSocketDisconnect:
        if _is_running(run_task):
            run_task.cancel()
    finally:
        broker.cancel_all()
        await agent.disconnect()
