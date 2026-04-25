"""
AsyncIterator[Message]
======================

Both `query()` and `ClaudeSDKClient.receive_response()` return an
`AsyncIterator[Message]`. That is the SDK's universal output channel:
you consume it with `async for msg in ...:`.

What this means in practice:

  * Lazy: messages arrive as the model produces them; iteration drives
    the agent loop forward turn by turn.
  * Single-pass: you cannot rewind. Capture state in your own variables
    if you need it later.
  * Cancellable: break out of the loop or cancel the surrounding task
    to stop consuming. With `ClaudeSDKClient` you can also call
    `await client.interrupt()` to stop the current model turn.
  * Composable: wrap it in any async pipeline — filter, map, fan out
    to multiple consumers via a queue, etc.

This script demos three useful patterns:
  1. simple drain
  2. early break (stop after first text block)
  3. fan-out: one producer, two consumers via memory channels

Run: uv run python foundations/08_async_iterator_message.py
"""

from typing import AsyncIterator

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from claude_agent_sdk.types import Message


def _opts() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(system_prompt="Reply in one short sentence.")


async def pattern_drain() -> None:
    print("\n--- 1. simple drain ---")
    async for msg in query(prompt="Name a primary color.", options=_opts()):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print("got:", b.text.strip())
        elif isinstance(msg, ResultMessage):
            print(f"[done turns={msg.num_turns}]")


async def pattern_early_break() -> None:
    print("\n--- 2. early break ---")
    async for msg in query(prompt="Count from 1 to 5, one per line.", options=_opts()):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print("first text block:", b.text.strip()[:2])
                    return  # stop iterating; subsequent messages are dropped


async def pattern_fanout() -> None:
    print("\n--- 3. fan-out to two consumers ---")
    src: AsyncIterator[Message] = query(prompt="Pick an animal.", options=_opts())

    send_a, recv_a = anyio.create_memory_object_stream[Message](16)
    send_b, recv_b = anyio.create_memory_object_stream[Message](16)

    async def producer() -> None:
        async with send_a, send_b:
            async for msg in src:
                await send_a.send(msg)
                await send_b.send(msg)

    async def consumer(name: str, recv) -> None:
        async with recv:
            async for msg in recv:
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            print(f"[{name}] {b.text.strip()}")

    async with anyio.create_task_group() as tg:
        tg.start_soon(producer)
        tg.start_soon(consumer, "A", recv_a)
        tg.start_soon(consumer, "B", recv_b)


async def main() -> None:
    await pattern_drain()
    await pattern_early_break()
    await pattern_fanout()


if __name__ == "__main__":
    anyio.run(main)
