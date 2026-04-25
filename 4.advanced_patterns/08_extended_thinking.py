"""
Extended thinking
=================

Claude can produce "thinking" blocks — explicit, surfaced reasoning the
model does before answering. With the Agent SDK you control it via:

  thinking=ThinkingConfigEnabled(budget_tokens=N)
        Always think; cap reasoning at N tokens.
  thinking=ThinkingConfigAdaptive()
        Let the runtime decide when to think and how hard.
  thinking=ThinkingConfigDisabled()
        No thinking blocks at all.

Or use the simpler `effort` knob: "low" | "medium" | "high" | "max"
which maps to a sensible thinking budget under the hood.

Two practical handles for SDK builders:

  - `ThinkingBlock` arrives in `AssistantMessage.content` alongside text
    and tool-use blocks. Render or log it separately — it isn't part of
    the "answer".
  - Thinking tokens are billed. Cap them with `budget_tokens` for
    predictable cost; use `effort="low"` for chatty endpoints, `"high"`
    for hard reasoning tasks.

This script asks a math puzzle, prints the thinking trace separately
from the final answer.

Run: uv run python advanced_patterns/08_extended_thinking.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ThinkingConfigEnabled,
)


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="Reason carefully, then answer concisely.",
        thinking=ThinkingConfigEnabled(
            type="enabled",
            budget_tokens=4000,
            display="summarized",
        ),
        effort="medium",
        # `effort="high"` would also work and is simpler:
        # effort="high",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "I have 13 coins, one is fake (lighter). Using a balance scale, "
            "what is the minimum number of weighings to guarantee finding it? Explain."
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, ThinkingBlock):
                        print("─ thinking ─")
                        print(b.thinking.strip())
                        print("─ /thinking ─")
                    elif isinstance(b, TextBlock):
                        print("\nanswer:", b.text.strip())
            elif isinstance(msg, ResultMessage):
                print(f"\n[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
