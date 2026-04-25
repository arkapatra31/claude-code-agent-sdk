"""
cwd & working dir
=================

`cwd` (current working directory) anchors all filesystem-relative tool
calls — Read, Write, Edit, Bash, Glob, Grep all resolve paths against it.

Two related options:
  * cwd: str | Path
        The agent's primary working dir. Tools default to this path;
        Bash commands run here.
  * add_dirs: list[Path]
        Extra directories the agent is allowed to read/edit beyond cwd.
        Useful when your repo references shared code outside the cwd.

Defaults:
  * If you omit `cwd`, the SDK uses the Python process's `os.getcwd()`.
  * The agent cannot escape `cwd ∪ add_dirs` for filesystem ops.

Best practice: pin `cwd` explicitly to make scripts location-independent
(don't rely on where the user runs them from).

Run: uv run python foundations/07_cwd_working_dir.py
"""

from pathlib import Path

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


async def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    foundations_dir = Path(__file__).resolve().parent

    options = ClaudeAgentOptions(
        system_prompt="Use tools to answer. Be brief.",
        allowed_tools=["Read", "Glob", "Bash"],
        permission_mode="acceptEdits",
        cwd=str(foundations_dir),       # agent works inside foundations/
        add_dirs=[repo_root / "sdk-patterns"],  # also allowed to read sibling
    )

    async for msg in query(
        prompt=(
            "Use Glob to list .py files in the current directory, "
            "then list .py files under ../sdk-patterns/. Report counts."
        ),
        options=options,
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(b.text.strip())
        elif isinstance(msg, ResultMessage):
            print(f"[turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
