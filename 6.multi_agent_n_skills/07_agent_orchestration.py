"""
Agent orchestration
===================

Orchestration = a top-level "manager" agent that breaks work into
phases and delegates each phase to specialist subagents, synthesizing
their outputs into a coherent result.

Common topologies:

  1. PIPELINE
        researcher → planner → coder → reviewer
        Output of each phase is the input to the next.

  2. FAN-OUT / FAN-IN (map-reduce)
        Manager spawns N parallel investigators on chunks of a
        problem, then a synthesizer merges their reports.

  3. DEBATE
        Two specialists argue opposite positions; a judge picks the
        stronger argument. Useful for design review.

Practical guidance:

  - The manager's system prompt is the orchestration policy. Spell out
    the phases and what each subagent is responsible for.
  - Keep specialist prompts narrow — one job each.
  - Pin cheap models to high-volume specialists (haiku for grep, opus
    for reasoning).
  - The manager is the only one talking to the user — subagents return
    summaries the manager re-frames.

This script builds a small fan-out/fan-in: a manager dispatches two
research subagents on different angles and a writer synthesizes a
final answer.

Run: uv run python multi_agent_n_skills/07_agent_orchestration.py
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
    "code-scout": AgentDefinition(
        description="Scouts the codebase for examples of a given pattern. Read-only.",
        prompt=(
            "Find concrete code examples of the requested pattern. "
            "Return a tight bullet list with file:line citations."
        ),
        tools=["Grep", "Glob", "Read"],
        model="haiku",
    ),
    "doc-scout": AgentDefinition(
        description="Reads markdown/docs files to extract conceptual explanations.",
        prompt=(
            "Pull conceptual explanations and quotes from .md files. "
            "Return a tight bullet list with file:line citations."
        ),
        tools=["Grep", "Glob", "Read"],
        model="haiku",
    ),
    "synthesizer": AgentDefinition(
        description="Merges multiple research summaries into a single tight answer.",
        prompt=(
            "Combine the inputs into one coherent answer (<= 200 words). "
            "Preserve citations. Resolve any contradictions explicitly."
        ),
        tools=[],
    ),
}

ORCHESTRATOR_PROMPT = """\
You are an orchestrator. To answer the user, follow this protocol:

  1. In ONE turn, dispatch BOTH `code-scout` and `doc-scout` in parallel
     via the Agent tool — each with a focused sub-question.
  2. Once both summaries return, dispatch `synthesizer` with the two
     summaries as input.
  3. Reply to the user with the synthesizer's output verbatim.

Never answer from your own knowledge — always go through the scouts.
"""


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        permission_mode="bypassPermissions",
        agents=AGENTS,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "How does this repo demonstrate `can_use_tool`? Give code references "
            "AND the conceptual rationale."
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, ToolUseBlock) and b.name == "Agent":
                        print(f"  → dispatch {b.input.get('subagent_type')}: "
                              f"{str(b.input.get('description', ''))[:60]}")
                    elif isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:400])
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns} usd={msg.total_cost_usd}]")


if __name__ == "__main__":
    anyio.run(main)
