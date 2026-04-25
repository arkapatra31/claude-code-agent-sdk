import asyncio
import logging
import os
from typing import Awaitable, Callable

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
)
from dotenv import load_dotenv

from adk_client.hooks import sensitive_file_guard
from adk_client.prompt import Prompts

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


PermissionRequester = Callable[[str, dict], Awaitable[dict]]


def _build_options(
    *,
    resume: str | None = None,
    can_use_tool=None,
) -> ClaudeAgentOptions:
    kwargs = dict(
        system_prompt=Prompts.SYSTEMPROMPT,
        model=os.getenv("ANTHROPIC_MODEL"),
        permission_mode="default",
        include_partial_messages=True,
        resume=resume,
        allowed_tools=[
            "Read",
            "Write",
            "Edit",
            "AskUserQuestion",
            "WebSearch",
            "WebFetch",
        ],
        hooks={"PreToolUse": [HookMatcher(hooks=[sensitive_file_guard])]},
    )
    if can_use_tool is not None:
        kwargs["can_use_tool"] = can_use_tool
    return ClaudeAgentOptions(**kwargs)


class ClaudeCodeAgentClient:
    """One agent client per WebSocket connection — owns its own SDK session."""

    def __init__(
        self,
        resume: str | None = None,
        on_permission_request: PermissionRequester | None = None,
    ):
        self._on_permission_request = on_permission_request
        self.options = _build_options(
            resume=resume,
            can_use_tool=self._can_use_tool if on_permission_request else None,
        )
        self.client = ClaudeSDKClient(options=self.options)
        self._connected = False
        self._connect_lock = asyncio.Lock()
        logger.info(
            "ClaudeCodeAgentClient initialized model=%s resume=%s ask=%s",
            self.options.model,
            resume,
            on_permission_request is not None,
        )

    async def _can_use_tool(self, tool_name: str, tool_input: dict, _context) -> dict:
        if self._on_permission_request is None:
            return {"behavior": "allow", "updatedInput": tool_input}
        try:
            decision = await self._on_permission_request(tool_name, tool_input)
        except Exception:
            logger.exception("permission request failed")
            return {"behavior": "deny", "message": "permission bridge error"}

        if decision.get("allow"):
            return {
                "behavior": "allow",
                "updatedInput": decision.get("input", tool_input),
            }
        return {
            "behavior": "deny",
            "message": decision.get("message", "denied by user"),
        }

    async def ensure_connected(self) -> ClaudeSDKClient:
        if self._connected:
            return self.client
        async with self._connect_lock:
            if not self._connected:
                await self.client.connect()
                self._connected = True
        return self.client

    async def disconnect(self) -> None:
        if not self._connected:
            return
        try:
            await self.client.disconnect()
        except Exception:
            logger.exception("agent disconnect failed")
        self._connected = False
