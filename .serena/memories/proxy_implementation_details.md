# MCP Explorer Proxy Implementation Details

## Overview

MCP Explorer includes a fully-functional proxy server that aggregates multiple MCP servers into dual HTTP endpoints. This proxy uses **FastMCP 2.0** to expose both modern HTTP (/mcp) and legacy SSE (/sse) transports, making it accessible to any MCP client over the network.

## Key Feature: Dual-Transport Support

**Current Implementation**: Uses **FastMCP 2.3.2+** with both HTTP and SSE transports simultaneously

### Supported Endpoints
- **HTTP endpoint**: `http://localhost:{port}/mcp` - Modern streamable HTTP transport (recommended)
- **SSE endpoint**: `http://localhost:{port}/sse` - Legacy Server-Sent Events transport (backward compatibility)

### Benefits of Dual-Transport
- HTTP transport for modern MCP clients (full bidirectional communication)
- SSE transport for backward compatibility with older clients
- Production-ready with enterprise features
- Single server instance serves both endpoints
- Auto-detection of client transport

## Architecture

### Data Models (`mcp_explorer/models/`)

**ProxyConfig** (`proxy_config.py:10-134`)
- Configuration model for proxy server settings
- Uses Pydantic BaseModel for validation
- Key fields:
  - `enabled: bool` - Whether proxy is running
  - `port: int` - Port number (default: 3000)
  - `enabled_servers: Set[str]` - Which servers are enabled
  - `enabled_tools: Dict[str, Set[str]]` - Per-server tool filtering
  - `enabled_resources: Dict[str, Set[str]]` - Per-server resource filtering
  - `enabled_prompts: Dict[str, Set[str]]` - Per-server prompt filtering
  - `enable_logging: bool` - Whether to log operations
  - `max_log_entries: int` - Max in-memory logs (default: 1000)
- Methods:
  - `load()` - Class method to load from `~/.config/mcp-explorer/proxy-config.toml`
  - `save()` - Save to TOML file (uses tomli-w)
  - `is_server_enabled()`, `is_tool_enabled()`, etc. - Check filters
- Persistence: TOML format, converts sets to lists for serialization

**LogEntry** (`log_entry.py:8-72`)
- Tracks individual proxy operations
- Fields:
  - `id: str` - Unique ID (timestamp-based)
  - `timestamp: datetime` - When operation occurred
  - `entry_type: LogEntryType` - TOOL_CALL, RESOURCE_READ, or PROMPT_GET
  - `server_name: str` - Which server handled it
  - `operation_name: str` - Tool/resource/prompt name
  - `parameters: Dict[str, Any]` - Request parameters
  - `response: Optional[Any]` - Response data
  - `error: Optional[str]` - Error message if failed
  - `duration_ms: Optional[float]` - Execution time
- Methods:
  - `get_status()` - Returns "SUCCESS", "ERROR", or "PENDING"
  - `get_display_name()` - Formats server/operation for display

### Proxy Core (`mcp_explorer/proxy/`)

**ProxyLogger** (`logger.py:9-135`)
- Manages logging of all proxy operations
- In-memory storage: List of LogEntry objects (max 1000 by default)
- File persistence: JSON Lines format in `~/.mcp-explorer/proxy-logs/`
- Methods:
  - `log_tool_call()`, `log_resource_read()`, `log_prompt_get()` - Record operations
  - `get_entries()` - Filter logs by type, server, or search query
  - `get_stats()` - Calculate total calls, success rate, error count
  - `clear()` - Remove all log entries
- Search: Case-insensitive substring matching on operation names, params, responses

**ProxyServer** (`server.py:15-312`)
- Aggregates multiple MCP servers using FastMCP 2.3.2+
- **Transport**: Dual endpoints - HTTP at `/mcp` and SSE at `/sse`
- Name prefixing to avoid conflicts:
  - Tools: `{server}__{tool}`
  - Resources: `{server}://{uri}`
  - Prompts: `{server}__{prompt}`
- Architecture:
  - Uses `FastMCP` class for server instance
  - Dynamically registers handlers during initialization
  - Each tool/resource/prompt gets its own handler function
  - Uses Starlette to mount both transport apps
- Key methods:
  - `__init__()` - Creates FastMCP instance and registers all handlers
  - `_setup_handlers()` - Iterates through servers and registers enabled items
  - `_register_tool()` - Registers a single tool with prefixed name
  - `_register_resource()` - Registers a single resource with prefixed URI
  - `_register_prompt()` - Registers a single prompt with prefixed name
  - `start()` - Starts Uvicorn server with both HTTP and SSE apps mounted
  - `stop()` - Stops the proxy server (cancels server task)
  - `is_running()` - Returns running status
- Integrates with ProxyLogger to track all operations

### UI Components (`mcp_explorer/ui/`)

**LogViewerScreen** (`log_viewer_screen.py:17-245`)
- Main screen for viewing logs
- Layout:
  - Topbar: Search input + navigation buttons (◀ ▶) + result counter
  - Main content: Log list with stats header
  - Right sidebar: Collapsible filter panel (toggle with Ctrl+F)
- State management:
  - `current_filter: Optional[LogEntryType]` - Active type filter
  - `errors_only: bool` - Show only errors
  - `search_query: str` - Current search term
  - `search_results: List[LogEntry]` - Filtered results
  - `current_search_index: int` - Position in search results
  - `filters_visible: bool` - Sidebar toggle state
- Key methods:
  - `refresh_logs()` - Update log list based on filters
  - `update_stats()` - Refresh statistics display
  - `highlight_current_result()` - Navigate to search result
  - `action_toggle_filters()` - Show/hide sidebar
- Bindings: F3/Shift+F3 for search, Ctrl+F for sidebar

**ProxyConfigScreen** (`proxy_config_screen.py:113-260`)
- Configure proxy settings
- Layout:
  - Control panel: Port input, status display, action buttons
  - Server list: Expandable server widgets
- ServerConfigWidget (`proxy_config_screen.py:14-110`):
  - Header: Checkbox, server name, counts, expand button
  - Details (when expanded): Checkboxes for tools/resources/prompts
  - Uses `expanded` state to show/hide details
- Features:
  - Port validation (1-65535)
  - Toggle proxy on/off (updates app subtitle)
  - Save to TOML file
  - Real-time checkbox updates

**MCPExplorerApp** (`app.py:17-151`)
- Main application class
- Proxy-related:
  - `proxy_config: ProxyConfig` - Loaded from file on init
  - `proxy_logger: ProxyLogger` - Shared logger instance
  - `proxy_server: Optional[ProxyServer]` - Proxy server instance
  - `update_subtitle()` - Updates header with proxy status
  - `sub_title` property shows "Proxy: ON @localhost:3000" or "Proxy: OFF"
- Actions:
  - `action_show_proxy_config()` - Press 'P'
  - `action_show_logs()` - Press 'L'

**LogEntryWidget** (`log_widgets.py:11-115`)
- Expandable log entry in list view
- Collapsed view shows: timestamp, operation, status, duration
- Expanded view shows: parameters, response, error (if any)
- Toggle state with expand button
- Uses `recompose()` to rebuild on expand/collapse

### Styling (`styles.tcss`)

**Log Viewer Styles** (lines 279-354)
- `#log-search-bar`: Topbar with search input and buttons
- `#log-content`: Horizontal container for logs and sidebar
- `#log-list-container`: Main content area (width: 1fr)
- `#filter-sidebar`: Right sidebar (width: 20), collapsible
- `.search-nav-btn`: Navigation buttons (width: 5)
- `.search-results`: Result counter (width: 12, centered)

**Proxy Config Styles** (lines 425-542)
- `#proxy-control-panel`: Top section with port/status
- `.proxy-config-title`: Centered title
- `.port-input`: Port input field (width: 10)
- `.proxy-status`: Status label with color
- `.proxy-running`: Green (#89d185)
- `.proxy-stopped`: Gray (#858585)
- `.server-config-widget`: Individual server container
- `.server-checkbox`: Checkbox for server enable/disable

**Color Scheme**
- Background: #1e1e1e (dark charcoal)
- Primary accent: #569cd6 (soft blue)
- Success: #89d185 (muted green)
- Error: #f48771 (soft coral)
- Text: #d4d4d4 (light gray)
- Secondary bg: #252525, #2d2d2d

## Key Implementation Patterns

### FastMCP 2.3.2+ Dual-Transport Setup
```python
from fastmcp import FastMCP
from fastmcp.server.http import create_sse_app
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn

# Initialize FastMCP server
self.mcp = FastMCP("mcp-explorer-proxy")

# Create Starlette app with both transports
app = Starlette(
    routes=[
        Mount("/mcp", app=self.mcp.http_app()),  # Modern HTTP transport
        Mount("/sse", app=create_sse_app(        # Legacy SSE transport
            server=self.mcp,
            message_path="/message",
            sse_path="/"
        )),
    ]
)

# Run with Uvicorn
config = uvicorn.Config(app, host="localhost", port=3000, log_level="error")
server = uvicorn.Server(config)
await server.serve()
```

### Dynamic Handler Registration
```python
def _register_tool(self, server_name: str, tool: Any) -> None:
    """Register a single tool with the FastMCP server."""
    prefixed_name = f"{server_name}__{tool.name}"
    description = f"[{server_name}] {tool.description or tool.name}"
    
    async def tool_handler(**kwargs: Any) -> str:
        # Handler implementation with logging
        return result
    
    self.mcp.tool(name=prefixed_name, description=description)(tool_handler)
```

### Config Persistence
```python
# Load config on app startup
self.proxy_config = ProxyConfig.load()

# Save when user clicks save button
self.config.save()

# TOML format with sets converted to lists
data = {
    "enabled": self.enabled,
    "port": self.port,
    "enabled_servers": list(self.enabled_servers),
    # ...
}
```

### Log Filtering
```python
# Get filtered entries
entries = self.logger.get_entries(
    entry_type=self.current_filter,  # Optional: TOOL_CALL, RESOURCE_READ, PROMPT_GET
    search_query=self.search_query or None  # Optional: substring search
)

# Filter by errors only
if self.errors_only:
    entries = [e for e in entries if e.error is not None]
```

## Common Modifications

### Adding New Transport Types
To add additional transports beyond HTTP and SSE:
```python
app = Starlette(
    routes=[
        Mount("/mcp", app=self.mcp.http_app()),
        Mount("/sse", app=create_sse_app(self.mcp, "/message", "/")),
        Mount("/custom", app=your_custom_app),  # Add custom transport
    ]
)
```

### Adding New Filter Type
1. Add enum value to `LogEntryType` in `log_entry.py`
2. Add log method to `ProxyLogger` (e.g., `log_new_type()`)
3. Add filter button in `log_viewer_screen.py` compose()
4. Add handler method (e.g., `filter_new_type()`)
5. Add to `set_active_filter()` button list

### Changing Port Range
- Edit `ProxyConfig` port field validator
- Update `update_port()` in `ProxyConfigScreen`

### Adding Config Field
1. Add field to `ProxyConfig` model
2. Update `save()` to include in TOML data
3. Update `load()` to read and convert (if needed)
4. Add UI control in `ProxyConfigScreen`

## Connection Instructions

### For MCP Clients

The proxy server exposes two HTTP endpoints that any MCP client can connect to:

**HTTP Endpoint (Recommended)**: `http://localhost:{port}/mcp` (default: `http://localhost:3000/mcp`)
**SSE Endpoint (Legacy)**: `http://localhost:{port}/sse` (default: `http://localhost:3000/sse`)

**Configuration Example** (for Claude Desktop with HTTP):
```json
{
  "mcpServers": {
    "mcp-explorer-proxy": {
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

**Configuration Example** (for GitHub Copilot with SSE):
```json
{
  "mcp": {
    "servers": {
      "mcp-explorer-proxy": {
        "type": "sse",
        "url": "http://localhost:3000/sse"
      }
    }
  }
}
```

### Connecting to the Proxy

1. Start MCP Explorer: `mcp-explorer`
2. Press 'P' to configure proxy
3. Enable desired servers and their tools/resources/prompts
4. Set port (default: 3000)
5. Save configuration
6. Start proxy server
7. Configure your MCP client to connect to either:
   - `http://localhost:{port}/mcp` (modern HTTP - recommended)
   - `http://localhost:{port}/sse` (legacy SSE - backward compatibility)

## Testing Notes

- Config file: Check `~/.config/mcp-explorer/proxy-config.toml` after save
- Log files: Check `~/.mcp-explorer/proxy-logs/` for JSON Lines
- HTTP endpoint: Test with `curl http://localhost:3000/mcp` or MCP client
- SSE endpoint: Test with `curl http://localhost:3000/sse` or legacy SSE client
- Both endpoints should return HTTP 307 (Temporary Redirect) for basic GET requests
- Search: Test with special chars, case sensitivity, empty results
- Filters: Test combination of type filter + search + errors only
- UI: Test expand/collapse, sidebar toggle, search navigation
- Port validation: Test invalid ports (0, -1, 70000, "abc")

## Performance Considerations

- Max log entries (1000) prevents memory issues
- Filter sidebar collapse improves rendering with many logs
- Expandable entries avoid rendering large JSON by default
- Search is in-memory (fast for 1000 entries)
- File logging is async (doesn't block UI)
- Dual transports allow both modern and legacy clients
- Single Uvicorn server handles both endpoints efficiently

## Dependencies

- `textual` - TUI framework
- `pydantic` - Data validation
- `tomli-w` - TOML writing
- `fastmcp>=2.3.2` - FastMCP 2.0 framework with modern HTTP and legacy SSE support
- `uvicorn` - ASGI server for running both transports
- `starlette` - Web framework for mounting multiple apps
- Python 3.11+ includes `tomllib` for reading TOML files
