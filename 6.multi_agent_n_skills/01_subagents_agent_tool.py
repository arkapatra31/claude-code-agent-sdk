"""
Subagents (Agent tool)
======================

A subagent is a fresh, isolated agent loop the main agent can spawn via
the built-in `Agent` tool. Each subagent has its own context window,
tool allowlist, and system prompt — when it finishes, only its final
summary is returned to the parent.

Why use them:

  - CONTEXT HYGIENE
        A research subagent can grep across a repo and read 30 files.
        The parent only sees the 200-word summary.

  - SCOPED PERMISSIONS
        Restrict a subagent to read-only tools while the parent can
        write.

  - PARALLELISM
        The parent can launch several subagents in one turn (see
        `06_parallel_tool_use.py`).

You declare available subagents via `agents={name: AgentDefinition(...)}`
on `ClaudeAgentOptions`. The model then picks the right one through the
`Agent` tool's `subagent_type` parameter.

Run: uv run python multi_agent_n_skills/01_subagents_agent_tool.py
"""

import anyio
from claude_agent_sdk import (
    AgentDefinition,
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
            "You are an orchestrator. Delegate research-heavy work to the "
            "`researcher` subagent via the Agent tool. Keep your own context tight."
        ),
        permission_mode="bypassPermissions",
        agents={
            "researcher": AgentDefinition(
                description="Read-only repo researcher. Use for grep/find/read tasks.",
                prompt=(
                    "You are a research subagent. Use Grep/Glob/Read to answer the "
                    "parent's question. Reply with a tight summary under 150 words. "
                    "Cite file:line."
                ),
                tools=["Read", "Grep", "Glob"],
                model="haiku",  # cheaper, faster for grep work
            ),
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Use the researcher subagent to find every file under foundations/ that "
            "imports ClaudeSDKClient. Return the list."
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:300])
                    elif isinstance(b, ToolUseBlock):
                        print(f"tool: {b.name} input={str(b.input)[:120]}")
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns} usd={msg.total_cost_usd}]")


if __name__ == "__main__":
    anyio.run(main)
