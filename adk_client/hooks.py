import fnmatch
import os
from pathlib import Path

from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

# Tools whose `file_path` input we guard
_FILE_PATH_TOOLS = frozenset({"Read", "Write", "Edit", "MultiEdit", "NotebookEdit"})

# Always-blocked patterns regardless of .gitignore
_ALWAYS_BLOCKED = [".env", ".env.*", "*.env", ".envrc", ".env.local", ".env.production"]


def _load_gitignore_patterns(cwd: str) -> list[str]:
    patterns: list[str] = list(_ALWAYS_BLOCKED)
    try:
        with open(os.path.join(cwd, ".gitignore")) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line.rstrip("/"))
    except FileNotFoundError:
        pass
    return patterns


def _is_sensitive(file_path: str, cwd: str, patterns: list[str]) -> bool:
    try:
        rel_path = os.path.relpath(file_path, cwd)
    except ValueError:
        rel_path = file_path

    filename = os.path.basename(file_path)
    path_parts = Path(rel_path).parts

    for pattern in patterns:
        clean = pattern.lstrip("/")
        # Match the bare filename
        if fnmatch.fnmatch(filename, clean):
            return True
        # Match the full relative path
        if fnmatch.fnmatch(rel_path, clean):
            return True
        # Match any path component (catches directory entries like .venv, __pycache__)
        if any(fnmatch.fnmatch(p, clean) for p in path_parts):
            return True

    return False


async def sensitive_file_guard(
    hook_input: HookInput,
    tool_use_id: str | None,
    context: HookContext,
) -> HookJSONOutput:
    """Block Read/Write/Edit on .env and files matching .gitignore patterns."""
    tool_name: str = hook_input.get("tool_name", "")  # type: ignore[union-attr]
    if tool_name not in _FILE_PATH_TOOLS:
        return {"continue_": True}

    tool_input: dict = hook_input.get("tool_input", {})  # type: ignore[union-attr]
    file_path: str = tool_input.get("file_path", "")
    if not file_path:
        return {"continue_": True}

    cwd: str = hook_input.get("cwd", os.getcwd())  # type: ignore[union-attr]
    patterns = _load_gitignore_patterns(cwd)

    if _is_sensitive(file_path, cwd, patterns):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Access denied: '{file_path}' matches .env or a .gitignore pattern."
                ),
            }
        }

    return {"continue_": True}
