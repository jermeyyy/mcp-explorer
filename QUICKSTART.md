# MCP Explorer - Quick Start Guide

## Installation

```bash
# Install with uv (recommended)
uv pip install -e .

# Or with standard pip
pip install -e .
```

## Usage

### Launch the TUI Application

```bash
mcp-explorer
```

Or with uv:

```bash
uv run mcp-explorer
```

### Navigation

**Main Screen (Server List)**:
- `↑/↓` or `j/k`: Navigate servers
- `Enter`: View server details
- `r`: Refresh server list
- `p`: Open Proxy Configuration
- `l`: Open Log Viewer
- `q`: Quit

**Server Detail Screen**:
- `Tab`: Switch between Tools/Resources/Prompts tabs
- `Enter`: View detailed info for selected item
- `Escape`: Go back to server list
- `q`: Quit

**Proxy Configuration Screen**:
- `Enter`: Toggle server/tool/resource/prompt selection
- `Escape`: Go back
- Start/Stop proxy and save configuration with buttons

**Log Viewer Screen**:
- `F3`: Next search result
- `Shift+F3`: Previous search result
- `Ctrl+F`: Toggle filter sidebar
- `Escape`: Go back

**Detail Screens**:
- `Escape`: Go back
- `p`: Preview prompt (when viewing a prompt)

## What You'll See

### Server List
Shows all discovered MCP servers with:
- Server name
- Description (if available)
- Status (✓ Connected, ○ Disconnected, ✗ Error)
- Type and capabilities ([STDIO] or [SSE], tool/resource/prompt counts)

### Server Details
When you select a server, you'll see:
- **Server Info**: Type, status, command/URL, configuration source
- **Tools Tab**: All available MCP tools with parameters
- **Resources Tab**: Available resources with URIs
- **Prompts Tab**: Prompt templates with arguments

### Example

```
┌─ MCP Explorer ────────────────────────────────────────┐
│                                                       │
│  ● kmp-code-assistant                                 │
│    Compose Multiplatform Code Assistant               │
│    ✓ Connected                                        │
│    [STDIO] 3 tools, 2 resources                       │
│                                                       │
│  ● serena-assistant                                   │
│    ✓ Connected                                        │
│    [STDIO] 18 tools                                   │
│                                                       │
│  ● intellij                                           │
│    ✓ Connected                                        │
│    [STDIO] 12 tools, 5 resources                      │
│                                                       │
│  ● docs-mcp                                           │
│    ✓ Connected                                        │
│    [SSE] 6 tools, 1 resources                         │
│                                                       │
└───────────────────────────────────────────────────────┘
```

## Testing

### Test Configuration Loading

```bash
# Quick config validation
uv run python test_config_only.py
```

Expected output:
```
✅ Found 1 configuration file(s)
✅ Valid JSON
✅ Loaded 4 server(s) total
✅ All tests completed successfully!
```

### Test App Startup

```bash
# Test imports and basic functionality
uv run python test_app_startup.py
```

Expected output:
```
✅ All tests passed! App should start correctly.
```

## Troubleshooting

### No servers found

**Issue**: "No MCP servers found. Check your configuration."

**Solution**:
1. Check if you have a config file in one of these locations:
   - `~/Library/Application Support/Claude/claude_desktop_config.json` (Claude Code)
   - `~/.config/github-copilot/intellij/mcp.json` (GitHub Copilot)
   - `~/.config/mcp/config.json`
   - `~/.mcp/config.json`
   - `./mcp.json` or `./.mcp.json`

2. Validate your config:
   ```bash
   uv run python test_config_only.py
   ```

### Config validation errors

**Issue**: "Invalid JSON/JSON5" error

**Solution**:
- Check JSON syntax (keys must be in quotes for strict JSON)
- Or use JSON5 format (unquoted keys allowed)
- Look for missing commas, brackets, or quotes
- Check the error message for line/column numbers

### Server connection errors

**Issue**: Server shows "✗ Error" status

**Possible causes**:
1. **Command not found**: Check if the command exists
   ```bash
   which uv  # or java, node, etc.
   ```

2. **Wrong path**: Verify paths in config are absolute and correct

3. **Missing dependencies**: Check if server dependencies are installed

4. **Port already in use**: For SSE servers, check if port is available

5. **Environment variables**: Verify required env vars are set

### JSON5 not working

**Issue**: Config with unquoted keys fails

**Solution**: Make sure `pyjson5` is installed:
```bash
uv pip install pyjson5
# or
pip install pyjson5
```

## Configuration Examples

See the `docs/` directory for examples:
- `docs/claude_config_example.json` - Claude Code format
- `docs/copilot_config_example.json` - GitHub Copilot format
- `docs/CONFIG_FORMATS.md` - Complete format reference

## Next Steps

1. **Explore your servers**: Navigate through tools, resources, and prompts
2. **Preview prompts**: Select a prompt and press `p` to preview
3. **Check configurations**: See which config file each server came from
4. **Refresh as needed**: Press `r` to reload servers after config changes

Enjoy exploring your MCP servers! 🎉
