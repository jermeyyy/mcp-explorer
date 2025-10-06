# MCP Explorer Proxy - Usage Guide

## 🚀 Overview

MCP Explorer functions as a **fully-featured MCP Proxy Server** that aggregates multiple MCP servers into a single interface. You can:

- ✅ **Aggregate** tools, resources, and prompts from multiple servers
- ✅ **Configure Port** - Choose which port the proxy runs on
- ✅ **Filter** which capabilities to expose (per-server granular control)
- ✅ **Persist Settings** - Configuration saved to ~/.config/mcp-explorer/proxy-config.toml
- ✅ **Log** all operations with detailed parameters and responses
- ✅ **Search** through logs with topbar search and F3 navigation
- ✅ **Expand** log entries to view full request/response data
- ✅ **Toggle Filters** - Collapsible sidebar to focus on logs

## 📋 Key Features

### 1. Proxy Configuration (Press 'P')
Configure which servers and capabilities to expose through the proxy:

- **Port Selection**: Choose proxy server port (default: 3000)
- **Status Display**: See if proxy is running or stopped at a glance
- **Server Selection**: Check/uncheck servers to enable/disable
- **Tool Filtering**: Expand servers to choose specific tools
- **Resource Filtering**: Select which resources to expose
- **Prompt Filtering**: Control prompt availability
- **Start/Stop Proxy**: Toggle proxy server with visual feedback
- **Save Configuration**: Persist settings to ~/.config/mcp-explorer/proxy-config.toml

### 2. Log Viewer (Press 'L')
Advanced log viewer with clean, focused UI:

- **Connected Clients Display**: Real-time count of active SSE connections shown prominently in stats bar
- **Client Connection Events**: Automatic logging of client connect/disconnect events with timestamps and IP addresses
- **Connected Clients Display**: Real-time count of active SSE connections shown prominently in stats bar
- **Client Connection Events**: Automatic logging of client connect/disconnect events with timestamps and IP addresses
- **Connected Clients Display**: Real-time count of active SSE connections shown prominently in stats bar
- **Client Connection Events**: Automatic logging of client connect/disconnect events with timestamps and IP addresses
- **Connected Clients Display**: Real-time count of active SSE connections shown prominently in stats bar
- **Client Connection Events**: Automatic logging of client connect/disconnect events with timestamps and IP addresses
- **Statistics**: See total calls, success rate, error count, and connected clients
- **Collapsible Filters**: Right sidebar with filter options (Ctrl+F to toggle)
- **Statistics**: See total calls, success rate, error count, and connected clients
- **Expandable Entries**: Click to see full parameters and responses
- **Statistics**: See total calls, success rate, error count, and connected clients
- **Type Filters**: View all, tools only, resources only, prompts only, or errors only
- **Statistics**: See total calls, success rate, error count, and connected clients
- **Search Counter**: Shows current result position (e.g., "3/15")

## 🎯 How to Use

### Step 1: Launch MCP Explorer

```bash
uv run mcp-explorer
```

or

```bash
mcp-explorer
```

### Step 2: Configure the Proxy

1. Press **'P'** to open Proxy Configuration
2. **Set Port** (optional): Change the proxy port in the Port field (default: 3000)
3. **Check/uncheck servers** to enable/disable them
4. Click **'▶'** next to a server to expand and see its capabilities
5. **Check/uncheck** specific tools, resources, or prompts within each server
6. Click **"▶ Start Proxy"** or **"⬛ Stop Proxy"** to toggle proxy server
7. Click **"💾 Save Configuration"** to persist all settings to disk
   - Settings are saved to: `~/.config/mcp-explorer/proxy-config.toml`
   - Settings auto-load on next startup

### Step 3: View Logs

1. Press **'L'** to open the Log Viewer
2. See all proxied operations in the main content area
3. Click **'▶'** on any entry to expand and see full details
4. **Toggle Filters** (Ctrl+F or button in sidebar):
   - Filter sidebar appears on the right
   - Shows filter options and actions
   - Click "Hide Filters" to maximize log viewing space
5. Use type filters to narrow down results:
   - **All**: Show everything
   - **Tools**: Only tool calls
   - **Resources**: Only resource reads
   - **Prompts**: Only prompt gets
   - **Errors Only**: Failed operations

### Step 4: Search Logs

1. Type in the **topbar search input** (top of screen)
2. Press **Enter** to execute search
3. See result counter: "3/15" means you're on result 3 of 15
4. Use **◀** or **▶** buttons to navigate
5. Or use **F3** to jump to next result
6. Use **Shift+F3** to go to previous result

## ⌨️ Keyboard Shortcuts

### Global
- **Q**: Quit application
- **R**: Refresh server list
- **P**: Open Proxy Configuration
- **L**: Open Log Viewer

### In Log Viewer
- **F3**: Next search result
- **Shift+F3**: Previous search result
- **Ctrl+F**: Toggle filter sidebar
- **Escape**: Go back

### In Proxy Config
- **Escape**: Go back

## 📊 Log Entry Details

Each log entry shows:

- **Timestamp**: When the operation occurred
- **Server/Operation**: Which server and what was called
- **Status**: SUCCESS, ERROR, or PENDING
- **Duration**: How long the operation took

Expanded entries show:

- **Parameters**: Full request parameters (JSON formatted)
- **Response**: Complete response data (JSON formatted)
- **Error**: Error message if operation failed

### Special Entry Types

- **Client Connected**: Logged when an SSE client connects (includes client ID and IP address)
- **Client Disconnected**: Logged when an SSE client disconnects (includes reason)

### Statistics Bar

The stats bar at the top of the log viewer displays:
- **Connected Clients**: Real-time count of active SSE connections
- **Total**: Total number of logged operations
- **Success**: Number of successful operations
- **Errors**: Number of failed operations
- **By Type**: Breakdown by operation type (tool calls, resource reads, prompts, etc.)

## 🌐 Connecting to the Proxy

The proxy server uses **HTTP transport** (via FastMCP 2.0), making it accessible to any MCP client over the network.

### Connection Details

- **Protocol**: HTTP (Streamable HTTP transport)
- **Endpoint**: `http://localhost:{port}` (default: `http://localhost:3000`)
- **Transport Type**: `http` or `sse` (Server-Sent Events for backward compatibility)

### Example Configurations

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "mcp-explorer-proxy": {
      "url": "http://localhost:3000"
    }
  }
}
```

**GitHub Copilot** (`.github/copilot/config.json`):
```json
{
  "mcp": {
    "servers": {
      "mcp-explorer-proxy": {
        "type": "http",
        "url": "http://localhost:3000"
      }
    }
  }
}
```

**Other MCP Clients**:
- Simply configure the client to connect to `http://localhost:{port}`
- The proxy will automatically expose all enabled servers and their capabilities

## 🔧 Proxy Architecture

### Name Prefixing

To avoid conflicts between servers with similar capabilities:

- **Tools**: `{server-name}__{tool-name}`
  - Example: `filesystem__read_file`

- **Resources**: `{server-name}://{resource-uri}`
  - Example: `database://users/list`

- **Prompts**: `{server-name}__{prompt-name}`
  - Example: `assistant__code_review`

### Filtering Logic

- **Server disabled**: No capabilities from that server are exposed
- **No filters set**: All capabilities are exposed (default)
- **Filters set**: Only checked capabilities are exposed

### Logging

- Logs stored in: `~/.mcp-explorer/proxy-logs/`
- Format: JSON Lines (one entry per line)
- In-memory cache: Last 1000 entries (configurable)
- Automatic log rotation when max size reached

## 📁 File Locations

```
~/.config/mcp-explorer/
└── proxy-config.toml     # Saved proxy configuration

~/.mcp-explorer/
├── proxy-logs/           # Log files (if enabled)
- 🔌 **Client Connected**: New SSE client connection
1. **Monitor Connected Clients**: Watch the "Connected Clients" counter in the stats bar to see active SSE connections in real-time

2. **Hide Filters**: Press Ctrl+F to hide the filter sidebar and maximize log viewing space
│   └── proxy-{timestamp}.jsonl
3. **Filter Before Searching**: Use type filters to narrow results before searching
    └── mcp_servers.log
4. **Clear Old Logs**: Click "Clear Logs" button in filter sidebar to remove all entries and free memory

5. **Expand to Copy**: Expand entries to see full JSON - useful for debugging

6. **Monitor in Real-time**: Keep log viewer open while testing to see operations
- 🟢 **Green** (SUCCESS): Operation completed successfully
7. **Error Investigation**: Use "Errors Only" filter to quickly find problems
- 🟣 **Purple** (PENDING): Operation in progress
8. **Search Operators**: Search works on operation names, parameters, and responses
### Log Entry Types
9. **Quick Navigation**: Use topbar search for fast access, results counter shows position
- 📄 **Resource Read**: Resource retrieval
10. **Port Configuration**: Change proxy port if default (3000) conflicts with other services

11. **Persistent Config**: All settings automatically load on next startup after saving

12. **Track Client Activity**: View connection/disconnection events to debug client connectivity issues

1. **Hide Filters**: Press Ctrl+F to hide the filter sidebar and maximize log viewing space

2. **Filter Before Searching**: Use type filters to narrow results before searching

- ✅ SSE client connection tracking
- ✅ Real-time connected clients display
- ✅ Automatic connection/disconnection event logging
- ✅ HTTP transport (network-accessible proxy server)
3. **Clear Old Logs**: Click "Clear Logs" button in filter sidebar to remove all entries and free memory

4. **Expand to Copy**: Expand entries to see full JSON - useful for debugging

5. **Monitor in Real-time**: Keep log viewer open while testing to see operations

6. **Error Investigation**: Use "Errors Only" filter to quickly find problems

7. **Search Operators**: Search works on operation names, parameters, and responses

8. **Quick Navigation**: Use topbar search for fast access, results counter shows position

9. **Port Configuration**: Change proxy port if default (3000) conflicts with other services

10. **Persistent Config**: All settings automatically load on next startup after saving

## ✅ Implemented Features

- ✅ Configuration persistence (save/load from TOML file)
- ✅ Port configuration
- ✅ Topbar search with navigation
- ✅ Collapsible filter sidebar
- ✅ Dynamic proxy status in app header
- ✅ Checkbox-based capability selection
- ✅ Auto-save and auto-load settings
- ✅ HTTP transport (network-accessible proxy server)

## 🔜 Planned Features

- [ ] Export logs to JSON/CSV
- [ ] Real-time log updates (auto-refresh)
- [ ] Log filtering by date/time range
- [ ] Statistics dashboard with graphs
- [ ] Configuration templates (save/load filter presets)
- [ ] Log entry copying to clipboard

## 🐛 Troubleshooting

### Proxy won't start
- Ensure at least one server is enabled
- Check that servers are connected (not in error state)
- View server list with 'R' to refresh

### No logs appearing
- Verify "Proxy Enabled" is ON in configuration
- Check that operations are actually being called
- Ensure logging is enabled in settings

### Search not working
- Try simpler search terms
- Check that entries exist (not filtered out)
- Clear and re-enter search query

### UI not responsive
- Too many log entries - click "Clear Logs"
- Close expanded entries to improve performance
- Restart application if needed
