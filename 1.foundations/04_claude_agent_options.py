"""
ClaudeAgentOptions
==================

The single config object passed to `query()` or `ClaudeSDKClient`. Every
behavior knob lives here. The most-used fields:

  Identity & prompting
    system_prompt: str | {"type":"preset","preset":"claude_code","append":"..."}
    model: str                       # e.g. "claude-opus-4-7", "claude-sonnet-4-6"

  Tools & permissions
    allowed_tools: list[str]         # e.g. ["Read","Write","Edit","Bash"]
    disallowed_tools: list[str]
    permission_mode: "default" | "acceptEdits" | "plan" | "bypassPermissions"
    can_use_tool: callable           # programmatic permission gate
    hooks: dict[event, list[HookMatcher]]

  Filesystem & shell
    cwd: str | Path                  # working directory for tools
    add_dirs: list[Path]             # extra readable dirs
    env: dict[str, str]              # extra env for the subprocess

  Session behavior
    resume: str                      # session_id to continue
    continue_conversation: bool      # auto-resume most recent
    fork_session: bool               # branch from resumed session
    max_turns: int
    include_partial_messages: bool   # enable StreamEvent deltas
    setting_sources: list["user"|"project"|"local"]   # default: []

  MCP servers & sub-agents
    mcp_servers: dict[str, McpServerConfig]
    agents: dict[str, AgentDefinition]

Run: uv run python foundations/04_claude_agent_options.py
"""

import os
from pathlib import Path

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt="You are a precise assistant. Reply in <= 2 sentences.",
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        allowed_tools=["Read", "Glob"],
        permission_mode="acceptEdits",
        cwd=str(Path(__file__).resolve().parent),
        max_turns=4,
        include_partial_messages=False,
        setting_sources=[],  # ignore CLAUDE.md / settings.json
    )


async def main() -> None:
    opts = build_options()
    print(f"model={opts.model} cwd={opts.cwd} tools={opts.allowed_tools}")

    async for msg in query(
        prompt="List the .py files in the current working directory.",
        options=opts,
    ):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print("TextBlock:", end=" ")
                    print(b.text.strip())
        elif isinstance(msg, ResultMessage):
            print("Result:", msg.result)
            print(f"[turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
