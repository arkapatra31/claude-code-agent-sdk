# Claude Code Agent SDK

A Python client implementation for the Claude Agent SDK, providing a simple interface to interact with Claude AI agents with built-in security features.

## Features

- **Singleton Pattern**: Efficient instance management with `ClaudeCodeAgentClient`
- **Async Support**: Built with async/await for non-blocking operations
- **Configurable Tools**: Customize available tools (Read, Write, Edit, AskUserQuestion)
- **Environment-based Configuration**: Easy model selection via environment variables
- **Logging**: Integrated logging for debugging and monitoring
- **Security Hooks**: PreToolUse hooks to prevent access to sensitive files (.env, .gitignore patterns)
- **Connection Management**: Automatic connection handling with thread-safe locking

## Prerequisites

- Python 3.13 or higher
- `uv` package manager (recommended) or `pip`

## Installation

1. Clone the repository and navigate to the project directory

2. Create a virtual environment and install dependencies using `uv` or `pip`

3. Set up your environment variables by copying `.env.example` to `.env` and adding:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `ANTHROPIC_MODEL`: Your preferred Claude model (e.g., claude-sonnet-4-20250514)

## Usage

### Basic Usage

1. Get the singleton instance using `ClaudeCodeAgentClient.get_instance()`
2. Call `ensure_connected()` to establish the connection
3. The client is now ready to use with security hooks enabled

### Running the Example

Run the main entry point with `python main.py`. The client initializes automatically with security hooks enabled.

## Project Structure

- **adk_client/claude.py** - Main client implementation
- **adk_client/hooks.py** - Security hooks for sensitive file protection
- **main.py** - Entry point
- **pyproject.toml** - Project configuration
- **.env** - Environment variables (not in git)
- **.gitignore** - Git ignore patterns
- **LICENSE** - License file
- **README.md** - This file

## Configuration

The `ClaudeCodeAgentClient` can be configured with:

- **system_prompt**: Custom system prompt for the agent
- **model**: Claude model to use (set via `ANTHROPIC_MODEL` env var)
- **allowed_tools**: List of tools the agent can use
- **permission_mode**: Permission handling mode (default: "default")
- **hooks**: PreToolUse hooks for security and validation

### Current Allowed Tools:
- `Read`: Read files
- `Write`: Write files
- `Edit`: Edit existing files
- `AskUserQuestion`: Ask clarifying questions

### Security Features

The SDK includes a **sensitive file guard** hook that automatically blocks access to:
- `.env` files and variants (`.env.*`, `*.env`, `.envrc`, `.env.local`, `.env.production`)
- Files matching patterns in `.gitignore` (e.g., `.venv/`, `__pycache__/`, `node_modules/`)

This prevents accidental exposure of sensitive data or modification of protected files.

## Development

### Key Components

#### Connection Management
The client uses a singleton pattern with thread-safe connection handling:
- `ensure_connected()`: Establishes connection if not already connected
- `_connect_lock`: Asyncio lock to prevent race conditions during connection

#### Hook System
Hooks are executed before tool use to enforce security policies:
- **PreToolUse**: Validates tool inputs before execution
- **Sensitive File Guard**: Blocks access to protected files automatically

### Dependencies

This project uses:
- `claude-agent-sdk>=0.1.68`: Official Claude Agent SDK
- `python-dotenv`: Environment variable management

### Adding New Tools

To add new tools, modify the `allowed_tools` list in the `ClaudeCodeAgentClient` initialization within `adk_client/claude.py`. Add your new tool name to the list of allowed tools alongside the existing ones.

### Adding Custom Hooks

To create custom hooks:
1. Create a new async hook function in `adk_client/hooks.py` that accepts `hook_input`, `tool_use_id`, and `context` parameters
2. Implement your validation logic and return appropriate hook output
3. Import your custom hook in `claude.py`
4. Add it to the hooks configuration in the `ClaudeAgentOptions` initialization

## License

See [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open an issue on the GitHub repository.
