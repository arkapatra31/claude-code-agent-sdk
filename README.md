# Claude Agent SDK — Learning Platform

A hands-on, runnable curriculum for the [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/). Each topic is a single, self-contained Python file with a docstring explaining the concept and a `main()` you can execute.

## Layout

```text
foundations/    Phase 01 — install, asyncio, options, system_prompt, permissions, cwd, AsyncIterator[Message]
sdk-patterns/   Phase 02 — agent loop, sessions, streaming I/O, message types, ClaudeSDKClient, structured outputs, context windows
Tools_MCP/      Phase 03 — @tool decorator, custom tools, in-process & remote MCP, ToolSearch, Bash, WebSearch, file/editor tools
```

## Prerequisites

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- `ANTHROPIC_API_KEY` exported in your environment (or set in `.env`)
- Node.js (the SDK launches the bundled `claude` CLI under the hood)

## Setup

```bash
uv sync
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env
```

## Running an example

Every file is independently runnable:

```bash
uv run python foundations/03_query_basics.py
uv run python sdk-patterns/01_agent_loop.py
uv run python Tools_MCP/03_in_process_mcp_servers.py
```

## Suggested path

1. Work through `foundations/` in numeric order — these establish the surface area (`query`, `ClaudeSDKClient`, `ClaudeAgentOptions`, permissions, async iteration).
2. Move to `sdk-patterns/` to see the agent loop, sessions, streaming, and structured outputs in motion.
3. Finish with `Tools_MCP/` to extend the agent with your own tools and MCP servers.

## License

See [LICENSE](LICENSE).
