"""
Sequential handoff: parent injects subagent-1 output into subagent-2 prompt
============================================================================

This example makes the injection step explicit and observable.

PIPELINE
    user question
        │
        ▼
    [code-analyst]  ← subagent 1
    Scans the repo, returns structured findings (file:line citations).
        │
        │  parent receives text output, embeds it verbatim
        ▼
    [doc-writer]    ← subagent 2
    Receives code-analyst's findings IN its prompt and turns them
    into a beginner-friendly explanation.
        │
        ▼
    parent relays final prose to user

KEY MECHANIC
    The parent's system prompt contains an explicit STEP instruction:
      "In subagent-2's prompt, paste the COMPLETE text returned by
       subagent-1 under the heading === FINDINGS ===."

    Claude (the parent LLM) reads subagent-1's tool result from its own
    context window and literally copies it into the next Agent tool call's
    `prompt` field. That is the injection.

    There is no SDK magic — it's the parent LLM composing the second
    prompt string using the first tool result as raw material.

Run: uv run python multi_agent_n_skills/09_sequential_handoff.py
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

# ── agent definitions ──────────────────────────────────────────────────────────

AGENTS = {
    "code-analyst": AgentDefinition(
        description=(
            "Use this to scan the repo for concrete code examples of a pattern. "
            "Returns bullet points with file:line citations. Read-only."
        ),
        prompt=(
            "You are a read-only code analyst. "
            "Use Grep, Glob, and Read to find concrete examples of the requested pattern. "
            "Return EXACTLY this format:\n\n"
            "SUMMARY: one sentence describing the pattern.\n"
            "FINDINGS:\n"
            "- <file>:<line> — <one-line explanation>\n"
            "...\n\n"
            "No preamble, no conclusion. Cite at least 3 locations."
        ),
        tools=["Grep", "Glob", "Read"],
        model="haiku",
    ),
    "doc-writer": AgentDefinition(
        description=(
            "Use this to turn raw code findings into beginner-friendly prose. "
            "Pass the code-analyst output under === FINDINGS === in the prompt."
        ),
        prompt=(
            "You are a technical writer for developers who are new to multi-agent systems. "
            "You will receive a section labelled === FINDINGS === containing file:line citations "
            "from a code analyst. Your job:\n\n"
            "1. Write a short (<=150 words) explanation of what the findings show.\n"
            "2. Highlight the most instructive example with a brief quote or paraphrase.\n"
            "3. End with one practical takeaway.\n\n"
            "Do NOT search the codebase yourself — work only from the findings you are given."
        ),
        tools=[],  # pure generation — no file access needed
    ),
}

# ── orchestrator prompt ────────────────────────────────────────────────────────
# This is where the injection contract is specified.

ORCHESTRATOR_PROMPT = """\
You are an orchestrator that answers questions about this codebase using a two-step pipeline.

STEP 1 — dispatch `code-analyst`:
  Call the Agent tool with subagent_type="code-analyst" and a focused search question.
  Wait for its response.

STEP 2 — dispatch `doc-writer`:
  Call the Agent tool with subagent_type="doc-writer".
  In the `prompt` field you MUST paste the COMPLETE text returned by code-analyst,
  wrapped exactly like this:

    === FINDINGS ===
    <paste code-analyst output here verbatim>
    === END FINDINGS ===

  Then add the user's original question after the block so doc-writer has context.

STEP 3 — relay:
  Return doc-writer's response verbatim to the user.

Never answer from your own knowledge. Always run both steps in order.
"""

# ── runner ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt=ORCHESTRATOR_PROMPT,
        permission_mode="bypassPermissions",
        agents=AGENTS,
    )

    question = (
        "How does this repo define AgentDefinition? "
        "Show examples and explain what each field does."
    )

    print(f"USER: {question}\n")
    print("─" * 60)

    async with ClaudeSDKClient(options=options) as client:
        await client.query(question)

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock) and block.name == "Agent":
                        agent = block.input.get("subagent_type", "?")
                        # Print the first 200 chars of the prompt to show injection
                        prompt_preview = str(block.input.get("prompt", ""))[:200]
                        print(f"\n[PARENT → {agent}]")
                        print(f"  prompt (first 200 chars): {prompt_preview!r}")

                    elif isinstance(block, TextBlock) and block.text.strip():
                        print(f"\n[FINAL ANSWER]\n{block.text.strip()}")

            elif isinstance(msg, ResultMessage):
                u = msg.usage or {}
                print(
                    f"\n[done  turns={msg.num_turns} "
                    f"input_tokens={u.get('input_tokens')} "
                    f"output_tokens={u.get('output_tokens')} "
                    f"usd={msg.total_cost_usd}]"
                )


if __name__ == "__main__":
    anyio.run(main)
