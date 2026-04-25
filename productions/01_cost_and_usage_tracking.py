"""
Cost and usage tracking
=======================

Every turn the SDK emits a `ResultMessage` once the agent stops. It
carries the numbers you need to bill, alert, and budget against:

  total_cost_usd     Dollar cost for the whole session up to now.
  usage              Token counts (input, output, cache_read, cache_creation).
  model_usage        Per-model breakdown when multiple models are used.
  duration_ms        Wallclock duration of the turn.
  duration_api_ms    Time spent talking to the API.
  num_turns          How many tool/agent turns this session used.
  permission_denials Tool calls that were blocked.
  errors             Errors surfaced during the run.

Two production patterns:

  1. Per-turn ledger — append a row to your warehouse on every
     ResultMessage. Keep `session_id` so you can join across turns.

  2. Hard budget cap — set `max_budget_usd` and/or `max_turns` on
     `ClaudeAgentOptions`. The SDK will stop the loop when crossed.

This script runs a small task, prints the per-turn telemetry, and
demonstrates a soft budget alarm in the client.

Run: uv run python productions/01_cost_and_usage_tracking.py
"""

import json

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

SOFT_BUDGET_USD = 0.10


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="Answer briefly.",
        max_budget_usd=1.00,  # hard cap enforced by the SDK
        max_turns=4,
    )

    running_cost = 0.0
    async with ClaudeSDKClient(options=options) as client:
        await client.query("Name three Python web frameworks, one line each.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print(b.text.strip())
            elif isinstance(msg, ResultMessage):
                running_cost = msg.total_cost_usd or 0.0
                ledger = {
                    "session_id": msg.session_id,
                    "turns": msg.num_turns,
                    "duration_ms": msg.duration_ms,
                    "api_ms": msg.duration_api_ms,
                    "usd": msg.total_cost_usd,
                    "usage": msg.usage,
                    "stop_reason": msg.stop_reason,
                    "denials": len(msg.permission_denials or []),
                }
                print("\n[ledger]", json.dumps(ledger, default=str))
                if running_cost > SOFT_BUDGET_USD:
                    print(f"[ALERT] crossed soft budget ${SOFT_BUDGET_USD:.2f}")


if __name__ == "__main__":
    anyio.run(main)
