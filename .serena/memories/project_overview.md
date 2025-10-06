# MCP Explorer - Project Overview

## Purpose
MCP Explorer is a TUI (Text User Interface) application for discovering and exploring local MCP servers. It provides an interactive interface to:
- Auto-discover MCP servers from Claude Code and GitHub Copilot IntelliJ configurations
- View server capabilities (tools, resources, prompts)
- Preview prompt outputs in real-time
- Validate configuration files

## Tech Stack
- **Language**: Python 3.11+
- **UI Framework**: Textual (TUI framework)
- **MCP Client**: mcp library (>=0.9.0)
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
├── services/        # Business logic
│   ├── config_loader.py    # Configuration file loading
│   ├── discovery.py        # Server discovery and initialization
│   └── client.py           # MCP protocol communication
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

## Entry Point
- **Command**: `mcp-explorer`
- **Script**: `mcp_explorer.main:main`
