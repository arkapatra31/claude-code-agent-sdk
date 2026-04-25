"""
Context windows
===============

Each model has a fixed context budget (input + output tokens). The SDK
helps you manage it:

  * Every ResultMessage exposes `.usage` with input/output/cache token
    counts — track the running total to know how close you are to the
    limit.
  * The harness emits a SystemMessage(subtype="compact_boundary") when
    auto-compaction kicks in: older turns get summarized to free up
    context. You can drive it manually with the `/compact` slash command
    via `client.query("/compact")`.
  * Use `setting_sources=[]` (default) to skip loading CLAUDE.md /
    settings.json so they don't eat your budget unintentionally.
  * Prompt caching is automatic for stable system prompts — keep the
    system prompt prefix unchanged across turns to maximize cache hits
    (visible as `cache_read_input_tokens`).

This script runs a few turns, prints token usage after each, and triggers
a manual compaction.

Run: uv run python sdk-patterns/08_context_windows.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
)


async def run_turn(client: ClaudeSDKClient, prompt: str, label: str) -> None:
    await client.query(prompt)
    async for msg in client.receive_response():
        if isinstance(msg, SystemMessage) and msg.subtype == "compact_boundary":
            print(f"[{label}] !! auto-compaction boundary: {msg.data}")
        elif isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(f"[{label}] {b.text.strip()[:120]}")
        elif isinstance(msg, ResultMessage):
            usage = msg.usage or {}
            print(
                f"[{label}] usage: input={usage.get('input_tokens')} "
                f"output={usage.get('output_tokens')} "
                f"cache_read={usage.get('cache_read_input_tokens')} "
                f"cache_create={usage.get('cache_creation_input_tokens')}"
            )
            return


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="You are a concise assistant. Always answer in <= 2 sentences.",
        setting_sources=[],  # don't auto-load CLAUDE.md / settings — keep budget tight
    )

    async with ClaudeSDKClient(options=options) as client:
        await run_turn(client, "Define 'context window' in one sentence.", "t1")
        await run_turn(client, "Now define 'prompt caching' in one sentence.", "t2")
        await run_turn(client, "And 'token' in one sentence.", "t3")

        # Manually compact — older turns are summarized to free the window.
        print("--- requesting compaction ---")
        await run_turn(client, "/compact", "compact")

        await run_turn(client, "What three terms have I asked you to define so far?", "t4")


if __name__ == "__main__":
    anyio.run(main)
