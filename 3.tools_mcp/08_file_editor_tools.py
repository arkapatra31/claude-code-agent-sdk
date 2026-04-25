"""
File / Editor tools
===================

The bread-and-butter built-ins for code work. All resolve paths against
`cwd` (and `add_dirs`).

  Read
      Inputs : {"file_path": str, "offset"?: int, "limit"?: int, "pages"?: str}
      Returns the file contents (with line numbers prefixed). Required
      to read a file BEFORE editing it.

  Write
      Inputs : {"file_path": str, "content": str}
      Creates or overwrites the file. The SDK enforces a "Read before
      Write" rule when overwriting existing files.

  Edit
      Inputs : {"file_path": str, "old_string": str, "new_string": str, "replace_all"?: bool}
      Surgical replace. `old_string` MUST match exactly once unless
      `replace_all=True`. Best for small, reviewable diffs.

  Glob
      Inputs : {"pattern": str, "path"?: str}
      Returns files matching the glob.

  Grep
      Inputs : {"pattern": str, "path"?: str, "output_mode"?: ...}
      ripgrep-style search.

Conventions the model has been trained on:
  * Prefer Edit over Write for existing files (smaller diffs).
  * Always Read first before editing.
  * Use Glob/Grep to discover before reading.

This script asks the agent to make a tiny, real edit inside a temp
sandbox so you can watch the Read -> Edit cycle.

Run: uv run python Tools_MCP/08_file_editor_tools.py
"""

import shutil
import tempfile
from pathlib import Path

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


async def main() -> None:
    sandbox = Path(tempfile.mkdtemp(prefix="editor-tools-"))
    target = sandbox / "greeting.py"
    target.write_text('def greet():\n    return "hello, world"\n')

    options = ClaudeAgentOptions(
        system_prompt="You are a careful code editor. Read before you edit.",
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
        permission_mode="acceptEdits",
        cwd=str(sandbox),
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(
                f"In greeting.py, change the returned string from 'hello, world' to "
                f"'hello, sdk'. Then read the file back and print its final contents."
            )
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            print("text:", b.text.strip()[:300])
                        elif isinstance(b, ToolUseBlock):
                            print(f"tool_use: {b.name}({b.input})")
                elif isinstance(msg, ResultMessage):
                    print(f"[done turns={msg.num_turns}]")

        print("\nfinal file on disk:\n" + target.read_text())
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    anyio.run(main)
