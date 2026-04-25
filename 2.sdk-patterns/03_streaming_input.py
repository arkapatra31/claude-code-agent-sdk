"""
Streaming input
===============

Streaming-input mode lets you push messages into the agent as an async
iterable instead of one fixed prompt. This enables:

  * multi-turn dialog driven by your own producer (UI, queue, file tail)
  * interleaving assistant turns with new user input
  * sending image blocks or pre-built content blocks mid-conversation

Two ways:
  A. Pass an async iterator of message dicts to `client.query(...)`.
  B. Use `query()` (the function) with `prompt=<async iterator>`.

Run: uv run python sdk-patterns/03_streaming_input.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)


async def user_inputs():
    """Async producer of user turns — could be a websocket, queue, etc."""
    prompts = [
        "Hi, my name is Ark.",
        "What is 7 * 6?",
        "Repeat my name back to me.",
    ]
    for p in prompts:
        yield {
            "type": "user",
            "message": {"role": "user", "content": p},
            "parent_tool_use_id": None,
            "session_id": "demo-stream",
        }
        # Simulate think time between user turns
        await anyio.sleep(0.1)


async def main() -> None:
    async with ClaudeSDKClient(
        options=ClaudeAgentOptions(system_prompt="Reply in one short sentence.")
    ) as client:
        await client.query(user_inputs())

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print(f"assistant: {b.text}")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
