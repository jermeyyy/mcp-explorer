# MCP Explorer

A powerful TUI (Text User Interface) application for discovering, exploring, and proxying local MCP (Model Context Protocol) servers.

## Features

### Server Discovery & Exploration

- **Automatic Discovery**: Finds all configured MCP servers from Claude Code and GitHub Copilot IntelliJ
- **Server Type Support**: Handles stdio, HTTP streaming, and SSE server types
- **JSON5 Support**: Parses both strict JSON and JSON5 (unquoted keys, comments, trailing commas)
- **Config Validation**: Validates configuration files with helpful error messages
- **Server Overview**: Lists all servers with their status, type, and capabilities at a glance
- **Detailed Exploration**:
  - View available tools with descriptions and parameters
  - Browse resources with URIs and metadata
  - Explore prompt templates with arguments
  - Preview prompt outputs in real-time

### MCP Proxy Server ⭐ NEW

- **Server Aggregation**: Combine multiple MCP servers into a single proxy endpoint
- **Port Configuration**: Choose which port the proxy runs on (default: 3000)
- **Granular Filtering**: Select which tools, resources, and prompts to expose per server
- **Persistent Config**: Settings auto-save to `~/.config/mcp-explorer/proxy-config.toml`
- **Dynamic Status**: App header shows proxy status and port in real-time
- **Advanced Logging**: Track all tool calls, resource reads, and prompt requests
- **Log Viewer**:
  - Topbar search with F3 navigation
  - Collapsible filter sidebar (Ctrl+F to toggle)
  - Expandable entries to view full parameters and responses
  - Type filters (Tools, Resources, Prompts, Errors only)
  - Search result counter and navigation buttons
  - Client connection/disconnection event logging

### Interface

- **Modern TUI**: Built with Textual for a responsive, keyboard-driven interface
- **Professional Design**: Clean, muted color scheme inspired by VS Code
- **Error Reporting**: Clear error messages for configuration issues and connection failures

## Installation

Using `uv` (recommended):

```bash
uv pip install -e .
```

Or with standard pip:

```bash
pip install -e .
```

## Usage

Run the application:

```bash
mcp-explorer
```

### Keyboard Shortcuts

- **Navigation**:
  - `↑/↓` or `j/k`: Navigate lists
  - `Enter`: Select item
  - `Escape`: Go back
  - `Tab`: Switch between tabs

- **Global Actions**:
  - `r`: Refresh server list
  - `p`: Open Proxy Configuration
  - `l`: Open Log Viewer
  - `q`: Quit application

- **In Log Viewer**:
  - `F3`: Next search result
  - `Shift+F3`: Previous search result
  - `Ctrl+F`: Toggle filter sidebar

- **Other**:
  - `p`: Preview prompt (when viewing a prompt)

## Configuration

MCP Explorer automatically discovers servers from (in order):

1. **Claude Code**: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. **GitHub Copilot IntelliJ**: `~/.config/github-copilot/intellij/mcp.json`
3. User MCP config: `~/.config/mcp/config.json`
4. Home directory: `~/.mcp/config.json`
5. Current directory: `./mcp.json` or `./.mcp.json`

Configuration format:

```json
{
  "mcpServers": {
    "my-stdio-server": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/server", "server.py"],
      "env": {
        "API_KEY": "value"
      },
      "description": "Optional description of the server"
    },
    "my-http-server": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      },
      "description": "HTTP streaming MCP server (FastMCP 2.0)"
    },
    "my-sse-server": {
      "type": "sse",
      "url": "http://localhost:8080/sse",
      "description": "SSE-based MCP server (legacy)"
    }
  }
}
```

**Supported Server Types:**
- `stdio`: Launches a local process and communicates via stdin/stdout (default)
- `http`: Connects to a network MCP server via HTTP streaming (FastMCP 2.0 - recommended for production)
- `sse`: Connects to a running server via Server-Sent Events (legacy, backward compatibility)

## Architecture

The application follows SOLID principles with a clean separation of concerns:

- **Models**: Domain entities (Server, Tool, Resource, Prompt)
- **Services**:
  - `MCPDiscoveryService`: Server discovery and initialization
  - `MCPClientService`: MCP protocol communication
  - `MCPConfigLoader`: Configuration file loading
- **UI**: Textual-based interface with screens, widgets, and dialogs

## Development

Install development dependencies:

```bash
uv pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Type checking:

```bash
mypy mcp_explorer
```

Linting:

### v0.3.0 - HTTP Streaming Support (Latest)

✅ **HTTP Streaming Servers**: Full support for HTTP streaming MCP servers using FastMCP 2.0
✅ **StreamableHTTP Transport**: Uses the recommended `streamablehttp_client` for production deployments
✅ **Authentication Headers**: Support for custom headers including Bearer tokens and API keys
✅ **Network Accessibility**: Connect to remote MCP servers over HTTP
✅ **Bidirectional Streaming**: Efficient real-time communication with HTTP servers
✅ **Proxy Support**: HTTP backend servers fully supported in the MCP proxy

### v0.2.0 - SSE Client Tracking
ruff check mcp_explorer
```

## Requirements

- Python 3.11 or higher
## Recent Updates

### v0.2.0 - SSE Client Tracking (Latest)

✅ **SSE Client Tracking**: Log viewer now displays real-time count of connected SSE clients
✅ **Connection Event Logging**: Track individual client connections and disconnections with timestamps
- **docs/HTTP_STREAMING_SUPPORT.md** - HTTP streaming server configuration and usage guide
✅ **Automatic Middleware**: Starlette middleware automatically tracks all SSE connections
✅ **Client Statistics**: View connected client count prominently in the stats bar

### v0.1.0 - Initial Release

### v0.1.0 - Latest Updates

✅ **Fixed ESC Navigation**: ESC key now works correctly in all detail screens
✅ **Fixed Resource Discovery**: Server capabilities (tools, resources, prompts) now discovered without errors
✅ **JSON5 Support**: Handles GitHub Copilot IntelliJ configs with unquoted keys
✅ **Multi-format Support**: Works with both Claude Code and GitHub Copilot configs

See `BUGFIXES.md` for details.

## Documentation

- **QUICKSTART.md** - Quick start guide with examples
- **PROXY_USAGE_GUIDE.md** - Complete guide to using the MCP Proxy feature
- **MCP_PROXY_STATUS.md** - Technical implementation details and status
- **CLAUDE.md** - Instructions for AI assistants using Serena MCP
- **docs/CONFIG_FORMATS.md** - Configuration format reference

## License

MIT
