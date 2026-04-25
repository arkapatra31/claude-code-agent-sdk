"""
Todo tracking
=============

`TodoWrite` is a built-in tool the agent uses to maintain a structured
checklist of subtasks. Each todo has a `content`, `activeForm`, and
`status` (`pending` | `in_progress` | `completed`). The model writes the
whole list each time, replacing the previous one.

Why this matters for SDK builders:

  - The TodoWrite tool calls flow through your normal tool-use stream.
    You can observe them with a PostToolUse hook (or by sniffing
    `ToolUseBlock` in the assistant messages) and mirror them into your
    own UI / Linear / database.

  - You can NUDGE the model into using todos by setting an explicit
    instruction in the system prompt — useful for multi-step jobs where
    you want progress visibility.

This script subscribes to TodoWrite events and prints the latest list
each time it changes.

Run: uv run python advanced_patterns/06_todo_tracking.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PostToolUseHookInput,
    ResultMessage,
    TextBlock,
)


async def on_todo_write(payload: PostToolUseHookInput, _tid, _ctx) -> dict:
    todos = payload["tool_input"].get("todos", [])
    print("\n[todos]")
    for t in todos:
        marker = {"completed": "[x]", "in_progress": "[~]", "pending": "[ ]"}.get(
            t.get("status", "pending"), "[?]"
        )
        print(f"  {marker} {t.get('content', '')}")
    return {}


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt=(
            "For multi-step jobs, ALWAYS use the TodoWrite tool to plan "
            "subtasks up front and update statuses as you go. Be explicit."
        ),
        allowed_tools=["TodoWrite", "Read"],
        permission_mode="bypassPermissions",
        hooks={
            "PostToolUse": [HookMatcher(matcher="TodoWrite", hooks=[on_todo_write])],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Plan how you'd refactor a monolith into 3 services. "
            "Track the plan as todos and walk through them."
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
