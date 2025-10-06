# MCP Configuration Formats

MCP Explorer supports multiple configuration formats used by different tools.

## Format Support

- **JSON**: Strict JSON (standard)
- **JSON5**: Relaxed JSON with unquoted keys, trailing commas, comments (GitHub Copilot IntelliJ)

## Schema Differences

### Claude Code Config

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Format**: Strict JSON

**Schema**:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["path/to/server.js"],
      "env": {
        "API_KEY": "value"
      }
    }
  }
}
```

**Key characteristics**:
- Uses `"mcpServers"` as the top-level key
- Strict JSON format only
- `type` field is optional (defaults to `"stdio"`)
- Does NOT support SSE servers (stdio only)

### GitHub Copilot IntelliJ Config

**Location**: `~/.config/github-copilot/intellij/mcp.json`

**Format**: JSON5 (unquoted keys allowed)

**Schema**:
```json5
{
  "servers": {
    "stdio-server": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "server.py"],
      "env": {},
      "description": "Optional description"
    },
    "sse-server": {
      type: "sse",  // Unquoted keys allowed in JSON5
      url: "http://localhost:8080/sse"
    }
  }
}
```

**Key characteristics**:
- Uses `"servers"` as the top-level key (not `"mcpServers"`)
- Supports JSON5 format (unquoted keys, trailing commas)
- `type` field explicitly set (`"stdio"` or `"sse"`)
- Supports both stdio and SSE servers
- Optional `description` field

## Comparison Table

| Feature | Claude Code | GitHub Copilot IntelliJ |
|---------|-------------|------------------------|
| Config key | `mcpServers` | `servers` |
| Format | Strict JSON | JSON5 |
| Unquoted keys | ❌ No | ✅ Yes |
| Trailing commas | ❌ No | ✅ Yes |
| Comments | ❌ No | ✅ Yes (// and /* */) |
| SSE support | ❌ No | ✅ Yes |
| Type field | Optional | Explicit |
| Description field | ❌ No | ✅ Yes |

## MCP Explorer Support

MCP Explorer supports **both formats**:

1. **Auto-detection**: Tries strict JSON first, falls back to JSON5
2. **Schema-agnostic**: Accepts both `"mcpServers"` and `"servers"` keys
3. **Full feature support**: Handles stdio and SSE servers from both sources
4. **Validation**: Validates required fields based on server type

## Configuration Locations (in priority order)

1. `~/Library/Application Support/Claude/claude_desktop_config.json` (Claude Code)
2. `~/.config/github-copilot/intellij/mcp.json` (GitHub Copilot IntelliJ)
3. `~/.config/mcp/config.json` (Custom)
4. `~/.mcp/config.json` (Custom)
5. `./mcp.json` (Project-specific)
6. `./.mcp.json` (Project-specific, hidden)

## Example Configs

### Stdio Server (works in both)

**Claude Code style**:
```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "server.py"],
      "env": {}
    }
  }
}
```

**GitHub Copilot style**:
```json5
{
  "servers": {
    "my-server": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "server.py"],
      "env": {},
      "description": "My MCP server"
    }
  }
}
```

### SSE Server (GitHub Copilot only)

```json5
{
  "servers": {
    "sse-server": {
      "type": "sse",
      "url": "http://localhost:8080/sse",
      "description": "HTTP-based MCP server"
    }
  }
}
```

### Complex Example (GitHub Copilot)

```json5
{
  "servers": {
    // Python server via uv
    "python-server": {
      type: "stdio",
      command: "uv",
      args: [
        "run",
        "--directory",
        "/path/to/project",
        "server.py"
      ],
      env: {
        "API_KEY": "secret"
      },
      description: "Python-based MCP server",
    },  // Trailing comma allowed

    // Java server (IntelliJ)
    "intellij": {
      type: "stdio",
      command: "/Applications/IntelliJ.app/Contents/jbr/Contents/Home/bin/java",
      args: [
        "-classpath",
        "/path/to/jar",
        "com.example.Main"
      ],
      env: {
        "PORT": "8080"
      }
    },

    // SSE server
    "docs-server": {
      type: "sse",
      url: "http://localhost:6280/sse"
    }
  }
}
```

## Migration Guide

### From Claude Code to GitHub Copilot

1. Change `"mcpServers"` → `"servers"`
2. Add `"type": "stdio"` to each server
3. Optionally add `"description"` fields
4. Can use JSON5 features (unquoted keys, comments, trailing commas)

### From GitHub Copilot to Claude Code

1. Change `"servers"` → `"mcpServers"`
2. Remove `"type"` field (assumed to be stdio)
3. Remove `"description"` field (not supported)
4. Convert to strict JSON (quote all keys, remove trailing commas, remove comments)
5. Remove SSE servers (not supported)

## Validation Rules

### Stdio Server
- **Required**: `command` (string)
- **Optional**: `args` (array), `env` (object), `description` (string)
- **Type**: `"stdio"` or omitted (defaults to stdio)

### SSE Server
- **Required**: `url` (string), `type: "sse"`
- **Optional**: `description` (string)
- **Not applicable**: `command`, `args`, `env`
