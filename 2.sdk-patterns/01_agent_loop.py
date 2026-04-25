"""
Agent Loop internals
====================

The agent loop is: user turn -> model produces text + tool_use blocks ->
SDK executes tools -> tool_result fed back -> model continues -> repeat
until the model emits a final assistant turn (no more tool_use) and a
ResultMessage closes the turn.

Each iteration the SDK:
  1. Sends the running message history to the model.
  2. Streams back AssistantMessage blocks (text, thinking, tool_use).
  3. For each tool_use: runs the tool (built-in or MCP), returns a
     UserMessage containing a tool_result block.
  4. Loops until the model stops requesting tools.

Run: uv run python sdk-patterns/01_agent_loop.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="You are a precise coding assistant.",
        allowed_tools=["Read", "Glob"],
        permission_mode="acceptEdits",
        cwd=".",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("List the python files in sdk-patterns/ and tell me how many there are.")

        turn = 0
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                turn += 1
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"[assistant#{turn}] text: {block.text[:120]}")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[assistant#{turn}] -> tool_use {block.name}({block.input})")
            elif isinstance(msg, UserMessage):
                # tool_results are surfaced as user-role messages back to the model
                for block in msg.content:
                    if isinstance(block, ToolResultBlock):
                        preview = str(block.content)[:120]
                        print(f"[tool_result] is_error={block.is_error} -> {preview}")
            elif isinstance(msg, ResultMessage):
                print(
                    f"[result] turns={msg.num_turns} cost=${msg.total_cost_usd or 0:.4f} "
                    f"duration_ms={msg.duration_ms}"
                )


if __name__ == "__main__":
    anyio.run(main)
