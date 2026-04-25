"""
Sessions & state
================

A "session" is the SDK's persistent conversation: every turn appended to
the same message history. Two ways to maintain state:

  1. Single ClaudeSDKClient instance — keep it alive across multiple
     `query()` calls; history accumulates inside the client.
  2. Resume by session_id — pass `resume="<session_id>"` in
     ClaudeAgentOptions to reattach to a previous run. The session_id
     is reported on every ResultMessage / SystemMessage("init").

Use `continue_conversation=True` to auto-resume the most recent session
without knowing the id.

Run: uv run python sdk-patterns/02_sessions_and_state.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)


async def collect_text(client: ClaudeSDKClient) -> tuple[str, str | None]:
    text_parts: list[str] = []
    session_id: str | None = None
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    text_parts.append(b.text)
        elif isinstance(msg, ResultMessage):
            session_id = msg.session_id
    return "".join(text_parts), session_id


async def main() -> None:
    # --- Part 1: live session — same client retains state across queries ---
    async with ClaudeSDKClient(
        options=ClaudeAgentOptions(system_prompt="Be terse.")
    ) as client:
        await client.query("Remember the number 42. Just acknowledge.")
        _, sid = await collect_text(client)
        print(f"session_id: {sid}")

        await client.query("What number did I ask you to remember?")
        answer, _ = await collect_text(client)
        print(f"recalled: {answer.strip()}")

    # --- Part 2: resume a prior session by id in a brand-new client ---
    if sid:
        async with ClaudeSDKClient(
            options=ClaudeAgentOptions(system_prompt="Be terse.", resume=sid)
        ) as resumed:
            await resumed.query("And the number again, please?")
            answer2, _ = await collect_text(resumed)
            print(f"after resume: {answer2.strip()}")


if __name__ == "__main__":
    anyio.run(main)
