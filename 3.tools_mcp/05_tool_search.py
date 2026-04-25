"""
Tool search
===========

When you wire many MCP servers (each with many tools), loading every
schema into the model's context is wasteful — and Claude only needs a
handful per turn. The harness solves this with **deferred tools**:

  * Tool *names* are advertised to the model up front (cheap).
  * The full JSON schemas are NOT loaded until needed.
  * The model calls the built-in `ToolSearch` tool with a query like
        "select:Read,Edit"        (load these specific tools by name)
        "filesystem read"          (keyword search; top N matches)
        "+slack send"              (require 'slack', rank by 'send')
  * The harness streams back the matched schemas inline; the model
    can then invoke them on the next turn.

You don't typically call ToolSearch yourself — you just enable it and
let the model self-discover. Enable by adding "ToolSearch" to
`allowed_tools` (or letting permission_mode allow it). The Claude Code
preset system prompt already teaches the model how to use it.

This script wires up two SDK servers with a bunch of tools and lets the
model answer a question — observe how it invokes ToolSearch first.

Run: uv run python Tools_MCP/05_tool_search.py
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


# --- math server ---
@tool("add", "Add two numbers.", {"a": float, "b": float})
async def add(args): return {"content": [{"type": "text", "text": str(args["a"] + args["b"])}]}

@tool("sub", "Subtract b from a.", {"a": float, "b": float})
async def sub(args): return {"content": [{"type": "text", "text": str(args["a"] - args["b"])}]}

@tool("mul", "Multiply two numbers.", {"a": float, "b": float})
async def mul(args): return {"content": [{"type": "text", "text": str(args["a"] * args["b"])}]}

@tool("div", "Divide a by b.", {"a": float, "b": float})
async def div(args): return {"content": [{"type": "text", "text": str(args["a"] / args["b"])}]}


# --- string server ---
@tool("upper", "Uppercase a string.", {"s": str})
async def upper(args): return {"content": [{"type": "text", "text": args["s"].upper()}]}

@tool("reverse", "Reverse a string.", {"s": str})
async def reverse(args): return {"content": [{"type": "text", "text": args["s"][::-1]}]}

@tool("len_chars", "Count characters in a string.", {"s": str})
async def len_chars(args): return {"content": [{"type": "text", "text": str(len(args["s"]))}]}


async def main() -> None:
    math_srv = create_sdk_mcp_server("math", tools=[add, sub, mul, div])
    str_srv = create_sdk_mcp_server("strs", tools=[upper, reverse, len_chars])

    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": "Many tools are available but their schemas are deferred — use ToolSearch to load only what you need.",
        },
        mcp_servers={"math": math_srv, "strs": str_srv},
        # Allow ToolSearch + the actual tools you want reachable post-search.
        allowed_tools=["ToolSearch", "mcp__math", "mcp__strs"],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Reverse the string 'Anthropic' and tell me the length of the result.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:200])
                    elif isinstance(b, ToolUseBlock):
                        print(f"tool_use: {b.name}({b.input})")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
