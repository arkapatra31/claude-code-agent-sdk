"""
Structured outputs
==================

The Claude Agent SDK does not expose a native "response_format=json_schema"
knob — structured output is achieved by:

  1. Telling the model the exact JSON schema in the system prompt.
  2. Instructing it to reply with ONLY a JSON object (no prose, no fences).
  3. Parsing & validating on receipt; on failure, re-prompt with the
     validation error so the model self-corrects.

This pattern is robust because the agent loop already supports multi-turn
self-correction.

Run: uv run python sdk-patterns/07_structured_outputs.py
"""

import json
from dataclasses import dataclass

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

SCHEMA = {
    "type": "object",
    "required": ["title", "tags", "priority"],
    "properties": {
        "title": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "additionalProperties": False,
}

SYSTEM = (
    "You convert free-form user requests into a JSON object that strictly "
    f"conforms to this JSON Schema:\n{json.dumps(SCHEMA, indent=2)}\n"
    "Reply with ONLY the JSON object — no markdown fences, no commentary."
)


@dataclass
class Ticket:
    title: str
    tags: list[str]
    priority: str


def validate(obj: dict) -> Ticket:
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    missing = [k for k in ("title", "tags", "priority") if k not in obj]
    if missing:
        raise ValueError(f"missing keys: {missing}")
    if obj["priority"] not in {"low", "medium", "high"}:
        raise ValueError("priority must be low|medium|high")
    if not isinstance(obj["tags"], list) or not all(isinstance(t, str) for t in obj["tags"]):
        raise ValueError("tags must be list[str]")
    return Ticket(title=obj["title"], tags=obj["tags"], priority=obj["priority"])


async def collect_text(client: ClaudeSDKClient) -> str:
    parts: list[str] = []
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, TextBlock):
                    parts.append(b.text)
        elif isinstance(msg, ResultMessage):
            break
    return "".join(parts).strip()


async def extract(user_request: str, max_attempts: int = 3) -> Ticket:
    options = ClaudeAgentOptions(system_prompt=SYSTEM)
    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_request)
        for attempt in range(1, max_attempts + 1):
            raw = await collect_text(client)
            try:
                return validate(json.loads(raw))
            except (json.JSONDecodeError, ValueError) as e:
                if attempt == max_attempts:
                    raise
                # Self-correction loop — feed the error back in the same session
                await client.query(
                    f"Your previous reply was invalid: {e}. "
                    "Reply again with ONLY the JSON object that conforms to the schema."
                )
        raise RuntimeError("unreachable")


async def main() -> None:
    ticket = await extract(
        "Hey, the login button is broken on mobile Safari and customers can't sign in. "
        "Tag it as bug and frontend, this is urgent."
    )
    print(ticket)


if __name__ == "__main__":
    anyio.run(main)
