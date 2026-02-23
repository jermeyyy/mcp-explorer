# Implementation Plan: FastMCP 3.0.1 Upgrade for MCP Explorer

## Overview

Upgrade mcp-explorer from FastMCP >=2.0.0 to FastMCP >=3.0.1, replacing the hand-built proxy server with FastMCP v3's native `create_proxy()` + Provider architecture, and adopting new v3 features: middleware pipeline, transforms, session state, visibility control, and CLI tools.

## Current State

- **FastMCP version**: `>=2.0.0` (pyproject.toml)
- **Proxy**: Custom-built in `mcp_explorer/proxy/server.py` — manually discovers backend servers, dynamically generates tool/resource/prompt handlers via `exec()`, and registers them on a `FastMCP` instance
- **Transports**: StdioTransport, StreamableHttpTransport, SSETransport (via `fastmcp.client.transports`)
- **Client**: `fastmcp.Client` with `elicitation_handler` and `log_handler`
- **UI tool terminal**: Connects to local proxy via SSETransport to execute tools
- **No deprecated v2 patterns** in use (no constructor kwargs, already uses `list_tools()` not `get_tools()`)

## Requirements (Validated from Changelog + Upgrade Guide)

### Breaking Changes to Address
1. `create_sse_app` import path may have moved (`fastmcp.server.http`)
2. Decorators now return functions (not `FunctionTool` objects) — low impact since we use function-call registration
3. Context state methods are now async (`await ctx.set_state()`, `await ctx.get_state()`)
4. Metadata namespace: `_fastmcp` → `fastmcp`
5. Background tasks now require optional `[tasks]` extra

### New v3 Features to Leverage
1. **Provider Architecture** — `ProxyProvider`, `FastMCPProvider`, `create_proxy()` for composing servers
2. **Transforms** — `Namespace`, `ToolTransform`, custom transforms replacing manual prefix logic
3. **Middleware Pipeline** — `LoggingMiddleware`, `TimingMiddleware`, `ErrorHandlingMiddleware`, `RateLimitingMiddleware`, `ResponseLimitingMiddleware`, `PingMiddleware`
4. **Session-Scoped State** — `await ctx.set_state()`/`await ctx.get_state()` for per-session persistence
5. **Visibility Control** — `server.enable()`/`server.disable()` with names, tags, components
6. **CLI Tools** — `fastmcp list`, `fastmcp call`, `fastmcp discover`, `fastmcp generate-cli`
7. **Configuration-Based Proxies** — `create_proxy(config_dict)` for multi-server composition
8. **MCP Feature Forwarding** — Automatic sampling, elicitation, logging, progress forwarding through proxies
9. **`@handle_tool_errors`** — Standardized error handling decorator for tools

---

## Tasks

### Phase 1: Core Upgrade (Dependency + Compatibility)

#### Task 1.1: Update Dependency Version
- **Description:** Bump FastMCP version pin in pyproject.toml
- **Files:** [pyproject.toml](pyproject.toml)
- **Changes:**
  - `"fastmcp>=2.0.0"` → `"fastmcp>=3.0.1,<4"`
- **Dependencies:** None
- **Acceptance Criteria:** `uv sync` succeeds, no version conflicts

#### Task 1.2: Verify and Fix Import Paths
- **Description:** Check all FastMCP imports still resolve under v3. Fix any moved modules.
- **Files:**
  - [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py) — `from fastmcp import Context, FastMCP`, `from fastmcp.client.elicitation import ElicitResult`, `from fastmcp.server.http import create_sse_app`
  - [mcp_explorer/services/client.py](mcp_explorer/services/client.py) — `from fastmcp import Client`, `from fastmcp.client.transports import SSETransport, StdioTransport, StreamableHttpTransport`
  - [mcp_explorer/ui/tool_terminal_screen.py](mcp_explorer/ui/tool_terminal_screen.py) — `from fastmcp import Client`, `from fastmcp.client.elicitation import ElicitResult`, `from fastmcp.client.transports import SSETransport`
- **Changes:** Update any import paths that moved in v3
- **Dependencies:** Task 1.1
- **Acceptance Criteria:** All imports resolve, `python -c "from fastmcp import FastMCP, Client, Context"` works

#### Task 1.3: Run Existing Tests
- **Description:** Run `uv run pytest` to identify any breakage from the v3 upgrade
- **Files:** All tests in `tests/`
- **Dependencies:** Task 1.2
- **Acceptance Criteria:** All existing tests pass or failures are cataloged for fixing

---

### Phase 2: Proxy Server Rewrite — `create_proxy()` Architecture

This is the **biggest improvement opportunity**. The current proxy manually discovers servers, dynamically constructs handlers via `exec()`, and registers them. FastMCP v3's `create_proxy()` + multi-server config does this natively with better session isolation and MCP feature forwarding.

#### Task 2.1: Replace Manual Proxy with `create_proxy()` Config-Based Proxy
- **Description:** Replace the hand-built proxy aggregation logic with FastMCP v3's `create_proxy(config)` which natively supports multi-server proxying with automatic namespacing
- **Files:** [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py) (major rewrite)
- **Changes:**
  - Remove `MCPProxyServer._register_tools()`, `_register_resources()`, `_register_prompts()` (all the `exec()` dynamic handler generation)
  - Remove `_forward_elicitation()` — handled automatically by ProxyProvider
  - Convert discovered servers into an `mcpServers` config dict
  - Use `create_proxy(config, name="mcp-explorer-proxy")` to create the proxy
  - The config dict maps server names → transport configs (stdio command/args/env, HTTP url/headers, SSE url/headers)
- **Current code pattern (remove):**
  ```python
  self.mcp = FastMCP("mcp-explorer-proxy")
  # ... 200+ lines of dynamic handler generation via exec()
  ```
- **New code pattern:**
  ```python
  from fastmcp.server import create_proxy

  config = {"mcpServers": {}}
  for server in discovered_servers:
      if server.type == ServerType.STDIO:
          config["mcpServers"][server.name] = {
              "command": server.command,
              "args": server.args,
              "env": server.env,
          }
      elif server.type == ServerType.HTTP:
          config["mcpServers"][server.name] = {
              "url": server.url,
              "transport": "http",
              "headers": server.headers,
          }
      elif server.type == ServerType.SSE:
          config["mcpServers"][server.name] = {
              "url": server.url,
              "transport": "sse",
              "headers": server.headers,
          }

  self.mcp = create_proxy(config, name="mcp-explorer-proxy")
  ```
- **Dependencies:** Task 1.2
- **Acceptance Criteria:**
  - Proxy discovers and aggregates all configured backend servers
  - Tools, resources, prompts from all backends are accessible through the proxy
  - Automatic namespacing prevents name collisions (e.g., `weather_get_forecast`)
  - Elicitation, logging, progress forwarding work automatically
  - ~200 lines of manual handler generation removed

#### Task 2.2: Update Proxy Transport Serving (http_app + SSE)
- **Description:** Verify `self.mcp.http_app()` and SSE serving still work with the `create_proxy()` result. Update `create_sse_app()` import if needed.
- **Files:** [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py) (the Starlette app creation section)
- **Current code:**
  ```python
  Mount("/mcp", app=self.mcp.http_app())
  # and
  from fastmcp.server.http import create_sse_app
  create_sse_app(server=self.mcp, message_path="/message", sse_path="/")
  ```
- **Changes:** Verify these work on the `create_proxy()` result (which returns a `FastMCP` instance). Fix import paths if moved.
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Proxy serves both `/mcp` (StreamableHTTP) and `/sse` (legacy SSE) endpoints

#### Task 2.3: Integrate Custom Proxy Logger as Middleware
- **Description:** Replace the current custom proxy logging approach with FastMCP v3's built-in `LoggingMiddleware` + a custom middleware for the proxy's log viewer feature
- **Files:**
  - [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py)
  - [mcp_explorer/proxy/logger.py](mcp_explorer/proxy/logger.py)
- **Changes:**
  - Create a custom `ProxyLogMiddleware(Middleware)` that captures tool calls, resource reads, and prompt retrievals for the TUI log viewer
  - Add `LoggingMiddleware` for debug logging
  - Wire both via `self.mcp.add_middleware()`
- **New code pattern:**
  ```python
  from fastmcp.server.middleware import Middleware, MiddlewareContext
  from fastmcp.server.middleware.logging import LoggingMiddleware

  class ProxyLogMiddleware(Middleware):
      def __init__(self, log_store):
          self.log_store = log_store

      async def on_call_tool(self, context: MiddlewareContext, call_next):
          self.log_store.log_request("tool_call", context.message.name, context.message.arguments)
          result = await call_next(context)
          self.log_store.log_response("tool_call", context.message.name, result)
          return result

      async def on_read_resource(self, context: MiddlewareContext, call_next):
          self.log_store.log_request("read_resource", str(context.message.uri))
          result = await call_next(context)
          self.log_store.log_response("read_resource", str(context.message.uri), result)
          return result

  self.mcp.add_middleware(ProxyLogMiddleware(self.log_store))
  self.mcp.add_middleware(LoggingMiddleware(include_payloads=True))
  ```
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Log viewer screen shows proxy request/response data via middleware

---

### Phase 3: Adopt v3 Middleware Features

#### Task 3.1: Add Error Handling Middleware
- **Description:** Add `ErrorHandlingMiddleware` to the proxy for standardized error handling and logging
- **Files:** [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py)
- **Changes:**
  ```python
  from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
  self.mcp.add_middleware(ErrorHandlingMiddleware(include_traceback=True, transform_errors=True))
  ```
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Proxy errors are consistently formatted and logged

#### Task 3.2: Add Timing Middleware
- **Description:** Add `TimingMiddleware` to track per-operation execution times, useful for the proxy's performance monitoring
- **Files:** [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py)
- **Changes:**
  ```python
  from fastmcp.server.middleware.timing import TimingMiddleware
  self.mcp.add_middleware(TimingMiddleware())
  ```
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Operation timing logged

#### Task 3.3: Add PingMiddleware for Connection Keepalive
- **Description:** Add `PingMiddleware` to keep long-lived HTTP streaming connections alive
- **Files:** [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py)
- **Changes:**
  ```python
  from fastmcp.server.middleware import PingMiddleware
  self.mcp.add_middleware(PingMiddleware(interval_ms=15000))
  ```
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Long-running proxy connections don't time out

#### Task 3.4: Add Response Limiting Middleware
- **Description:** Add `ResponseLimitingMiddleware` to prevent oversized tool responses from crashing the TUI
- **Files:** [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py)
- **Changes:**
  ```python
  from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
  self.mcp.add_middleware(ResponseLimitingMiddleware(max_size=500_000))
  ```
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Oversized responses gracefully truncated

---

### Phase 4: Enhanced Client Features

#### Task 4.1: Update Tool Terminal to Use StreamableHttpTransport
- **Description:** The tool terminal screen currently connects to the proxy via `SSETransport`. Upgrade to `StreamableHttpTransport` for bidirectional streaming support.
- **Files:** [mcp_explorer/ui/tool_terminal_screen.py](mcp_explorer/ui/tool_terminal_screen.py)
- **Current code (L572):**
  ```python
  transport = SSETransport(url=f"http://localhost:{proxy_port}/sse")
  ```
- **New code:**
  ```python
  transport = StreamableHttpTransport(url=f"http://localhost:{proxy_port}/mcp")
  ```
- **Dependencies:** Task 2.2
- **Acceptance Criteria:** Tool terminal connects via StreamableHTTP; SSE remains as fallback

#### Task 4.2: Expose Pagination Support in Client
- **Description:** FastMCP v3 adds MCP-compliant pagination for `list_*()` calls. For servers with many tools, this prevents timeout/memory issues.
- **Files:** [mcp_explorer/services/client.py](mcp_explorer/services/client.py)
- **Changes:** The FastMCP `Client.list_tools()` now supports pagination automatically. Verify it works correctly when backend servers have large numbers of components. Add optional page size config if needed.
- **Dependencies:** Task 1.2
- **Acceptance Criteria:** Large server component lists load without issues

---

### Phase 5: New Feature Additions

#### Task 5.1: Add Visibility Control to Proxy UI
- **Description:** Leverage FastMCP v3's `server.enable()`/`server.disable()` to allow users to toggle specific servers or tools on/off in the TUI
- **Files:**
  - [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py)
  - [mcp_explorer/ui/screens.py](mcp_explorer/ui/screens.py) (new UI controls)
- **Changes:**
  - Add methods to the proxy for enabling/disabling specific backend servers by name
  - Use `self.mcp.disable(names={...}, components={"tool"})` from v3
  - Add toggle buttons/keybindings in the TUI for per-server visibility
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Users can toggle individual servers on/off in the proxy without restart

#### Task 5.2: Add Server Version Display
- **Description:** FastMCP v3's Client exposes `.server_name` and `.server_version` properties. Display these in the server details panel.
- **Files:**
  - [mcp_explorer/services/client.py](mcp_explorer/services/client.py)
  - [mcp_explorer/ui/widgets.py](mcp_explorer/ui/widgets.py)
  - [mcp_explorer/models/server.py](mcp_explorer/models/server.py)
- **Changes:**
  - Already has `hasattr` guards for `client.server_name`/`client.server_version` — ensure these populate the model
  - Display server name + version in the TUI server details view
- **Dependencies:** Task 1.2
- **Acceptance Criteria:** Server version shown in UI when available

#### Task 5.3: Add `fastmcp discover` Integration
- **Description:** FastMCP v3's CLI can discover servers from Claude Desktop, Cursor, Goose configs via `fastmcp discover`. Integrate this as an additional server discovery source alongside the existing config loader.
- **Files:**
  - [mcp_explorer/services/discovery.py](mcp_explorer/services/discovery.py)
  - [mcp_explorer/services/config_loader.py](mcp_explorer/services/config_loader.py)
- **Changes:**
  - Add optional discovery via FastMCP's name-based server resolution
  - Fall back to existing config file discovery if FastMCP discovery unavailable
- **Dependencies:** Task 1.2
- **Acceptance Criteria:** Additional servers from supported clients auto-discovered

#### Task 5.4: Add Rate Limiting Support (Optional)
- **Description:** Add configurable rate limiting via `RateLimitingMiddleware` to the proxy, useful when proxying production servers
- **Files:** [mcp_explorer/proxy/server.py](mcp_explorer/proxy/server.py)
- **Changes:**
  ```python
  from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
  if config.rate_limit:
      self.mcp.add_middleware(RateLimitingMiddleware(
          max_requests_per_second=config.rate_limit
      ))
  ```
- **Dependencies:** Task 2.1
- **Acceptance Criteria:** Proxy can optionally rate-limit tool calls

---

### Phase 6: Testing & Documentation

#### Task 6.1: Update Existing Tests
- **Description:** Fix any test failures from the upgrade and add tests for new middleware/proxy features
- **Files:** All tests in `tests/`
- **Dependencies:** All previous tasks
- **Acceptance Criteria:** All tests pass (`uv run pytest`)

#### Task 6.2: Update Documentation
- **Description:** Update PROXY_USAGE_GUIDE.md, HTTP_STREAMING_SUPPORT.md, and README.md with v3 features
- **Files:**
  - [PROXY_USAGE_GUIDE.md](PROXY_USAGE_GUIDE.md)
  - [docs/HTTP_STREAMING_SUPPORT.md](docs/HTTP_STREAMING_SUPPORT.md)
  - [README.md](README.md)
- **Dependencies:** All previous tasks
- **Acceptance Criteria:** Docs reflect v3 features and updated API

#### Task 6.3: Format and Lint
- **Description:** Run `uv run ruff format` and `uv run ruff check` on all modified files
- **Files:** All modified files
- **Dependencies:** All previous tasks
- **Acceptance Criteria:** No lint errors

---

## Sequencing

```
Phase 1 (Core Upgrade)
  ├── 1.1 Update dependency
  ├── 1.2 Fix imports
  └── 1.3 Run tests
        │
Phase 2 (Proxy Rewrite) ←── biggest impact
  ├── 2.1 create_proxy() rewrite
  ├── 2.2 Transport serving
  └── 2.3 Logger as middleware
        │
Phase 3 (Middleware)    ←── can parallelize
  ├── 3.1 Error handling
  ├── 3.2 Timing
  ├── 3.3 Ping keepalive
  └── 3.4 Response limiting
        │
Phase 4 (Client)
  ├── 4.1 StreamableHTTP for tool terminal
  └── 4.2 Pagination support
        │
Phase 5 (New Features)  ←── can parallelize
  ├── 5.1 Visibility control UI
  ├── 5.2 Server version display
  ├── 5.3 fastmcp discover integration
  └── 5.4 Rate limiting (optional)
        │
Phase 6 (Testing & Docs)
  ├── 6.1 Tests
  ├── 6.2 Documentation
  └── 6.3 Lint & format
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `create_proxy()` config format doesn't match our server discovery model | High | Verify config schema against FastMCP docs; fall back to manual ProxyProvider instantiation if needed |
| `create_sse_app` removed or moved in v3 | Medium | Check v3 source; may need to use `http_app()` with SSE-compatibility mode or keep SSE as fallback transport |
| Dynamic exec()-based handlers incompatible with v3 decorators returning functions | Medium | create_proxy() eliminates need for exec() entirely — this risk is mitigated by the rewrite |
| Elicitation forwarding behavior changes | Medium | Test with actual elicitation-supporting tools; create_proxy() handles this natively |
| Client transport paths changed | Low | Check v3 import locations; FastMCP maintains backward compat for most client imports |

## Key Benefits After Upgrade

1. **~300 lines of proxy code removed** — replaced by `create_proxy(config)` (~10 lines)
2. **Automatic MCP feature forwarding** — elicitation, sampling, logging, progress handled by framework
3. **Production-grade middleware** — logging, timing, error handling, rate limiting, response size control
4. **Session isolation** — each proxy client gets isolated backend sessions (currently shared)
5. **Connection keepalive** — PingMiddleware prevents HTTP streaming timeouts
6. **Visibility control** — users can toggle servers/tools dynamically
7. **Better error handling** — standardized via ErrorHandlingMiddleware
8. **CLI tools** — `fastmcp discover`, `fastmcp list`, `fastmcp call` available for debugging

## Open Questions

1. Does `create_proxy()` support mixed transport configs (some stdio, some HTTP, some SSE) in the same config dict? — **Likely yes** based on docs showing multi-server configs
2. Should we keep SSE transport support for the tool terminal, or fully switch to StreamableHTTP? — **Recommend dual support** with StreamableHTTP preferred
3. Should rate limiting be enabled by default or only configurable? — **Configurable, off by default**
4. Does the existing Starlette middleware for SSE client tracking need to be preserved? — **Investigate during Task 2.2**
