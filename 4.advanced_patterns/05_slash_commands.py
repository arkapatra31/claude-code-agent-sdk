"""
Slash commands
==============

Slash commands are short, named prompts the user can trigger with
`/<name>` from the input line. In Claude Code they're stored as Markdown
files under `.claude/commands/<name>.md` (project) or
`~/.claude/commands/<name>.md` (user). The SDK picks them up
automatically when you opt into the relevant `setting_sources`.

File format:

    ---
    description: One-line summary shown in the picker.
    ---
    The body of the command — this becomes the user prompt.
    You can reference $ARGUMENTS to substitute whatever the user typed
    after the slash command.

This script:
  1. Writes a `.claude/commands/summarize.md` slash command into the
     working dir.
  2. Starts a session with `setting_sources=["project"]` so the SDK
     loads it.
  3. Invokes it as if the user typed `/summarize <text>`.

Run: uv run python advanced_patterns/05_slash_commands.py
"""

import os

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

WORKSPACE = os.path.abspath("./_sandbox")
COMMANDS_DIR = os.path.join(WORKSPACE, ".claude", "commands")

SUMMARIZE_CMD = """\
---
description: Summarize the supplied text in one sentence.
---
Summarize the following in exactly one sentence, no preamble:

$ARGUMENTS
"""


def write_command() -> None:
    os.makedirs(COMMANDS_DIR, exist_ok=True)
    with open(os.path.join(COMMANDS_DIR, "summarize.md"), "w") as f:
        f.write(SUMMARIZE_CMD)


async def main() -> None:
    write_command()
    options = ClaudeAgentOptions(
        cwd=WORKSPACE,
        setting_sources=["project"],  # required for the SDK to load .claude/
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options) as client:
        # Trigger the slash command exactly as a user would.
        await client.query(
            "/summarize The Claude Agent SDK lets you embed Claude as an "
            "autonomous agent inside Python apps with tool use, hooks, "
            "permissions, and multi-turn sessions."
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip())
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
