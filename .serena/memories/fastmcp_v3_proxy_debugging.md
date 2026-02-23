# FastMCP v3 Proxy - Key Learnings

## CRITICAL: Namespace Separator
FastMCP v3 `create_proxy()` with multi-server MCPConfig uses **single underscore** `_` for namespace:
- Tools: `servername_toolname` (NOT `servername__toolname`)
- Prompts: `servername_promptname`
- Resources: `protocol://servername/path`

The old manual proxy used double underscore `__`. All code that constructs or parses prefixed names must use single `_`.

## CRITICAL: http_app() Mounting
**NEVER mount `http_app()` as a sub-app via Starlette `Mount`!**

Starlette `Mount` does NOT propagate lifespan events to sub-apps. Use `http_app()` as the ROOT ASGI app and append routes:
```python
app = self.mcp.http_app()  # root app with lifespan
app.routes.append(Mount("/sse", app=sse_app))  # add SSE routes
app.add_middleware(SSEClientTrackingMiddleware, proxy_server=self)
```

## CRITICAL: http_app() does NOT accept `routes` parameter
`http_app()` signature: `(path, middleware, json_response, stateless_http, transport, event_store, retry_interval)`.
Append routes via `app.routes.append()` after creation.

## CRITICAL: Default streamable_http_path
`fastmcp.settings.streamable_http_path` defaults to `/mcp`. Don't mount at `/mcp` via `Mount` or you get `/mcp/mcp`.

## Transport Setup
- Tool terminal: `StreamableHttpTransport(url=f"http://localhost:{port}/mcp")`
- SSE legacy at `/sse`
- Proxy: `create_proxy(config_dict, name="mcp-explorer-proxy")`

## Files Modified in v3 Upgrade
- `mcp_explorer/proxy/server.py` — create_proxy() + middleware + correct http_app usage
- `mcp_explorer/services/discovery.py` — fastmcp discover integration
- `mcp_explorer/models/proxy_config.py` — added rate_limit field
- `mcp_explorer/ui/tool_terminal_screen.py` — SSETransport → StreamableHttpTransport, `_` separator
- `tests/test_*.py` — added @pytest.mark.asyncio markers
