"""
Reduce hallucinations
=====================

Hallucinations come from the model filling gaps with plausible-but-wrong
content. Production agents reduce that risk with FOUR levers:

  1. GROUND THE ANSWER.
        Force the model to read source material with `Read` / search
        tools, and to cite the file + line it pulled from. If it can't
        find a source, it must say "I don't know."

  2. CONSTRAIN THE OUTPUT.
        A schema (or "answer ONLY with X") removes degrees of freedom
        the model could hallucinate into.

  3. TWO-PASS SELF-CHECK.
        After drafting, ask the model to verify each claim against the
        provided sources and remove unsupported ones.

  4. INSTRUCT EXPLICIT UNCERTAINTY.
        Add to the system prompt: "If unsure, say so. Do not guess."
        Cheap, surprisingly effective.

This script is a grounded Q&A: it gives the agent a small "facts" file,
forces it to cite, and rejects answers without citations.

Run: uv run python productions/03_reduce_hallucinations.py
"""

import os
import re

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

WORKSPACE = os.path.abspath("./_sandbox")
FACTS = os.path.join(WORKSPACE, "facts.md")

SYSTEM = """\
You answer questions ONLY from facts.md in the working directory.
Rules:
  - Read facts.md first using the Read tool.
  - Every factual claim must end with a citation in the form [facts.md:LINE].
  - If the file does not contain the answer, reply exactly: "I don't know."
  - Do not invent line numbers. Do not paraphrase from outside knowledge.
"""

CITE_RE = re.compile(r"\[facts\.md:\d+\]")


async def main() -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    with open(FACTS, "w") as f:
        f.write(
            "1. ACME was founded in 1998 in Portland, Oregon.\n"
            "2. The flagship product is the Mark IV Widget.\n"
            "3. Support hours are 09:00–17:00 PT, Monday to Friday.\n"
        )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM,
        allowed_tools=["Read"],
        permission_mode="bypassPermissions",
        cwd=WORKSPACE,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "When was ACME founded, and who is its CEO? Answer concisely."
        )
        final = ""
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        final += b.text
            elif isinstance(msg, ResultMessage):
                pass

        print("answer:", final.strip())
        # Validator: any claim must be cited or be the explicit IDK string.
        claims = [s for s in re.split(r"(?<=[.!?])\s+", final.strip()) if s]
        unsupported = [
            c for c in claims if c.strip() != "I don't know." and not CITE_RE.search(c)
        ]
        if unsupported:
            print("\n[VALIDATOR REJECT] uncited claims:")
            for u in unsupported:
                print(" -", u)
        else:
            print("\n[VALIDATOR OK] every claim is cited or admits ignorance.")


if __name__ == "__main__":
    anyio.run(main)
