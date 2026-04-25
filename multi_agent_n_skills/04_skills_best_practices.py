"""
Skills best practices
=====================

Skills are easy to write and easy to write BADLY. The model only loads
SKILL.md when its description matches the user's task — so the
description and instructions must be precise. Common mistakes and the
fixes:

  1. VAGUE DESCRIPTIONS
        Bad : "general code helper"
        Good: "Use when refactoring a Python module to async — converts
              def → async def, requests → httpx, adds awaits."
        The description IS the trigger. Be task-shaped, not topical.

  2. ENORMOUS SKILL.md
        The whole file is loaded into context every time the skill
        triggers. Keep SKILL.md small (≈ 50-200 lines). Push reference
        docs into bundled files and tell the skill to Read them only
        when needed.

  3. DUPLICATING TOOL BEHAVIOR
        If the agent already knows how to run `pytest`, don't write a
        skill that just says "run pytest". Skills earn their keep when
        they encode non-obvious procedure.

  4. IMPLICIT STATE
        Skills don't share memory with each other or with prior turns.
        State all preconditions explicitly in SKILL.md.

  5. NO EXIT CRITERIA
        Tell the model when the skill is "done": output format, what
        success looks like. Otherwise it rambles.

  6. UNVERSIONED RESOURCES
        Bundle templates with the skill, don't fetch them from the
        internet at runtime — repeatability matters.

This script writes a "good" skill and a "bad" skill side by side and
exercises the good one. The pair is a study aid: read both SKILL.md
files after running.

Run: uv run python multi_agent_n_skills/04_skills_best_practices.py
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
SKILLS_ROOT = os.path.join(WORKSPACE, ".claude", "skills")

GOOD = """\
---
name: pr-description
description: Use when the user has a diff and wants a GitHub PR description in our team's standard format.
---

Output exactly these sections, in order, as Markdown:

## Summary
- 1-3 bullets, each <= 20 words. Focus on user-visible change.

## Why
- One short paragraph explaining the motivation.

## Test plan
- Bulleted checklist of how a reviewer can verify.

Rules:
  - Do not include a "Changes" section that lists every file.
  - Never invent test results — describe what to RUN, not what passed.
  - If the diff is empty, reply: "No changes detected."
"""

BAD = """\
---
name: helper
description: helps with stuff
---

Try to do whatever the user wants. Be helpful.
"""


def write_skills() -> None:
    for name, body in [("pr-description", GOOD), ("helper", BAD)]:
        d = os.path.join(SKILLS_ROOT, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w") as f:
            f.write(body)


async def main() -> None:
    write_skills()
    options = ClaudeAgentOptions(
        cwd=WORKSPACE,
        setting_sources=["project"],
        skills="all",
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Use the pr-description skill on this diff: 'Switched the auth "
            "middleware from JWT to session cookies; added a 30-day rolling "
            "expiry; updated 4 integration tests.'"
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
