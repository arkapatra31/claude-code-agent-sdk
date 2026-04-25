"""
Agent Skills SDK
================

A "skill" is a packaged capability the agent can invoke by name. Unlike
slash commands (which are just prompts) or tools (which are functions),
a skill is an instructions+resources bundle the model loads on demand.

Layout on disk (project-local):

    .claude/skills/
      <skill-name>/
        SKILL.md           ← required. Frontmatter + instructions.
        scripts/           ← optional helper scripts the skill uses
        templates/         ← optional templates / reference material

SKILL.md frontmatter:

    ---
    name: <skill-name>
    description: One-line trigger description — when should the agent use this?
    ---

    Body: instructions for the model on how to use the skill, including
    any tool-call recipes and links to bundled resources.

Wiring from the SDK:

    ClaudeAgentOptions(
        skills=["<skill-name>", ...]      # explicit list, OR
        skills="all",                      # load every available skill
        setting_sources=["project"],       # required to load .claude/skills/
    )

This script generates a tiny `commit-msg` skill at runtime and asks the
agent to use it.

Run: uv run python multi_agent_n_skills/03_agent_skills_sdk.py
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
SKILL_DIR = os.path.join(WORKSPACE, ".claude", "skills", "commit-msg")

SKILL_MD = """\
---
name: commit-msg
description: Convert a freeform change description into a Conventional Commits subject + body.
---

When invoked, follow this recipe:

1. Identify the change type: feat | fix | chore | refactor | docs | test.
2. Write a single subject line: `<type>(<scope>): <imperative summary>`
   - <= 72 chars, lowercase, no trailing period.
3. Add a 1-3 line body explaining the *why*, not the *what*.
4. Output ONLY the commit message — no preamble, no fences.
"""


def write_skill() -> None:
    os.makedirs(SKILL_DIR, exist_ok=True)
    with open(os.path.join(SKILL_DIR, "SKILL.md"), "w") as f:
        f.write(SKILL_MD)


async def main() -> None:
    write_skill()
    options = ClaudeAgentOptions(
        cwd=WORKSPACE,
        setting_sources=["project"],
        skills=["commit-msg"],
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Use the commit-msg skill on this change: 'Added retry with exponential "
            "backoff to the API client because flaky 503s were causing user errors.'"
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print(b.text.strip())
            elif isinstance(msg, ResultMessage):
                print(f"\n[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
