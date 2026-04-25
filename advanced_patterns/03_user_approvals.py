"""
User approvals
==============

Sometimes a policy can't be decided in code — a human has to look at the
proposed action and say yes or no. The SDK lets you turn `can_use_tool`
into an approval prompt by `await`-ing user input inside the callback.

Patterns:

  - Auto-approve "safe" tools (Read, Grep) for flow.
  - Prompt the operator on "risky" tools (Bash, Write, Edit).
  - Remember decisions for the rest of the session via a small cache —
    so the operator doesn't get prompted twice for the same command.

In production you'd swap `input()` for a webhook, Slack approval, or a
queued review UI. The shape of the callback is identical.

Run: uv run python advanced_patterns/03_user_approvals.py
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

SAFE_TOOLS = {"Read", "Grep", "Glob"}
RISKY_TOOLS = {"Bash", "Write", "Edit"}

_remembered: dict[str, bool] = {}


def _key(tool: str, tool_input: dict) -> str:
    if tool == "Bash":
        return f"Bash::{tool_input.get('command', '')}"
    if tool in {"Write", "Edit"}:
        return f"{tool}::{tool_input.get('file_path', '')}"
    return tool


async def ask_human(tool: str, tool_input: dict) -> bool:
    """Block on operator input. Returns True iff approved."""
    print("\n" + "=" * 60)
    print(f"APPROVAL NEEDED: {tool}")
    for k, v in tool_input.items():
        s = str(v)
        print(f"  {k}: {s if len(s) < 200 else s[:200] + '…'}")
    # `to_thread.run_sync` keeps the event loop responsive while we wait.
    answer = await anyio.to_thread.run_sync(lambda: input("approve? [y/N/always] ").strip().lower())
    return answer in {"y", "yes", "always"}


async def can_use_tool(tool_name: str, tool_input: dict, _ctx) -> dict:
    if tool_name in SAFE_TOOLS:
        return {"behavior": "allow", "updatedInput": tool_input}

    if tool_name in RISKY_TOOLS:
        key = _key(tool_name, tool_input)
        if key in _remembered:
            decision = _remembered[key]
        else:
            decision = await ask_human(tool_name, tool_input)
            _remembered[key] = decision
        if decision:
            return {"behavior": "allow", "updatedInput": tool_input}
        return {"behavior": "deny", "message": "operator declined"}

    return {"behavior": "deny", "message": f"{tool_name} not permitted"}


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="You may use Read freely. Bash and Write require operator approval.",
        allowed_tools=["Read", "Bash", "Write"],
        permission_mode="default",
        can_use_tool=can_use_tool,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Show the README size with `wc -c README.md`, then list files with `ls`.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:200])
                    elif isinstance(b, ToolUseBlock):
                        print(f"tool: {b.name} {str(b.input)[:80]}")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
