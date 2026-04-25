"""
Custom tool functions
=====================

Beyond the trivial `add(a,b)` example, custom tools are how you give the
agent capabilities specific to your domain: query a database, hit an
internal API, run a calculation, parse a file, etc.

Patterns to follow:

  1. Validate inputs early. The model will sometimes hand you malformed
     args; raise a clear error or return `isError: True` so the agent
     can self-correct.

  2. Keep return content as text the model can reason about. JSON-encode
     structured results so the model sees keys + values verbatim.

  3. Make tools pure-ish: no global mutation that other tools depend on.
     Pass state via closures or a small registry instead.

  4. Errors are first-class:
        return {"content":[{"type":"text","text":"reason"}], "isError": True}
     The model will read the error and try a different approach.

This file defines a small "weather" tool with realistic shape; the
end-to-end wiring lives in 03_in_process_mcp_servers.py.

Run: uv run python Tools_MCP/02_custom_tool_functions.py
"""

import json
from datetime import datetime, timezone

from claude_agent_sdk import tool

# pretend backend
_FAKE_DB = {
    "london":   {"temp_c": 12, "condition": "rain"},
    "tokyo":    {"temp_c": 18, "condition": "cloudy"},
    "new york": {"temp_c": 7,  "condition": "snow"},
}


@tool(
    name="get_weather",
    description="Return current weather for a city. Units: 'c' or 'f'.",
    input_schema={"city": str, "units": str},
)
async def get_weather(args: dict) -> dict:
    city = (args.get("city") or "").strip().lower()
    units = (args.get("units") or "c").lower()

    if not city:
        return {
            "content": [{"type": "text", "text": "city is required"}],
            "isError": True,
        }
    if units not in ("c", "f"):
        return {
            "content": [{"type": "text", "text": "units must be 'c' or 'f'"}],
            "isError": True,
        }

    row = _FAKE_DB.get(city)
    if not row:
        return {
            "content": [{"type": "text", "text": f"unknown city: {city!r}"}],
            "isError": True,
        }

    temp = row["temp_c"] if units == "c" else round(row["temp_c"] * 9 / 5 + 32, 1)
    payload = {
        "city": city,
        "temperature": temp,
        "units": units,
        "condition": row["condition"],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


if __name__ == "__main__":
    import anyio

    async def smoke() -> None:
        for args in [
            {"city": "London", "units": "c"},
            {"city": "Mars", "units": "c"},
            {"city": "Tokyo", "units": "k"},
            {},
        ]:
            print(args, "->", await get_weather.handler(args))

    anyio.run(smoke)
