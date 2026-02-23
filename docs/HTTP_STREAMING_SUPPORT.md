# HTTP Streaming Support for MCP Explorer

## Overview

MCP Explorer supports HTTP streaming servers using FastMCP v3's **StreamableHTTP** transport. This is the **default and recommended transport** for both the proxy server and connecting to remote MCP servers, providing efficient bidirectional streaming over HTTP.

> **Upgrade note (v3):** StreamableHTTP is now the primary transport. The tool terminal connects via the `/mcp` endpoint using `StreamableHttpTransport`. SSE remains available at `/sse` for legacy clients.

## Configuration Format

### Basic HTTP Server

```json
{
  "mcpServers": {
    "my-http-server": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "description": "My HTTP MCP Server"
    }
  }
}
```

### HTTP Server with Authentication Headers

```json
{
  "mcpServers": {
    "authenticated-server": {
      "type": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_TOKEN",
        "X-Custom-Header": "custom-value"
      },
      "description": "Authenticated HTTP MCP Server"
    }
  }
}
```

## Transport Endpoints

### Proxy Server Endpoints

When running the MCP Explorer proxy, two endpoints are available:

| Endpoint | Transport | Status |
|----------|-----------|--------|
| `/mcp` | **StreamableHTTP** | ✅ **Primary** — used by tool terminal and modern clients |
| `/sse` | Server-Sent Events | Available for legacy clients |

The tool terminal now connects to the proxy via the `/mcp` endpoint using `StreamableHttpTransport`, replacing the previous SSE-based connection at `/sse`.

### Backend Server Connections

When connecting to remote MCP servers as backends, the transport is specified per server:

- `"transport": "streamable-http"` — StreamableHTTP (default for `type: "http"`)
- `"transport": "sse"` — SSE for legacy servers

## Features

- **Bidirectional Streaming**: Full support for streaming requests and responses
- **Authentication**: Custom headers for API tokens, OAuth, etc.
- **Network Accessibility**: Connect to remote MCP servers over HTTP
- **Multiple Clients**: HTTP servers can handle concurrent client connections
- **StreamableHTTP Default**: Modern transport used by proxy and tool terminal

## Server Types Supported

1. **STDIO** (`"type": "stdio"`) - Local command-line servers
2. **HTTP** (`"type": "http"`) - Network HTTP streaming servers (StreamableHTTP)
3. **SSE** (`"type": "sse"`) - Legacy SSE servers (backward compatibility)

## Implementation Details

### Changes Made

1. **Server Model** (`mcp_explorer/models/server.py`)
   - `ServerType.HTTP` enum value for HTTP streaming servers
   - `headers` field for HTTP/SSE server authentication

2. **Client Service** (`mcp_explorer/services/client.py`)
   - `connect_to_http_server()` method using `streamablehttp_client`
   - All server connection methods support custom headers
   - HTTP server support in `query_server_capabilities()`, `call_tool()`, and `get_prompt_preview()`

3. **Config Loader** (`mcp_explorer/services/config_loader.py`)
   - HTTP server type validation
   - Headers validation for HTTP/SSE servers

4. **Discovery Service** (`mcp_explorer/services/discovery.py`)
   - HTTP server initialization with URL and headers extraction
   - FastMCP v3 discovery integration (Claude Desktop, Cursor, Goose, etc.)

5. **Proxy Server** (`mcp_explorer/proxy/server.py`)
   - Uses FastMCP v3 `create_proxy()` for automatic server aggregation
   - Dual transport: StreamableHTTP at `/mcp`, SSE at `/sse`
   - Middleware stack for logging, error handling, timing, and more

### Tool Terminal

The tool terminal screen now uses `StreamableHttpTransport` to connect to the proxy at the `/mcp` endpoint. This provides:

- Full bidirectional streaming for tool execution
- Better connection management than SSE
- Consistent transport with the primary proxy endpoint

## Usage Examples

### Connecting to a Remote FastMCP Server

If you have a FastMCP server running with HTTP transport:

```bash
# On the server
fastmcp run server.py --transport http --port 8000
```

Configure it in MCP Explorer:

```json
{
  "mcpServers": {
    "remote-server": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Production Deployment with Authentication

```json
{
  "mcpServers": {
    "production-api": {
      "type": "http",
      "url": "https://mcp.yourcompany.com/api/v1/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_API_TOKEN}",
        "X-API-Version": "1.0"
      },
      "description": "Production MCP API"
    }
  }
}
```

## Comparison with Other Transports

| Feature | STDIO | HTTP (StreamableHTTP) | SSE (Legacy) |
|---------|-------|----------------------|--------------|
| Network Access | ❌ | ✅ | ✅ |
| Bidirectional Streaming | ✅ | ✅ | ⚠️ Limited |
| Multiple Clients | ❌ | ✅ | ✅ |
| Authentication | Via env vars | Via headers | Via headers |
| Recommended For | Local tools | Production APIs & proxy | Legacy systems |
| Proxy Endpoint | N/A | `/mcp` (primary) | `/sse` (legacy) |

## Troubleshooting

### HTTP Client Not Available

If you see "HTTP client not available" errors, ensure you have the latest dependencies:

```bash
uv sync
# or
pip install --upgrade mcp
```

### Connection Errors

- Verify the URL is correct and includes the `/mcp` path
- Check that the server is running and accessible
- Verify any authentication headers are correct

### Headers Not Working

Ensure headers are properly formatted as a JSON object with string values:

```json
{
  "headers": {
    "Authorization": "Bearer token123",
    "Content-Type": "application/json"
  }
}
```

### SSE vs StreamableHTTP

- Modern clients should use the `/mcp` endpoint (StreamableHTTP)
- If a client only supports SSE, use the `/sse` endpoint
- Both endpoints are served by the same FastMCP instance and share all middleware

## FastMCP v3 Reference

For more information on FastMCP v3's transports and proxy features, see:
- [FastMCP Documentation](https://gofastmcp.com/)
- [FastMCP Transports](https://gofastmcp.com/clients/transports)
- [FastMCP Proxy](https://gofastmcp.com/servers/proxy)
