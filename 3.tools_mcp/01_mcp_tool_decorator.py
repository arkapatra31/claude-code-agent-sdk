"""
@tool decorator (a.k.a. @mcp_tool)
==================================

`claude_agent_sdk.tool` is a decorator that turns a plain async Python
function into an `SdkMcpTool` — a tool the model can call as if it were
a remote MCP tool, but executed in-process.

Signature:
    tool(name: str, description: str, input_schema: type | dict) -> decorator

The wrapped function:
    async def fn(args: dict) -> dict
        return {"content": [{"type": "text", "text": "..."}]}

Notes:
  * `input_schema` may be a dict-shaped JSON schema fragment (the simple
    form: {"city": str, "units": str}) or a full TypedDict / dataclass
    style schema. The simple dict form is mapped to JSON Schema for you.
  * The return value MUST follow MCP tool-result shape:
        {"content": [{"type":"text", "text": "..."}], "isError": False}
  * The model invokes it by the FULL name: `mcp__<server>__<tool>`.

This file just defines tools and prints their metadata; see
03_in_process_mcp_servers.py for the end-to-end run.

Run: uv run python Tools_MCP/01_mcp_tool_decorator.py
"""

from claude_agent_sdk import tool


@tool(
    name="add",
    description="Add two integers and return the sum.",
    input_schema={"a": int, "b": int},
)
async def add(args: dict) -> dict:
    total = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": str(total)}]}


@tool(
    name="greet",
    description="Greet a person by name.",
    input_schema={"name": str},
)
async def greet(args: dict) -> dict:
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}


if __name__ == "__main__":
    for t in (add, greet):
        print(f"name={t.name!r} desc={t.description!r} schema={t.input_schema}")
