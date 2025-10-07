# HTTP Streaming Support for MCP Explorer

## Overview

MCP Explorer now supports HTTP streaming servers using FastMCP 2.0's `StreamableHttpTransport`. This is the recommended transport for production MCP deployments, providing efficient bidirectional streaming over HTTP connections.

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

## Features

- **Bidirectional Streaming**: Full support for streaming requests and responses
- **Authentication**: Custom headers for API tokens, OAuth, etc.
- **Network Accessibility**: Connect to remote MCP servers over HTTP
- **Multiple Clients**: HTTP servers can handle concurrent client connections

## Server Types Supported

1. **STDIO** (`"type": "stdio"`) - Local command-line servers
2. **HTTP** (`"type": "http"`) - Network HTTP streaming servers (NEW)
3. **SSE** (`"type": "sse"`) - Legacy SSE servers (backward compatibility)

## Implementation Details

### Changes Made

1. **Server Model** (`mcp_explorer/models/server.py`)
   - Added `ServerType.HTTP` enum value
   - Added `headers` field for HTTP/SSE server authentication

2. **Client Service** (`mcp_explorer/services/client.py`)
   - Added `connect_to_http_server()` method using `streamable_http_client`
   - Updated all server connection methods to support custom headers
   - Added HTTP server support to `query_server_capabilities()`, `call_tool()`, and `get_prompt_preview()`

3. **Config Loader** (`mcp_explorer/services/config_loader.py`)
   - Added HTTP server type validation
   - Added headers validation for HTTP/SSE servers

4. **Discovery Service** (`mcp_explorer/services/discovery.py`)
   - Added HTTP server initialization with URL and headers extraction

### Proxy Server Support

The proxy server (`mcp_explorer/proxy/server.py`) automatically supports HTTP backend servers through the updated client service. When you enable an HTTP MCP server in the proxy configuration, it will:

1. Connect to the HTTP server using the streamable HTTP transport
2. Query its capabilities (tools, resources, prompts)
3. Proxy tool calls and resource reads to the HTTP backend
4. Support multiple concurrent proxy clients

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

| Feature | STDIO | HTTP | SSE |
|---------|-------|------|-----|
| Network Access | ❌ | ✅ | ✅ |
| Bidirectional Streaming | ✅ | ✅ | ⚠️ Limited |
| Multiple Clients | ❌ | ✅ | ✅ |
| Authentication | Via env vars | Via headers | Via headers |
| Recommended For | Local tools | Production APIs | Legacy systems |

## Troubleshooting

### HTTP Client Not Available

If you see "HTTP client not available" errors, ensure you have the MCP library installed (version >= 0.9.0):

```bash
uv sync
# or
pip install --upgrade mcp
```

**Note:** The MCP library's HTTP client function is called `streamablehttp_client` (all lowercase, no underscores between words). This is automatically handled by the client service.

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

## FastMCP 2.0 Reference

For more information on FastMCP's HTTP transport, see:
- [FastMCP Transports Documentation](https://gofastmcp.com/clients/transports)
- [Running FastMCP Servers](https://gofastmcp.com/deployment/running-server)
# HTTP Streaming Support for MCP Explorer

## Overview

MCP Explorer now supports HTTP streaming servers using FastMCP 2.0's `StreamableHttpTransport`. This is the recommended transport for production MCP deployments, providing efficient bidirectional streaming over HTTP connections.

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

## Features

- **Bidirectional Streaming**: Full support for streaming requests and responses
- **Authentication**: Custom headers for API tokens, OAuth, etc.
- **Network Accessibility**: Connect to remote MCP servers over HTTP
- **Multiple Clients**: HTTP servers can handle concurrent client connections

## Server Types Supported

1. **STDIO** (`"type": "stdio"`) - Local command-line servers
2. **HTTP** (`"type": "http"`) - Network HTTP streaming servers (NEW)
3. **SSE** (`"type": "sse"`) - Legacy SSE servers (backward compatibility)

## Implementation Details

### Changes Made

1. **Server Model** (`mcp_explorer/models/server.py`)
   - Added `ServerType.HTTP` enum value
   - Added `headers` field for HTTP/SSE server authentication

2. **Client Service** (`mcp_explorer/services/client.py`)
   - Added `connect_to_http_server()` method using `streamablehttp_client` from `mcp.client.streamable_http`
   - Updated all server connection methods to support custom headers
   - Added HTTP server support to `query_server_capabilities()`, `call_tool()`, and `get_prompt_preview()`

3. **Config Loader** (`mcp_explorer/services/config_loader.py`)
   - Added HTTP server type validation
   - Added headers validation for HTTP/SSE servers

4. **Discovery Service** (`mcp_explorer/services/discovery.py`)
   - Added HTTP server initialization with URL and headers extraction

### Proxy Server Support

The proxy server (`mcp_explorer/proxy/server.py`) automatically supports HTTP backend servers through the updated client service. When you enable an HTTP MCP server in the proxy configuration, it will:

1. Connect to the HTTP server using the streamable HTTP transport
2. Query its capabilities (tools, resources, prompts)
3. Proxy tool calls and resource reads to the HTTP backend
4. Support multiple concurrent proxy clients

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

| Feature | STDIO | HTTP | SSE |
|---------|-------|------|-----|
| Network Access | ❌ | ✅ | ✅ |
| Bidirectional Streaming | ✅ | ✅ | ⚠️ Limited |
| Multiple Clients | ❌ | ✅ | ✅ |
| Authentication | Via env vars | Via headers | Via headers |
| Recommended For | Local tools | Production APIs | Legacy systems |

## Troubleshooting

### HTTP Client Not Available

If you see "HTTP client not available" errors, ensure you have the latest MCP library:

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

## FastMCP 2.0 Reference

For more information on FastMCP's HTTP transport, see:
- [FastMCP Transports Documentation](https://gofastmcp.com/clients/transports)
- [Running FastMCP Servers](https://gofastmcp.com/deployment/running-server)

