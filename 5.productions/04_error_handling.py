"""
Error handling
==============

Failures the SDK surfaces, and how to handle them in production:

  CLINotFoundError       The bundled `claude` CLI couldn't be located
                         (Node not installed, or `cli_path` wrong).
                         FIX: install Node, or pass `cli_path=...`.

  CLIConnectionError     Process started but the JSON stream broke
                         (CLI crashed, network died, parent killed it).
                         FIX: retry the whole session; don't reuse the
                         dead client.

  CLIJSONDecodeError     A frame off the CLI didn't parse as JSON.
                         Usually a bug or version skew between SDK and
                         CLI. Capture, log the raw line, fail loudly.

  ProcessError           The CLI exited non-zero. Check `exit_code` and
                         `stderr`. Often "API key missing" or "rate
                         limited".

  ClaudeSDKError         Base class — catch this last as a safety net.

Soft failures that DON'T raise — you must check `ResultMessage`:
  - `is_error=True`         The agent ended in an error state.
  - `stop_reason="max_turns" / "max_budget"`  Hit a guardrail.
  - `permission_denials`    Tool calls blocked; final answer may be
                            partial.
  - `errors`                Per-turn errors collected by the loop.

The pattern below: tenacity-style retry with exponential backoff for
transient errors, immediate failure for config errors.

Run: uv run python productions/04_error_handling.py
"""

import asyncio
import random

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ClaudeSDKError,
    ProcessError,
    ResultMessage,
    TextBlock,
)

TRANSIENT = (CLIConnectionError, CLIJSONDecodeError, ProcessError)


async def run_with_retry(prompt: str, *, attempts: int = 3) -> str:
    options = ClaudeAgentOptions(system_prompt="Be brief.", max_turns=2)
    last_exc: Exception | None = None

    for i in range(1, attempts + 1):
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                out: list[str] = []
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for b in msg.content:
                            if isinstance(b, TextBlock):
                                out.append(b.text)
                    elif isinstance(msg, ResultMessage):
                        # Soft failure surfaces here.
                        if msg.is_error:
                            raise RuntimeError(
                                f"agent reported error: stop={msg.stop_reason} "
                                f"errors={msg.errors}"
                            )
                return "".join(out).strip()

        except CLINotFoundError as e:
            # Not transient — retrying won't help.
            raise SystemExit(f"FATAL: claude CLI not found ({e})")

        except TRANSIENT as e:
            last_exc = e
            backoff = (2 ** (i - 1)) + random.random()
            print(f"[retry {i}/{attempts}] transient {type(e).__name__}: {e!r}; "
                  f"sleeping {backoff:.1f}s")
            await asyncio.sleep(backoff)

        except ClaudeSDKError as e:
            # Unknown SDK-level error — log and fail.
            raise RuntimeError(f"unhandled SDK error: {e!r}") from e

    raise RuntimeError(f"giving up after {attempts} attempts: {last_exc!r}")


async def main() -> None:
    answer = await run_with_retry("What is 2+2? Reply with just the digit.")
    print("final:", answer)


if __name__ == "__main__":
    anyio.run(main)
