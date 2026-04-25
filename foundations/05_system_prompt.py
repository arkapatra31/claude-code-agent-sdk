"""
system_prompt
=============

Three shapes are accepted by `ClaudeAgentOptions.system_prompt`:

  1. None (omit it)
       The SDK uses the model's default behavior — generic assistant,
       no Claude Code persona, no built-in tool guidance.

  2. A plain string
       Replaces the system prompt entirely. You own all instructions.
       Use this for narrow, single-purpose agents (extractors, classifiers).

  3. A preset dict
       {"type": "preset", "preset": "claude_code", "append": "..."}
       Loads the built-in Claude Code system prompt (the same one that
       powers the CLI: tool guidance, file-edit etiquette, etc.) and
       appends your additions. Use this when you want the full coding
       agent behavior plus your own rules.

Rule of thumb:
  * coding / file-editing agents -> preset "claude_code" + append
  * narrow data agents (extractors, routers) -> plain string

Run: uv run python foundations/05_system_prompt.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


PLAIN = "You are a haiku generator. Reply ONLY with a 5-7-5 haiku."

PRESET = {
    "type": "preset",
    "preset": "claude_code",
    "append": (
        "Project-specific rules:\n"
        "- Prefer minimal diffs.\n"
        "- Never write to paths under .venv/ or node_modules/.\n"
    ),
}


async def run(label: str, system_prompt, prompt: str) -> None:
    print(f"\n--- {label} ---")
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(system_prompt=system_prompt),
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(b.text.strip())
        elif isinstance(msg, ResultMessage):
            return


async def main() -> None:
    await run("plain string", PLAIN, "Topic: autumn rain.")
    await run("preset + append", PRESET, "In one sentence, what rules do you follow on this project?")


if __name__ == "__main__":
    anyio.run(main)
