"""
permission_mode
===============

Controls how the SDK handles tool calls that would mutate state
(file writes, edits, bash, etc.).

Modes:
  "default"           Prompt for permission on each sensitive tool call.
                      In SDK contexts without an interactive UI, this
                      effectively blocks unless `can_use_tool` is set.
  "acceptEdits"       Auto-approve file Read/Write/Edit operations.
                      Other dangerous tools (Bash, etc.) still gated.
  "plan"              Plan-only mode. Model can think and propose, but
                      cannot execute mutating tools. Great for review
                      or design phases.
  "bypassPermissions" Approve everything. Use ONLY in trusted
                      automation; equivalent to --dangerously-skip-
                      permissions on the CLI.

For fine-grained control, instead of (or alongside) a mode, pass
`can_use_tool=async (tool_name, tool_input, ctx) -> {"behavior": "allow"|"deny", ...}`.
This lets you allow some inputs and deny others (e.g. allow Bash for
`git status` but deny `rm -rf`).

Run: uv run python foundations/06_permission_mode.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


async def can_use_tool(tool_name: str, tool_input: dict, _ctx) -> dict:
    """Programmatic gate: allow Read freely, sandbox Bash to git only."""
    if tool_name == "Read":
        return {"behavior": "allow", "updatedInput": tool_input}
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if cmd.strip().startswith("git "):
            return {"behavior": "allow", "updatedInput": tool_input}
        return {"behavior": "deny", "message": f"Bash blocked: only git commands allowed (got: {cmd[:40]})"}
    return {"behavior": "deny", "message": f"{tool_name} not permitted"}


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="You are a helpful assistant with limited tool access.",
        allowed_tools=["Read", "Bash"],
        permission_mode="default",     # defer to can_use_tool
        can_use_tool=can_use_tool,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Run `git status` and then `rm -rf /tmp/foo` and report what happened.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print(f"text: {b.text.strip()[:200]}")
                    elif isinstance(b, ToolUseBlock):
                        print(f"tool_use: {b.name} input={b.input}")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
