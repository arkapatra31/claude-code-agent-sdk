"""
Bash tool
=========

`Bash` is a built-in tool that executes shell commands inside the
agent's `cwd`. It is the most powerful — and most dangerous — built-in.

Inputs the model sends:
    {"command": "<shell command>", "description": "<short reason>", "timeout": <ms>?}

Outputs to the model:
    stdout + stderr (truncated past a limit), plus a non-zero exit
    summary if the command failed.

Safety levers (use ONE OR MORE — defense in depth):

  1. `allowed_tools` / `disallowed_tools`
        Toggle Bash on/off entirely.

  2. `permission_mode`
        "default" gates Bash through can_use_tool / user prompts.
        "bypassPermissions" runs anything (only in trusted automation).

  3. `can_use_tool`
        Programmatic gate — inspect the command string and allow/deny.
        Best place to enforce a command allowlist (e.g. only `git`,
        `ls`, `cat`).

  4. Sandbox via `cwd` + ephemeral temp dirs.

This script demos a `git`-only Bash sandbox.

Run: uv run python Tools_MCP/06_bash_tool.py
"""

import shlex

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

ALLOWED_BINARIES = {"git", "ls", "pwd", "cat"}


async def can_use_tool(tool_name: str, tool_input: dict, _ctx) -> dict:
    if tool_name != "Bash":
        return {"behavior": "allow", "updatedInput": tool_input}

    cmd = tool_input.get("command", "")
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return {"behavior": "deny", "message": "unparseable command"}

    if not argv:
        return {"behavior": "deny", "message": "empty command"}

    binary = argv[0]
    # Reject pipes, redirects, &&, ; chains by parsing first token only;
    # anything fancy will have shell metacharacters that shlex keeps as
    # part of arg-strings, so check for them defensively.
    if any(c in cmd for c in [";", "&&", "||", "|", ">", "<", "`", "$("]):
        return {"behavior": "deny", "message": "shell metacharacters not allowed"}

    if binary not in ALLOWED_BINARIES:
        return {
            "behavior": "deny",
            "message": f"binary {binary!r} not in allowlist {sorted(ALLOWED_BINARIES)}",
        }

    return {"behavior": "allow", "updatedInput": tool_input}


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="Use Bash sparingly. Only safe read-only commands are permitted.",
        allowed_tools=["Bash"],
        permission_mode="default",
        can_use_tool=can_use_tool,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Run `git status -s` to see uncommitted files, then run `rm -rf /tmp/x` "
            "(I expect that one to be denied). Report what you observed."
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


if __name__ == "__main__":
    anyio.run(main)
