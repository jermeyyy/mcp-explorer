# HTTP Streaming Support Implementation

## Overview
MCP Explorer now fully supports HTTP streaming MCP servers using FastMCP 2.0's StreamableHTTP transport. This enables connecting to remote MCP servers over HTTP with bidirectional streaming and authentication.

## Implementation Files

### Models (`mcp_explorer/models/server.py`)
- **ServerType enum**: Added `HTTP = "http"` alongside STDIO and SSE
- **MCPServer model**: Added `headers: dict[str, str]` field for HTTP/SSE authentication
- Headers support Bearer tokens, API keys, and custom headers

### Client Service (`mcp_explorer/services/client.py`)

#### Imports
```python
from mcp.client.streamable_http import streamablehttp_client
HTTP_AVAILABLE = True  # Flag for HTTP client availability
```

#### Methods
1. **`connect_to_http_server()`** - New async context manager
   - Connects to HTTP MCP server using `streamablehttp_client`
   - Accepts url and optional headers
   - Returns tuple: (read, write, get_session_id_callback)
   - Manages session lifecycle

2. **`query_server_capabilities()`** - Updated
   - Added HTTP server type case
   - Queries tools, resources, prompts from HTTP servers

3. **`call_tool()`** - Updated
   - Supports executing tools on HTTP servers
   - Passes headers for authentication

4. **`get_prompt_preview()`** - Updated
   - Previews prompts from HTTP servers

#### Updated SSE Methods
- `connect_to_sse_server()` now accepts `headers` parameter
- Passes headers to `sse_client()` for authentication

### Config Loader (`mcp_explorer/services/config_loader.py`)
- Added "http" to valid server types
- Validates HTTP server configuration:
  - Requires `url` field
  - Validates `headers` is a dict if present

### Discovery Service (`mcp_explorer/services/discovery.py`)
- Added HTTP server initialization in `_init_server()`
- Extracts `url` and `headers` from config
- Creates MCPServer instances with HTTP type

### Proxy Server (`mcp_explorer/proxy/server.py`)
- Automatically supports HTTP backend servers
- No changes needed - uses MCPClientService which handles all transports
- Can proxy tools/resources from HTTP servers to clients

## Configuration Example

```json
{
  "mcpServers": {
    "docs-mcp": {
      "type": "http",
      "url": "http://localhost:6280/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      },
      "description": "HTTP streaming MCP server"
    }
  }
}
```

## Technical Details

### StreamableHTTP Transport
- Function: `streamablehttp_client(url, headers={}, timeout=30, sse_read_timeout=300)`
- Returns: `(read_stream, write_stream, get_session_id_callback)`
- Protocol: MCP over HTTP with bidirectional streaming
- Session management: Automatic session ID tracking
- Authentication: Via custom headers

### Error Handling
- HTTP_AVAILABLE flag prevents errors if streamablehttp_client unavailable
- Connection errors marked on server object
- Validation errors reported during config loading

## Benefits
1. **Network Accessibility**: Connect to remote MCP servers
2. **Production Ready**: Recommended transport for deployed servers
3. **Authentication**: Bearer tokens, API keys via headers
4. **Multiple Clients**: HTTP servers support concurrent connections
5. **Bidirectional**: Full streaming support (unlike SSE)
6. **Proxy Compatible**: HTTP backends work through MCP proxy

## Usage

### Direct Connection
```bash
mcp-explorer  # Discovers and connects to HTTP servers from config
```

### Through Proxy
```bash
mcp-explorer --proxy  # HTTP backends accessible through unified proxy
```

## Related Documentation
- `docs/HTTP_STREAMING_SUPPORT.md` - Complete usage guide
- FastMCP 2.0 docs: https://gofastmcp.com/clients/transports
