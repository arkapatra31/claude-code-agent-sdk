"""
Hooks (pre/post tool)
=====================

Hooks are user-supplied callbacks the SDK fires at well-defined points in
the agent loop. They are stronger than `can_use_tool` because they fire on
*every* matching event (tool start, tool end, prompt submit, stop, etc.)
and can mutate context, block actions, or just observe.

Lifecycle hook events exposed by the SDK:
    PreToolUse           Right before a tool call executes — can deny.
    PostToolUse          After a tool call completes successfully.
    PostToolUseFailure   After a tool call fails / errors.
    UserPromptSubmit     When the user sends a new turn.
    Stop / SubagentStop  When the agent (or a subagent) finishes.
    PreCompact           Before context compaction runs.
    Notification         When the CLI emits a notification.
    SubagentStart        Before a subagent spins up.
    PermissionRequest    When a permission gate fires.

Wiring: pass `hooks={event: [HookMatcher(matcher=<tool-name-regex>, hooks=[fn])]}`
to `ClaudeAgentOptions`. The `matcher` is optional — omit it to match all
tool calls for that event.

This script logs PreToolUse and PostToolUse for every Bash call, and
blocks any Bash command that touches `/etc`.

Run: uv run python advanced_patterns/01_hooks.py
"""

import time

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PostToolUseHookInput,
    PreToolUseHookInput,
    ResultMessage,
    TextBlock,
)

_started: dict[str, float] = {}


async def pre_bash(payload: PreToolUseHookInput, tool_use_id: str | None, _ctx) -> dict:
    cmd = payload["tool_input"].get("command", "")
    print(f"[hook:Pre]  Bash → {cmd[:60]}")
    if "/etc" in cmd:
        # Block by returning a permissionDecision of "deny".
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "writes to /etc are not allowed",
            }
        }
    if tool_use_id:
        _started[tool_use_id] = time.monotonic()
    return {}


async def post_bash(payload: PostToolUseHookInput, tool_use_id: str | None, _ctx) -> dict:
    elapsed = (time.monotonic() - _started.pop(tool_use_id, time.monotonic())) * 1000
    print(f"[hook:Post] Bash done in {elapsed:.0f}ms")
    return {}


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="Use Bash to run the requested commands.",
        allowed_tools=["Bash"],
        permission_mode="bypassPermissions",
        hooks={
            "PreToolUse": [HookMatcher(matcher="Bash", hooks=[pre_bash])],
            "PostToolUse": [HookMatcher(matcher="Bash", hooks=[post_bash])],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Run `echo hello`, then try `cat /etc/passwd` (expect that one to be blocked)."
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:200])
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
