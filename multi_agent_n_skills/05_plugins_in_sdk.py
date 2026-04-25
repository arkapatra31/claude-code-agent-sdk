"""
Plugins in SDK
==============

A plugin is a directory bundle the SDK loads as a single unit, exposing
some combination of:

  - skills/      Agent skills (see 03_agent_skills_sdk.py)
  - commands/    Slash commands
  - agents/      Subagent definitions (Markdown frontmatter format)
  - hooks/       Hook scripts wired in via the plugin manifest

You point the SDK at one or more plugin directories with the `plugins`
option:

    ClaudeAgentOptions(
        plugins=[{"type": "local", "path": "/abs/path/to/plugin"}],
    )

Plugin layout:

    my-plugin/
      plugin.json        # manifest: name, version, description
      skills/
        <name>/SKILL.md
      commands/
        <name>.md
      agents/
        <name>.md

Why plugins instead of `.claude/` files in the project?

  - SHIPPABLE: one path → distributable to teammates.
  - SCOPED: pull a plugin in for one session, drop it in another.
  - VERSIONED: tag a plugin directory and bump it like a library.

This script generates a tiny local plugin and loads it at runtime.

Run: uv run python multi_agent_n_skills/05_plugins_in_sdk.py
"""

import json
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
PLUGIN = os.path.join(WORKSPACE, "plugins", "release-tools")

MANIFEST = {
    "name": "release-tools",
    "version": "0.1.0",
    "description": "Helpers for cutting releases — changelog, version bumps.",
}

CHANGELOG_SKILL = """\
---
name: changelog
description: Use when asked to draft a CHANGELOG entry for a new version.
---

Output a Keep-A-Changelog style block:

  ## [vX.Y.Z] - YYYY-MM-DD
  ### Added / Changed / Fixed
  - bullet (<= 18 words each)

Group bullets under the right heading; omit empty headings.
"""

BUMP_COMMAND = """\
---
description: Suggest the next semver version given the change list.
---
Given the following description of changes, output ONLY the next semver
version (no prose):

$ARGUMENTS
"""


def scaffold_plugin() -> None:
    os.makedirs(os.path.join(PLUGIN, "skills", "changelog"), exist_ok=True)
    os.makedirs(os.path.join(PLUGIN, "commands"), exist_ok=True)
    with open(os.path.join(PLUGIN, "plugin.json"), "w") as f:
        json.dump(MANIFEST, f, indent=2)
    with open(os.path.join(PLUGIN, "skills", "changelog", "SKILL.md"), "w") as f:
        f.write(CHANGELOG_SKILL)
    with open(os.path.join(PLUGIN, "commands", "bump.md"), "w") as f:
        f.write(BUMP_COMMAND)


async def main() -> None:
    scaffold_plugin()
    options = ClaudeAgentOptions(
        cwd=WORKSPACE,
        plugins=[{"type": "local", "path": PLUGIN}],
        skills="all",
        setting_sources=["project"],
        permission_mode="bypassPermissions",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Use the changelog skill for v1.4.0 with these changes: "
            "added retry/backoff; fixed a Windows path bug; refactored the auth module."
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
