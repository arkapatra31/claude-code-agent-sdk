"""
Modifying system prompts
========================

The `system_prompt` option in `ClaudeAgentOptions` accepts three shapes:

  1. A plain string
        Replaces Claude Code's default system prompt entirely.
        You own the whole behavior contract.

  2. A SystemPromptPreset
        `{"type": "preset", "preset": "claude_code", "append": "..."}`
        Keeps the built-in agent prompt and APPENDS your text. Good for
        layering project-specific rules on top of standard tool/file
        behavior.

  3. A SystemPromptFile
        `{"type": "file", "path": "<path-to-md>"}`
        Loads the prompt from disk — handy for long, version-controlled
        prompts, or for sharing one prompt across many entrypoints.

Choosing:
  - Building a vertical agent that doesn't need Claude Code's
    file-editor mannerisms? Use a plain string.
  - Building tooling on top of Claude Code (lint helper, code assistant,
    etc.)? Use the preset+append form.
  - Long prompt + want diffs in PRs? Use the file form.

This script demos all three in sequence.

Run: uv run python advanced_patterns/07_modifying_system_prompts.py
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
PROMPT_PATH = os.path.join(WORKSPACE, "agent_prompt.md")


async def run_once(label: str, options: ClaudeAgentOptions, prompt: str) -> None:
    print(f"\n=== {label} ===")
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print(b.text.strip())
            elif isinstance(msg, ResultMessage):
                print(f"[turns={msg.num_turns}]")


async def main() -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    with open(PROMPT_PATH, "w") as f:
        f.write(
            "You are 'haiku-bot'. Reply to ANY user input with a single haiku "
            "(5-7-5 syllables). No preamble."
        )

    # 1. Plain string — fully replaces the default.
    await run_once(
        "plain string",
        ClaudeAgentOptions(
            system_prompt="You are a pirate. End every message with 'arr!'.",
        ),
        "Greet me.",
    )

    # 2. Preset + append — keep Claude Code defaults, layer rules on top.
    await run_once(
        "preset + append",
        ClaudeAgentOptions(
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": "Always start replies with the marker [layered].",
            },
        ),
        "Say hi.",
    )

    # 3. From file.
    await run_once(
        "from file",
        ClaudeAgentOptions(system_prompt={"type": "file", "path": PROMPT_PATH}),
        "Spring rain.",
    )


if __name__ == "__main__":
    anyio.run(main)
