# Claude Agent SDK — Learning Platform

A hands-on, runnable curriculum for the [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/). Each topic is a single, self-contained Python file with a docstring explaining the concept and a `main()` you can execute.

## Layout

```text
foundations/             Phase 01 — install, asyncio, options, system_prompt, permissions, cwd, AsyncIterator[Message]
sdk-patterns/            Phase 02 — agent loop, sessions, streaming I/O, message types, ClaudeSDKClient, structured outputs, context windows
tools_mcp/               Phase 03 — @tool decorator, custom tools, in-process & remote MCP, ToolSearch, Bash, WebSearch, file/editor tools
advanced_patterns/       Phase 04 — hooks, permission handling, user approvals, file checkpointing, slash commands, todo tracking, system prompts, extended thinking
productions/             Phase 05 — cost & usage tracking, prompt caching, hallucination reduction, error handling, jailbreak mitigation
multi_agent_n_skills/    Phase 06 — subagents, subagent_type, Skills SDK, skills best practices, plugins, parallel tool use, orchestration, context delegation
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
uv run python tools_mcp/03_in_process_mcp_servers.py
uv run python advanced_patterns/01_hooks.py
uv run python productions/01_cost_and_usage_tracking.py
uv run python multi_agent_n_skills/07_agent_orchestration.py
```

## Suggested path

1. Work through `foundations/` in numeric order — these establish the surface area (`query`, `ClaudeSDKClient`, `ClaudeAgentOptions`, permissions, async iteration).
2. Move to `sdk-patterns/` to see the agent loop, sessions, streaming, and structured outputs in motion.
3. Continue with `tools_mcp/` to extend the agent with your own tools and MCP servers.
4. Layer in `advanced_patterns/` for hooks, fine-grained permissions, checkpointing, slash commands, todos, system-prompt shaping, and extended thinking.
5. Harden with `productions/` — cost tracking, prompt caching, grounding against hallucinations, error handling, and jailbreak defenses.
6. Finish with `multi_agent_n_skills/` to orchestrate subagents, ship Skills/Plugins, and delegate heavy context off the main loop.

## License

See [LICENSE](LICENSE).
