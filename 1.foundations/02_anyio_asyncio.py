"""
anyio / asyncio
===============

The SDK is async-first. Everything (`query()`, `ClaudeSDKClient`,
`receive_response()`) is an async iterator or coroutine — you must run
it inside an event loop.

You have two choices:

  * `asyncio` (stdlib)        — the default Python event loop.
  * `anyio`                    — a thin compatibility layer that runs on
                                 asyncio OR trio, with nicer task groups
                                 and cancellation semantics. The SDK
                                 itself uses anyio internally.

Either works. Pick `anyio` if you want structured concurrency
(`anyio.create_task_group`) for things like:
  * running a producer (push input) and consumer (read output) in parallel
  * cancelling all child tasks if one fails

Run: uv run python foundations/02_anyio_asyncio.py
"""

import asyncio

import anyio
from claude_agent_sdk import AssistantMessage, TextBlock, query


async def ask(prompt: str) -> str:
    parts: list[str] = []
    async for msg in query(prompt=prompt):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    parts.append(b.text)
    return "".join(parts).strip()


async def main_anyio() -> None:
    # Structured concurrency: two queries in parallel, both cancelled
    # if one raises. Results gathered via a shared list.
    results: dict[str, str] = {}

    async def run(key: str, prompt: str) -> None:
        results[key] = await ask(prompt)

    async with anyio.create_task_group() as tg:
        tg.start_soon(run, "a", "Say 'A'.")
        tg.start_soon(run, "b", "Say 'B'.")

    print("anyio results:", results)


def main_asyncio() -> None:
    # Equivalent with stdlib asyncio.gather.
    async def go():
        a, b = await asyncio.gather(ask("Say 'A'."), ask("Say 'B'."))
        print("asyncio results:", {"a": a, "b": b})

    asyncio.run(go())


if __name__ == "__main__":
    anyio.run(main_anyio)
    main_asyncio()
