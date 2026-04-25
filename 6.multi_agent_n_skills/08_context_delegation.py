"""
Context delegation
==================

The single biggest reason to delegate to a subagent isn't speed — it's
CONTEXT BUDGET. Reading a 30-file repo, ingesting a 200KB log, or
exploring a deep search tree all bloat the parent's context. Once it
fills, you pay more per turn AND quality degrades.

The fix: hand the heavy task to a subagent and accept ONLY its summary
back. The parent's context stays small, the subagent's context dies
with its loop.

Rules of thumb:

  - DELEGATE when the work needs to read >5 files, or any file > a few
    KB, or any open-ended search.
  - PIN A SUMMARY BUDGET. Tell the subagent "reply in <= 300 tokens"
    or "one bullet list". Otherwise it returns a wall of text and
    defeats the point.
  - PASS POINTERS, NOT PAYLOADS. The parent gives the subagent a
    question + file paths, not the file contents. The subagent reads
    them itself.
  - VERIFY BEFORE TRUSTING. The parent should require citations
    (file:line) so a downstream reader can audit the summary.

This script demonstrates the saving: the parent asks a researcher to
digest a noisy log and return a 5-bullet summary. The parent never
sees the log itself.

Run: uv run python multi_agent_n_skills/08_context_delegation.py
"""

import os

import anyio
from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

WORKSPACE = os.path.abspath("./_sandbox")
LOG = os.path.join(WORKSPACE, "noisy.log")


def seed_log() -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    lines = []
    for i in range(2000):
        if i % 137 == 0:
            lines.append(f"{i:05d} ERROR connection reset by peer (peer=10.0.{i % 255}.7)")
        elif i % 211 == 0:
            lines.append(f"{i:05d} WARN slow query took 4200ms on table=orders")
        else:
            lines.append(f"{i:05d} INFO heartbeat ok")
    with open(LOG, "w") as f:
        f.write("\n".join(lines))


async def main() -> None:
    seed_log()
    options = ClaudeAgentOptions(
        system_prompt=(
            "You are a parent agent with a small context budget. NEVER read "
            "log files yourself. Delegate to the `log-digester` subagent and "
            "summarize its findings for the user."
        ),
        permission_mode="bypassPermissions",
        cwd=WORKSPACE,
        agents={
            "log-digester": AgentDefinition(
                description="Reads a log file and returns a 5-bullet summary of patterns.",
                prompt=(
                    "Read the file at the path the parent gives you. Return "
                    "EXACTLY 5 bullets summarizing recurring patterns, error "
                    "rates, and notable anomalies. Each bullet <= 20 words. "
                    "No preamble."
                ),
                tools=["Read", "Grep"],
                model="haiku",
            ),
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            f"Delegate to log-digester to summarize {LOG}. Then relay its bullets to me."
        )
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print(b.text.strip())
            elif isinstance(msg, ResultMessage):
                # Parent input tokens stay tiny because it never read the log.
                u = msg.usage or {}
                print(
                    f"\n[parent context kept small: input_tokens={u.get('input_tokens')}, "
                    f"output_tokens={u.get('output_tokens')}, usd={msg.total_cost_usd}]"
                )


if __name__ == "__main__":
    anyio.run(main)
