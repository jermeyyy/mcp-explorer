# Configuration and Features

## MCP Server Configuration

### Supported Formats
MCP Explorer supports two configuration formats:

1. **Claude Code Config** (Strict JSON)
   - Location: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Top-level key: `"mcpServers"`
   - Stdio servers only

2. **GitHub Copilot IntelliJ Config** (JSON5)
   - Location: `~/.config/github-copilot/intellij/mcp.json`
   - Top-level key: `"servers"`
   - Supports both stdio and SSE servers
   - Allows unquoted keys, trailing commas, comments

### Configuration Search Order
1. `~/Library/Application Support/Claude/claude_desktop_config.json`
2. `~/.config/github-copilot/intellij/mcp.json`
3. `~/.config/mcp/config.json`
4. `~/.mcp/config.json`
5. `./mcp.json`
6. `./.mcp.json`

### Server Types

#### Stdio Servers
```json
{
  "mcpServers": {
    "server-name": {
      "command": "uv",
      "args": ["run", "server.py"],
      "env": {
        "API_KEY": "value"
      },
      "description": "Optional description"
    }
  }
}
```

#### SSE Servers
```json5
{
  "servers": {
    "sse-server": {
      "type": "sse",
      "url": "http://localhost:8080/sse",
      "description": "HTTP-based server"
    }
  }
}
```

## Application Features

### Discovery
- Automatic server discovery from multiple config sources
- Parallel server initialization
- Async communication with servers
- Error handling with detailed error messages

### UI Features
- Server list with status indicators (✓ Connected, ○ Disconnected, ✗ Error)
- Server details view (command, type, config source)
- Tools tab: View all available MCP tools with parameters
- Resources tab: Browse available resources with URIs
- Prompts tab: Explore prompt templates with arguments
- Prompt preview: Preview prompt outputs in real-time
- Keyboard-driven navigation

### Validation
- JSON/JSON5 parsing with error messages
- Configuration validation (required fields, server types)
- Connection error reporting
- Capability discovery errors handled gracefully

## Key Capabilities

### Tools
MCP tools exposed by servers with:
- Name
- Description
- Input schema (parameters)

### Resources
MCP resources with:
- URI
- Name
- Description
- MIME type

### Prompts
MCP prompt templates with:
- Name
- Description
- Arguments
- Preview capability
