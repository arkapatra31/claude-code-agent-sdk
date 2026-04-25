"""
File checkpointing
==================

When the agent edits files, you usually want a "tape" of the changes so
you can review or revert. The SDK exposes this via:

    ClaudeAgentOptions(enable_file_checkpointing=True)

When enabled, the SDK snapshots files BEFORE each Write/Edit/NotebookEdit
and tracks the diff. You get two practical benefits:

  - Visibility:  inspect what changed during the session.
  - Rollback:    restore from a snapshot if a turn went sideways.

You can also implement a poor-man's checkpoint manually with a
PreToolUse hook that copies the target file before mutation. That's
useful if you want custom storage (S3, git stash, db) instead of the
SDK's in-memory tape. This script demos both: the built-in flag AND a
manual pre-write snapshot hook.

Run: uv run python advanced_patterns/04_file_checkpointing.py
"""

import os
import shutil
import time

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PreToolUseHookInput,
    ResultMessage,
    TextBlock,
)

WORKSPACE = os.path.abspath("./_sandbox")
SNAPSHOTS = os.path.join(WORKSPACE, ".snapshots")


async def snapshot_before_write(
    payload: PreToolUseHookInput, _tool_use_id: str | None, _ctx
) -> dict:
    tool = payload["tool_name"]
    if tool not in {"Write", "Edit"}:
        return {}
    path = payload["tool_input"].get("file_path")
    if not path or not os.path.exists(path):
        return {}
    os.makedirs(SNAPSHOTS, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    dest = os.path.join(SNAPSHOTS, f"{os.path.basename(path)}.{stamp}.bak")
    shutil.copy2(path, dest)
    print(f"[checkpoint] saved {path} → {dest}")
    return {}


async def main() -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    target = os.path.join(WORKSPACE, "draft.txt")
    with open(target, "w") as f:
        f.write("first version\n")

    options = ClaudeAgentOptions(
        system_prompt="Edit the file as requested. One change per turn.",
        allowed_tools=["Read", "Write", "Edit"],
        permission_mode="bypassPermissions",
        cwd=WORKSPACE,
        enable_file_checkpointing=True,  # SDK-level tape
        hooks={
            "PreToolUse": [HookMatcher(hooks=[snapshot_before_write])],  # custom tape
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(f"Replace the contents of {target} with 'second version'.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        print("text:", b.text.strip()[:200])
            elif isinstance(msg, ResultMessage):
                print(f"[done turns={msg.num_turns}]")

    print("\nSnapshots dir:")
    if os.path.isdir(SNAPSHOTS):
        for fn in sorted(os.listdir(SNAPSHOTS)):
            print(" -", fn)


if __name__ == "__main__":
    anyio.run(main)
