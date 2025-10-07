# Configuration and Features

## MCP Server Configuration

### Supported Formats
MCP Explorer supports two configuration formats:

1. **Claude Code Config** (Strict JSON)
   - Location: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Top-level key: `"mcpServers"`
   - Supports stdio and HTTP servers

2. **GitHub Copilot IntelliJ Config** (JSON5)
   - Location: `~/.config/github-copilot/intellij/mcp.json`
   - Top-level key: `"servers"`
   - Supports stdio, HTTP, and SSE servers
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

#### HTTP Streaming Servers (FastMCP 2.0)
```json
{
  "mcpServers": {
    "http-server": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN",
        "X-Custom-Header": "value"
      },
      "description": "HTTP streaming server (recommended for production)"
    }
  }
}
```

**HTTP Streaming Features:**
- Uses `streamablehttp_client` from MCP library
- Bidirectional streaming over HTTP
- Custom authentication headers support
- Network accessibility for remote servers
- Multiple concurrent client support
- Recommended transport for production deployments

#### SSE Servers (Legacy)
```json5
{
  "servers": {
    "sse-server": {
      "type": "sse",
      "url": "http://localhost:8080/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      },
      "description": "SSE-based server (legacy, backward compatibility)"
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
- Support for stdio, HTTP, and SSE server types

### UI Features
- Server list with status indicators (✓ Connected, ○ Disconnected, ✗ Error)
- Server details view (command, type, config source)
- Server type badges: [STDIO], [HTTP], [SSE]
- Tools tab: View all available MCP tools with parameters
- Resources tab: Browse available resources with URIs
- Prompts tab: Explore prompt templates with arguments
- Prompt preview: Preview prompt outputs in real-time
- Keyboard-driven navigation

### Validation
- JSON/JSON5 parsing with error messages
- Configuration validation (required fields, server types)
- HTTP server validation (URL and headers)
- Connection error reporting
- Capability discovery errors handled gracefully

## Key Capabilities

### Tools
MCP tools exposed by servers with:
- Name
- Description
- Input schema (parameters)
- Execution through all server types (stdio, HTTP, SSE)

### Resources
MCP resources with:
- URI
- Name
- Description
- MIME type
- Access through all server types

### Prompts
MCP prompt templates with:
- Name
- Description
- Arguments
- Preview capability
- Support for all server types

## Transport Comparison

| Feature | STDIO | HTTP | SSE |
|---------|-------|------|-----|
| Network Access | ❌ | ✅ | ✅ |
| Bidirectional Streaming | ✅ | ✅ | ⚠️ Limited |
| Multiple Clients | ❌ | ✅ | ✅ |
| Authentication | Via env vars | Via headers | Via headers |
| Recommended For | Local tools | Production APIs | Legacy systems |
