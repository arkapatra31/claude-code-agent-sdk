import asyncio
import logging
import os

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
)
from dotenv import load_dotenv

from adk_client.hooks import sensitive_file_guard
from adk_client.prompt import Prompts

load_dotenv()

logger = logging.getLogger(__name__)


_PARENT_SYSTEM_PROMPT = (
    Prompts.SYSTEMPROMPT
    + "\n\nDelegate specialized work to sub-agents via the Task tool when appropriate:"
    "\n  - 'code-reviewer' for reviewing diffs and code quality"
    "\n  - 'researcher' for open-ended codebase or web research"
    "\n  - 'test-writer' for authoring unit / integration tests"
)


_SUBAGENTS: dict[str, AgentDefinition] = {
    "code-reviewer": AgentDefinition(
        description="Reviews diffs and code for correctness, security, and style.",
        prompt=(
            "You are a senior code reviewer. Review the provided diff or files "
            "for correctness, security, readability, and adherence to project "
            "conventions. Return a concise, prioritized list of findings."
        ),
        tools=["Read", "Grep", "Glob"],
    ),
    "researcher": AgentDefinition(
        description="Investigates open-ended questions across the codebase and web.",
        prompt=(
            "You are a research assistant. Investigate the question across the "
            "codebase and (when allowed) the web. Return a brief synthesis with "
            "citations to file paths or URLs."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    ),
    "test-writer": AgentDefinition(
        description="Authors unit and integration tests for target code.",
        prompt=(
            "You are a test-writing specialist. Produce focused unit or "
            "integration tests for the target code. Cover the golden path and "
            "meaningful edge cases. Match the project's existing test style."
        ),
        tools=["Read", "Write", "Edit", "Grep", "Glob"],
    ),
}


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=_PARENT_SYSTEM_PROMPT,
        model=os.getenv("ANTHROPIC_MODEL"),
        permission_mode="default",
        include_partial_messages=True,
        allowed_tools=[
            "Read",
            "Write",
            "Edit",
            "AskUserQuestion",
            "WebSearch",
            "WebFetch",
            "Task",
        ],
        hooks={"PreToolUse": [HookMatcher(hooks=[sensitive_file_guard])]},
        agents=_SUBAGENTS,
    )


class ClaudeCodeAgentSDK:
    """Singleton parent agent that orchestrates registered sub-agents."""

    _instance: "ClaudeCodeAgentSDK | None" = None

    def __init__(self) -> None:
        self.options = _build_options()
        self.client = ClaudeSDKClient(options=self.options)
        self._connected = False
        self._connect_lock = asyncio.Lock()
        logger.info(
            "ClaudeCodeAgentSDK initialized model=%s subagents=%s",
            self.options.model,
            list((self.options.agents or {}).keys()),
        )

    @classmethod
    def get_instance(cls) -> "ClaudeCodeAgentSDK":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def subagents(self) -> dict[str, AgentDefinition]:
        return self.options.agents or {}

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
            logger.exception("agent sdk disconnect failed")
        self._connected = False


agent_sdk = ClaudeCodeAgentSDK.get_instance()

__all__ = ["ClaudeCodeAgentSDK", "agent_sdk"]
