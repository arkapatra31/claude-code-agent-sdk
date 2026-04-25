"""
subagent_type
=============

When the parent calls the built-in `Agent` tool, it must pass a
`subagent_type` to choose WHICH subagent to spin up. The names available
come from the `agents={...}` dict on `ClaudeAgentOptions` plus a few
built-ins (e.g. `general-purpose`).

This is the routing knob for a multi-agent system: each `subagent_type`
is a specialist with its own prompt, tool set, model, and effort
budget. The parent's job is to pick the right specialist for the job.

Design tips:

  - NAMES ARE PART OF THE PROMPT.
        The model picks `subagent_type` based on the agent's
        `description`. Make descriptions task-shaped:
        "Use this for X" beats "general assistant".

  - DON'T OVERLAP CAPABILITIES.
        Two subagents with similar descriptions confuse the router.
        Make each one's lane crisp.

  - COST/SPEED LANES.
        A `quick-grep` haiku-backed subagent + a `deep-thinker`
        opus-backed subagent gives the parent a cheap/expensive choice.

This script registers three subagents with distinct lanes and lets the
parent route a couple of tasks across them.

Run: uv run python multi_agent_n_skills/02_subagent_type.py
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

AGENTS = {
    "quick-grep": AgentDefinition(
        description="Fast keyword/file lookups across the repo. Read-only. Cheap.",
        prompt="You answer single grep/find questions in <80 words. Cite file:line.",
        tools=["Grep", "Glob", "Read"],
        model="haiku",
    ),
    "deep-thinker": AgentDefinition(
        description="Multi-file reasoning, design questions, architectural review.",
        prompt=(
            "You analyze code carefully across multiple files and write a thorough "
            "but tight report. Use Read freely; cite specifics."
        ),
        tools=["Read", "Grep", "Glob"],
        effort="high",
    ),
    "writer": AgentDefinition(
        description="Drafts user-facing prose: docs, release notes, READMEs.",
        prompt="You produce polished prose. No code. Match the requested tone.",
        tools=[],  # no tools — pure generation
    ),
}


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt=(
            "You are an orchestrator. For every user request, pick the BEST "
            "subagent_type from `quick-grep` (cheap lookups), `deep-thinker` "
            "(analysis), or `writer` (prose). Delegate via the Agent tool."
        ),
        permission_mode="bypassPermissions",
        agents=AGENTS,
    )

    requests = [
        "Find which file defines `can_use_tool` examples. One line.",
        "Write a 2-sentence release note announcing prompt caching support.",
    ]

    async with ClaudeSDKClient(options=options) as client:
        for r in requests:
            print(f"\n>>> request: {r}")
            await client.query(r)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            print("text:", b.text.strip()[:300])
                        elif isinstance(b, ToolUseBlock) and b.name == "Agent":
                            print(f"  routed → subagent_type={b.input.get('subagent_type')}")
                elif isinstance(msg, ResultMessage):
                    print(f"[turn done usd={msg.total_cost_usd}]")


if __name__ == "__main__":
    anyio.run(main)
