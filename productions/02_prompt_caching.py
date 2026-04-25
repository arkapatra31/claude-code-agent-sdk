"""
Prompt caching
==============

Anthropic's prompt cache lets you reuse the prefix of a request across
calls — slashing TTFT and cost when you have a long, stable system
prompt or knowledge pack.

How the Agent SDK exposes it:
  - The CLI under the hood enables caching automatically when your
    system prompt + tools + early messages are stable across turns.
  - You read cache hits/misses from `ResultMessage.usage`, which
    includes `cache_creation_input_tokens` and `cache_read_input_tokens`
    on supported models.

Engineering rules that make caching actually pay off:

  1. PUT THE STABLE STUFF FIRST.
        System prompt → tool schemas → long reference doc → user query.
        Cache hits the longest matching prefix.

  2. DON'T INTERPOLATE VOLATILE DATA INTO THE PREFIX.
        Timestamps, request IDs, user names belong in the user message,
        not the system prompt. One char of drift busts the cache.

  3. KEEP THE SAME SESSION FOR REPEATED Q&A.
        `ClaudeSDKClient` reuses the cache; fresh `query()` calls do
        not.

  4. CACHE TTL IS ~5 MINUTES.
        Don't expect overnight reuse — design for short, hot loops.

This script issues two queries against the same long context inside one
session and prints the cache_read tokens climbing on the second turn.

Run: uv run python productions/02_prompt_caching.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

# A stable, multi-KB knowledge pack. Pretend this is your product manual.
KNOWLEDGE = (
    "ACME WIDGET SUPPORT MANUAL\n"
    + ("- step: tighten bolt A clockwise to 12Nm.\n" * 200)
    + "- escalation: page oncall@acme.example after 2 failed attempts.\n"
)

SYSTEM = (
    "You are an ACME support engineer. Answer ONLY from the manual below.\n\n"
    f"<manual>\n{KNOWLEDGE}\n</manual>"
)


def _print_usage(label: str, msg: ResultMessage) -> None:
    u = msg.usage or {}
    print(
        f"[{label}] in={u.get('input_tokens')} out={u.get('output_tokens')} "
        f"cache_create={u.get('cache_creation_input_tokens')} "
        f"cache_read={u.get('cache_read_input_tokens')} "
        f"usd={msg.total_cost_usd}"
    )


async def main() -> None:
    options = ClaudeAgentOptions(system_prompt=SYSTEM)

    async with ClaudeSDKClient(options=options) as client:
        for label, q in [
            ("turn1", "What torque do I use on bolt A?"),
            ("turn2", "When should I escalate?"),
        ]:
            await client.query(q)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            print(f"{label} answer:", b.text.strip())
                elif isinstance(msg, ResultMessage):
                    _print_usage(label, msg)


if __name__ == "__main__":
    anyio.run(main)
