"""
ClaudeSDKClient
===============

`ClaudeSDKClient` is the long-lived, bidirectional client. Compared to
the one-shot `query()` function it gives you:

  * persistent session across many .query() calls
  * mid-conversation interruption via .interrupt()
  * dynamic permission/model/setting changes:
        await client.set_permission_mode("plan")
        await client.set_model("claude-sonnet-4-6")
  * separation of "send" (.query) and "receive" (.receive_response /
    .receive_messages) so producers and consumers can run concurrently.

Lifecycle:
  async with ClaudeSDKClient(options=...) as c:
      await c.query("...")
      async for msg in c.receive_response(): ...
      await c.interrupt()                      # stop current turn
      await c.set_permission_mode("acceptEdits")
      await c.query("next turn")

Run: uv run python sdk-patterns/06_claude_sdk_client.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)


async def drain(client: ClaudeSDKClient, label: str) -> None:
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(f"[{label}] {b.text.strip()[:200]}")
        elif isinstance(msg, ResultMessage):
            print(f"[{label}] done turns={msg.num_turns}")


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="Be terse.",
        permission_mode="default",
    )

    async with ClaudeSDKClient(options=options) as client:
        # Turn 1
        await client.query("Pick a random fruit and remember it.")
        await drain(client, "t1")

        # Switch permission mode mid-conversation
        await client.set_permission_mode("plan")

        # Turn 2 — same session, history retained
        await client.query("What fruit did you pick?")
        await drain(client, "t2")

        # Turn 3 — show interruption: start a long task then cancel
        await client.query("Count slowly from 1 to 50, one number per line.")

        async def reader():
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            print(f"[t3] {b.text[:80]}")
                elif isinstance(msg, ResultMessage):
                    return

        async with anyio.create_task_group() as tg:
            tg.start_soon(reader)
            await anyio.sleep(1.0)
            print("[t3] interrupting...")
            await client.interrupt()


if __name__ == "__main__":
    anyio.run(main)
