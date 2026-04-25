"""
Parallel tool use
=================

Claude can issue multiple tool calls in a single assistant turn. The
SDK dispatches them concurrently and waits for all results before
feeding them back into the loop. For independent calls, this collapses
N round-trips into one — a big latency win.

Two flavors you'll see:

  1. PARALLEL BUILT-IN TOOLS
        e.g. read 5 files at once, or run 3 grep queries side by side.
        No setup needed — just instruct the model to do work in
        parallel when calls are independent.

  2. PARALLEL SUBAGENTS
        Spawn several `Agent` calls in one turn for fan-out research.
        Each subagent gets its own context window; results stream back
        and the parent synthesizes them.

How to encourage parallelism:
  - System prompt: "When tool calls are independent, issue them in a
    single turn instead of sequentially."
  - Avoid artificial dependencies in your prompt ("first do X, then Y")
    when X and Y are independent.

This script asks the agent to read 3 files in parallel and report sizes.
Watch the tool-use timestamps cluster.

Run: uv run python multi_agent_n_skills/06_parallel_tool_use.py
"""

import os
import time

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

WORKSPACE = os.path.abspath("./_sandbox")


def seed_files() -> list[str]:
    paths = []
    os.makedirs(WORKSPACE, exist_ok=True)
    for i in range(3):
        p = os.path.join(WORKSPACE, f"doc_{i}.txt")
        with open(p, "w") as f:
            f.write(f"document number {i}\n" * (10 * (i + 1)))
        paths.append(p)
    return paths


async def main() -> None:
    paths = seed_files()
    options = ClaudeAgentOptions(
        system_prompt=(
            "When the user asks for information from multiple independent "
            "sources, ISSUE TOOL CALLS IN PARALLEL within a single turn. "
            "Do not chain sequentially when the calls do not depend on "
            "each other."
        ),
        allowed_tools=["Read"],
        permission_mode="bypassPermissions",
        cwd=WORKSPACE,
    )

    async with ClaudeSDKClient(options=options) as client:
        t0 = time.monotonic()
        await client.query(
            "Read these three files and report each one's line count: "
            + ", ".join(paths)
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                # Tool-use blocks issued in the same AssistantMessage =
                # parallel dispatch.
                tool_uses = [b for b in msg.content if isinstance(b, ToolUseBlock)]
                if tool_uses:
                    dt = (time.monotonic() - t0) * 1000
                    print(f"[t+{dt:.0f}ms] turn issued {len(tool_uses)} tool calls "
                          f"in parallel: {[b.name for b in tool_uses]}")
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:300])
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns} api_ms={msg.duration_api_ms}]")


if __name__ == "__main__":
    anyio.run(main)
