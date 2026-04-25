"""
Remote MCP servers
==================

Beyond in-process SDK servers, the agent can connect to any MCP server
speaking the standard protocol. Three transport flavors are supported
via `mcp_servers` config:

  1. stdio
        Spawn a local subprocess and speak MCP over stdin/stdout.
        Best for filesystem-bound tools (filesystem MCP, sqlite MCP).

        {"type": "stdio",
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
         "env": {...}}

  2. sse
        Connect to a long-lived SSE endpoint.

        {"type": "sse",
         "url": "https://mcp.example.com/sse",
         "headers": {"Authorization": "Bearer ..."}}

  3. http
        Plain HTTP MCP endpoint.

        {"type": "http",
         "url": "https://mcp.example.com/",
         "headers": {"Authorization": "Bearer ..."}}

Tools surface as `mcp__<server_name>__<tool_name>` just like SDK servers.
You must list the qualified names in `allowed_tools` (or rely on
`permission_mode`) for the model to actually call them.

This script just shows the config wiring — it does NOT spin up a real
remote server, so we register a stdio server pointed at the public
filesystem MCP, gated to a tmp dir. Comment out / replace if your
environment has no `npx`.

Run: uv run python Tools_MCP/04_remote_mcp_servers.py
"""

import os
import tempfile

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


def build_options() -> ClaudeAgentOptions:
    sandbox = tempfile.mkdtemp(prefix="mcp-fs-")
    # write a sample file the agent can read via the remote MCP fs server
    with open(os.path.join(sandbox, "hello.txt"), "w") as f:
        f.write("hello from remote MCP!\n")

    mcp_servers = {
        # ---- stdio: local subprocess speaking MCP ----
        "fs": {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", sandbox],
        },
        # ---- sse / http examples (commented; require a real endpoint) ----
        # "company": {
        #     "type": "sse",
        #     "url": "https://mcp.example.com/sse",
        #     "headers": {"Authorization": f"Bearer {os.environ['MCP_TOKEN']}"},
        # },
        # "search": {
        #     "type": "http",
        #     "url": "https://mcp.example.com/",
        #     "headers": {"Authorization": f"Bearer {os.environ['MCP_TOKEN']}"},
        # },
    }

    return ClaudeAgentOptions(
        system_prompt="Use mcp__fs tools to inspect the sandbox.",
        mcp_servers=mcp_servers,
        # we don't know the exact tool names ahead of time; allow the whole server
        allowed_tools=["mcp__fs"],
        permission_mode="acceptEdits",
    )


async def main() -> None:
    options = build_options()

    async with ClaudeSDKClient(options=options) as client:
        await client.query("List the files available, then read hello.txt and echo its contents.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:200])
                    elif isinstance(b, ToolUseBlock):
                        print(f"tool_use: {b.name}({b.input})")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns} error={msg.is_error}]")


if __name__ == "__main__":
    anyio.run(main)
