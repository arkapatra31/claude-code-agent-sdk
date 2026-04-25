"""
In-process MCP servers
======================

`create_sdk_mcp_server(name, version, tools)` packages a list of
`@tool`-decorated functions into an MCP server that runs inside the same
Python process as your agent — no subprocess, no network, no protocol
overhead. Tools become callable as `mcp__<server_name>__<tool_name>`.

Why in-process beats remote:
  * direct function calls -> sub-millisecond latency
  * shared memory: pass DB connections, caches, ML models via closure
  * no auth / transport setup
  * trivially testable (call .handler directly)

Wiring it to the agent:
    server = create_sdk_mcp_server("calc", tools=[add, mul])
    options = ClaudeAgentOptions(
        mcp_servers={"calc": server},
        allowed_tools=["mcp__calc__add", "mcp__calc__mul"],
    )

Run: uv run python Tools_MCP/03_in_process_mcp_servers.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)


@tool("add", "Add two integers.", {"a": int, "b": int})
async def add(args: dict) -> dict:
    return {"content": [{"type": "text", "text": str(args["a"] + args["b"])}]}


@tool("mul", "Multiply two integers.", {"a": int, "b": int})
async def mul(args: dict) -> dict:
    return {"content": [{"type": "text", "text": str(args["a"] * args["b"])}]}


async def main() -> None:
    server = create_sdk_mcp_server(name="calc", version="1.0.0", tools=[add, mul])

    options = ClaudeAgentOptions(
        system_prompt="Use the calc tools to answer arithmetic questions. Show your work.",
        mcp_servers={"calc": server},
        allowed_tools=["mcp__calc__add", "mcp__calc__mul"],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("What is (12 + 7) * 3?")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip())
                    elif isinstance(b, ToolUseBlock):
                        print(f"tool_use: {b.id} {b.name} ({b.input})")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
