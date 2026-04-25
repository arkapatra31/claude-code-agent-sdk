"""
Permission handling
===================

The SDK gives you THREE knobs that compose into a permission policy:

  1. `allowed_tools` / `disallowed_tools`
        Coarse switch — tool is on or off for the whole session.

  2. `permission_mode`
        Global default behavior:
          "default"           gate sensitive tools (asks via can_use_tool)
          "acceptEdits"       auto-approve Read/Write/Edit
          "plan"              read-only / planning mode
          "bypassPermissions" approve everything (trusted automation only)

  3. `can_use_tool(tool, input, ctx) -> {"behavior": "allow"|"deny", ...}`
        Fine-grained per-call gate. Inspect the actual arguments and
        return a decision. You can also rewrite the input by returning
        `updatedInput`, or persist a rule by returning
        `permissionUpdates` (see PermissionUpdate).

Layering matters: `disallowed_tools` and `permission_mode="plan"` reject
calls before `can_use_tool` even sees them. Keep the broad rules in
config and the surgical rules in `can_use_tool`.

This example: Read is always free, Write needs argument-level checks,
everything else is denied.

Run: uv run python advanced_patterns/02_permission_handling.py
"""

import os

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

WORKSPACE = os.path.abspath("./_sandbox")


async def can_use_tool(tool_name: str, tool_input: dict, _ctx) -> dict:
    if tool_name == "Read":
        return {"behavior": "allow", "updatedInput": tool_input}

    if tool_name == "Write":
        path = os.path.abspath(tool_input.get("file_path", ""))
        # Confine all writes to the sandbox dir.
        if not path.startswith(WORKSPACE + os.sep):
            return {
                "behavior": "deny",
                "message": f"writes restricted to {WORKSPACE}",
            }
        # Cap file size — refuse to overwrite huge blobs.
        if len(tool_input.get("content", "")) > 50_000:
            return {"behavior": "deny", "message": "content > 50KB rejected"}
        return {"behavior": "allow", "updatedInput": tool_input}

    return {"behavior": "deny", "message": f"{tool_name} is not permitted"}


async def main() -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    options = ClaudeAgentOptions(
        system_prompt="You have Read and Write only, scoped to the sandbox dir.",
        allowed_tools=["Read", "Write"],
        permission_mode="default",
        can_use_tool=can_use_tool,
        cwd=WORKSPACE,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            f"Write 'hello' to ./note.txt inside {WORKSPACE}, "
            "then try writing to /etc/passwd (expect deny). Report results."
        )
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
