"""
Web search tool (and WebFetch)
==============================

The harness ships two networked built-ins:

  * WebSearch  — model-side search; returns ranked snippets/URLs.
                 Inputs: {"query": str, "allowed_domains": [..]?, "blocked_domains": [..]?}
  * WebFetch   — fetches a specific URL and returns cleaned text.
                 Inputs: {"url": str, "prompt": str}
                 (`prompt` tells the secondary model how to summarize
                 the fetched page, so the main model only sees what's
                 relevant.)

Typical flow the model uses:
    1. WebSearch for candidate URLs
    2. WebFetch the most promising one with a focused `prompt`
    3. Cite URL(s) in the answer

Privacy / cost:
  * Both tools make outbound network calls. Disable in offline / data-
    sensitive contexts by leaving them out of `allowed_tools`.
  * Use `blocked_domains` to keep the model away from specific sites.

Run: uv run python Tools_MCP/07_web_search_tool.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt=(
            "You research questions on the open web. "
            "Use WebSearch first to find candidate URLs, then WebFetch one or two "
            "to read in detail. Cite URLs in your final answer."
        ),
        allowed_tools=["WebSearch", "WebFetch"],
        permission_mode="acceptEdits",
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "When was the Model Context Protocol (MCP) first announced by Anthropic? "
            "Give a one-sentence answer with a source URL."
        )

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:300])
                    elif isinstance(b, ToolUseBlock):
                        # truncate long inputs (search results pages can be huge)
                        inp = {k: (str(v)[:120] + "...") if len(str(v)) > 120 else v
                               for k, v in b.input.items()}
                        print(f"tool_use: {b.name}({inp})")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")


if __name__ == "__main__":
    anyio.run(main)
