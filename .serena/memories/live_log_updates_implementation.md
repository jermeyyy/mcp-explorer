# Live Log Updates Implementation

## Overview
Implemented real-time log updates for the proxy log viewer with a Claude-inspired inline, collapsible UI design.

## Core Architecture

### Callback System (`proxy/logger.py`)
- **ProxyLogger** maintains `_update_callbacks` list for listener registration
- `add_update_callback()` / `remove_update_callback()` methods for callback management
- `_add_entry()` notifies all callbacks when new log entries are added

### Auto-Refresh Mechanism (`ui/log_viewer_screen.py`)
- Registers callback with logger on mount, cleans up on unmount
- Polls every 0.5 seconds with `_check_for_updates()` as backup mechanism
- Tracks `last_entry_count` to detect new entries efficiently
- Uses `_on_new_log_entry()` callback handler for immediate updates

## UI Design - Claude-Inspired Cards

### Visual Structure
Each log entry is a bordered card with:
- **Header**: Status dot (● SUCCESS/ERROR/PENDING), timestamp, operation, duration
- **Content Preview**: Smart truncation (3 lines or 150 chars)
- **Expand/Collapse**: Inline expansion with "Show more/less" button
- **Details Section**: Full parameters, response, and errors when expanded

### Content Collapsing Logic (`ui/log_widgets.py`)
- **Text**: Collapsed if > 3 lines or > 150 characters
- **JSON**: Collapsed if > 3 lines when pretty-printed
- **Errors**: Collapsed if > 100 characters
- Automatically determines if expand button needed via `_has_expandable_content()`

### Styling (`ui/styles.tcss`)
- `.log-entry-card` - bordered cards with hover effects (#2d2d2d on hover)
- `.log-status-dot` - colored indicators (green/red/purple)
- `.log-content-preview` - left border for visual hierarchy
- `.log-expand-btn` - subtle expand/collapse controls
- Color-coded content sections for parameters, responses, errors

## Key Features
1. **Live Updates**: Logs appear in real-time without manual refresh
2. **Inline Expansion**: All details expand within the card, no separate panes
3. **Smart Previews**: Shows essentials at a glance, expand for details
4. **Performance**: Efficient updates, lazy expansion, proper cleanup
5. **Visual Hierarchy**: Status indicators, card layout, color coding

## Files Modified
- `mcp_explorer/proxy/logger.py` - Callback system
- `mcp_explorer/ui/log_widgets.py` - Refactored widget with inline design
- `mcp_explorer/ui/log_viewer_screen.py` - Auto-refresh and callbacks
- `mcp_explorer/ui/styles.tcss` - Claude-inspired card styles

## User Experience
**Before**: Manual refresh, separate detail pane, no previews
**After**: Auto-refresh, inline expansion, smart previews, visual hierarchy

