# MCP Explorer - Project Overview

## Purpose
MCP Explorer is a TUI (Text User Interface) application for discovering and exploring MCP servers. It provides an interactive interface to:
- Auto-discover MCP servers from Claude Code and GitHub Copilot IntelliJ configurations
- View server capabilities (tools, resources, prompts)
- Preview prompt outputs in real-time
- Validate configuration files
- Proxy multiple MCP servers through a single unified endpoint

## Tech Stack
- **Language**: Python 3.11+
- **UI Framework**: Textual (TUI framework)
- **MCP Client**: mcp library (>=0.9.0) with HTTP streaming support
- **Proxy Server**: FastMCP (>=2.0.0) for HTTP streaming transport
- **Models**: Pydantic (>=2.0.0) for domain models
- **Output Formatting**: Rich (>=13.0.0)
- **Config Parsing**: pyjson5 (>=1.6.0) for JSON5 support
- **Build System**: Hatchling
- **Package Manager**: uv (recommended) or pip

## Architecture
The application follows SOLID principles with clean separation of concerns:

### Directory Structure
```
mcp_explorer/
├── models/          # Domain entities (Server, Tool, Resource, Prompt)
│   └── server.py   # ServerType enum: STDIO, HTTP, SSE
├── services/        # Business logic
│   ├── config_loader.py    # Configuration file loading
│   ├── discovery.py        # Server discovery and initialization
│   └── client.py           # MCP protocol communication (stdio, HTTP, SSE)
├── proxy/           # MCP Proxy Server
│   ├── server.py   # FastMCP-based proxy aggregating multiple servers
│   └── logger.py   # Proxy request/response logging
└── ui/              # Textual-based interface
    ├── app.py              # Main application
    ├── screens.py          # UI screens
    ├── widgets.py          # UI widgets
    ├── dialogs.py          # UI dialogs
    └── styles.tcss         # Textual CSS styles
```

### Key Design Patterns
- **Service Layer**: Business logic separated from UI
- **Domain Models**: Pydantic models for type safety and validation
- **Async/Await**: Asynchronous server discovery and communication
- **Separation of Concerns**: Models, Services, UI clearly separated
- **Transport Abstraction**: Unified client interface for stdio, HTTP, and SSE

## Server Type Support

### STDIO (Local Process)
- Launches subprocess and communicates via stdin/stdout
- Used for: Local tools, development, Claude Desktop integration
- Configuration: command, args, env

### HTTP Streaming (Network - FastMCP 2.0)
- Connects to HTTP MCP servers using StreamableHTTP transport
- Uses: `streamablehttp_client` from mcp.client.streamable_http
- Used for: Production deployments, remote servers, multiple clients
- Configuration: url, headers (for authentication)
- Features: Bidirectional streaming, network accessibility, authentication

### SSE (Legacy)
- Connects via Server-Sent Events
- Used for: Backward compatibility with older servers
- Configuration: url, headers
- Note: Limited to server-to-client streaming

## Entry Point
- **Command**: `mcp-explorer`
- **Script**: `mcp_explorer.main:main`
- **Proxy Mode**: `mcp-explorer --proxy`

## Key Features
- Multi-transport support (stdio, HTTP, SSE)
- HTTP streaming with FastMCP 2.0
- Authentication via custom headers
- MCP proxy server aggregation
- Real-time capability discovery
- Async server initialization
