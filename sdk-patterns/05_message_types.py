"""
Message types
=============

The SDK's receive_response() yields a small, well-defined set of
message types. Knowing them lets you write robust handlers.

Top-level messages:
  - SystemMessage      : lifecycle events (subtype="init", "compact_boundary", ...)
  - AssistantMessage   : a full assistant turn; .content is list[ContentBlock]
  - UserMessage        : user-role turn; usually contains tool_result blocks
  - StreamEvent        : raw incremental deltas (only with include_partial_messages)
  - ResultMessage      : end-of-turn marker with cost/usage/session_id

Content blocks (inside AssistantMessage / UserMessage):
  - TextBlock          : plain text
  - ThinkingBlock      : extended-thinking traces (.thinking, .signature)
  - ToolUseBlock       : model requests a tool (.name, .input, .id)
  - ToolResultBlock    : tool's reply (.tool_use_id, .content, .is_error)

Run: uv run python sdk-patterns/05_message_types.py
"""

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


def describe_block(b) -> str:
    if isinstance(b, TextBlock):
        return f"TextBlock({len(b.text)} chars)"
    if isinstance(b, ThinkingBlock):
        return f"ThinkingBlock({len(b.thinking)} chars)"
    if isinstance(b, ToolUseBlock):
        return f"ToolUseBlock(name={b.name}, id={b.id})"
    if isinstance(b, ToolResultBlock):
        return f"ToolResultBlock(is_error={b.is_error})"
    return type(b).__name__


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="Be brief.",
        allowed_tools=["Read"],
        permission_mode="acceptEdits",
        include_partial_messages=False,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Read pyproject.toml and tell me the python version requirement.")

        async for msg in client.receive_response():
            if isinstance(msg, SystemMessage):
                print(f"SystemMessage subtype={msg.subtype}")
            elif isinstance(msg, AssistantMessage):
                blocks = ", ".join(describe_block(b) for b in msg.content)
                print(f"AssistantMessage[{msg.model}]: {blocks}")
            elif isinstance(msg, UserMessage):
                blocks = ", ".join(describe_block(b) for b in msg.content) if isinstance(msg.content, list) else str(type(msg.content))
                print(f"UserMessage: {blocks}")
            elif isinstance(msg, StreamEvent):
                print(f"StreamEvent type={msg.event.get('type')}")
            elif isinstance(msg, ResultMessage):
                print(
                    f"ResultMessage subtype={msg.subtype} turns={msg.num_turns} "
                    f"is_error={msg.is_error} session={msg.session_id}"
                )


if __name__ == "__main__":
    anyio.run(main)
