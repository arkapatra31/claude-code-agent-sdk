"""
pip install claude-agent-sdk
============================

The SDK ships as a single package on PyPI:

    pip install claude-agent-sdk
    # or with uv (this repo)
    uv add claude-agent-sdk

Runtime requirements:
  * Python >= 3.10 (this repo pins >= 3.13 in pyproject.toml)
  * Node.js — the SDK launches the `claude` CLI binary under the hood
    via subprocess; it is bundled with the package.
  * An Anthropic API key in the environment:
        export ANTHROPIC_API_KEY=sk-ant-...
    or use Bedrock / Vertex env vars (CLAUDE_CODE_USE_BEDROCK=1, etc.).

This script just verifies the install + key + a one-shot model call.

Run: uv run python foundations/01_install.py
"""

import os
import sys

import anyio
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, query


async def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("WARN: ANTHROPIC_API_KEY is not set", file=sys.stderr)

    import claude_agent_sdk
    print(f"claude_agent_sdk version: {getattr(claude_agent_sdk, '__version__', 'unknown')}")

    async for msg in query(prompt="Reply with the single word: ready"):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    print(f"model says: {b.text.strip()}")
        elif isinstance(msg, ResultMessage):
            print(f"ok — cost=${msg.total_cost_usd or 0:.6f}")


if __name__ == "__main__":
    anyio.run(main)
