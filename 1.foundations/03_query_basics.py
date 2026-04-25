"""
query() basics
==============

`query()` is the simplest entry point — a one-shot async generator that
yields Messages until the turn ends. Use it for:

  * fire-and-forget prompts
  * scripts that don't need multi-turn state
  * batch jobs (each `query()` is its own session)

Signature:
    query(
        prompt: str | AsyncIterable[dict],
        options: ClaudeAgentOptions | None = None,
    ) -> AsyncIterator[Message]

Compared to `ClaudeSDKClient`:
  * No `.connect()` / `.disconnect()` — managed for you.
  * No `.interrupt()` mid-turn, no `set_permission_mode()`.
  * One prompt in, a stream of messages out, then done.

Run: uv run python foundations/03_query_basics.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


async def main() -> None:
    options = ClaudeAgentOptions(system_prompt="Reply in one short sentence.")

    async for msg in query(prompt="What is the capital of France?", options=options):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print("answer:", b.text.strip())
        elif isinstance(msg, ResultMessage):
            print(f"done — turns={msg.num_turns} session={msg.session_id}")


if __name__ == "__main__":
    anyio.run(main)
