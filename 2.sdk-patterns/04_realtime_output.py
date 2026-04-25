"""
Real-time output
================

Set `include_partial_messages=True` to receive StreamEvent messages —
incremental deltas as the model generates them — instead of waiting for
each AssistantMessage to complete. Useful for:

  * token-by-token UI rendering
  * early cancellation when the model goes off-track
  * showing "thinking..." indicators

Event shapes you'll see in StreamEvent.event:
  - {"type":"content_block_start", ...}
  - {"type":"content_block_delta", "delta":{"type":"text_delta","text":"..."}}
  - {"type":"content_block_stop", ...}
  - {"type":"message_delta", ...}

Run: uv run python sdk-patterns/04_realtime_output.py
"""

import sys

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
    TextBlock,
)


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="Write a short haiku about streaming tokens.",
        include_partial_messages=True,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Go.")

        async for msg in client.receive_response():
            if isinstance(msg, StreamEvent):
                ev = msg.event
                if ev.get("type") == "content_block_delta":
                    delta = ev.get("delta", {})
                    if delta.get("type") == "text_delta":
                        sys.stdout.write(delta.get("text", ""))
                        sys.stdout.flush()
            elif isinstance(msg, AssistantMessage):
                # Final, fully assembled assistant turn arrives after deltas.
                final = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
                print(f"\n--- final assembled ---\n{final}")
            elif isinstance(msg, ResultMessage):
                print(f"[done in {msg.duration_ms} ms]")


if __name__ == "__main__":
    anyio.run(main)
