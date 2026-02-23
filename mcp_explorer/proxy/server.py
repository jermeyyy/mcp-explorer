"""MCP Proxy Server implementation using FastMCP v3 create_proxy() and middleware."""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any

from fastmcp.server import create_proxy
from fastmcp.server.middleware import Middleware, MiddlewareContext, PingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.middleware import CallNext, PromptResult, ResourceResult, ToolResult
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware
from mcp import types as mt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..models import MCPServer, ProxyConfig, ServerType
from .logger import ProxyLogger


class SSEClientTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track SSE client connections and disconnections."""

    def __init__(self, app, proxy_server: "ProxyServer"):
        super().__init__(app)
        self.proxy_server = proxy_server

    async def dispatch(self, request: Request, call_next) -> Response:
        """Track SSE client connections."""
        # Only track SSE endpoint requests
        if request.url.path.startswith("/sse"):
            # Generate unique client ID
            client_id = str(uuid.uuid4())
            remote_addr = request.client.host if request.client else "unknown"

            # Register the client
            self.proxy_server.register_client(client_id, remote_addr)

            try:
                # Process the request
                response = await call_next(request)
                return response
            finally:
                # Unregister the client when connection closes
                self.proxy_server.unregister_client(client_id, "connection_closed")
        else:
            # For non-SSE requests, just pass through
            return await call_next(request)


class ProxyLogMiddleware(Middleware):
    """Custom middleware that captures proxy operations for the TUI log viewer.

    Logs tool calls, resource reads, and prompt gets with timing.
    """

    def __init__(self, proxy_logger: ProxyLogger, enable_logging: bool = True) -> None:
        self.proxy_logger = proxy_logger
        self.enable_logging = enable_logging

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """Log tool calls with timing."""
        tool_name = context.message.name
        arguments = context.message.arguments or {}
        # Extract server name from prefixed tool name (format: server_tool)
        server_name, _, original_tool_name = tool_name.partition("_")
        if not original_tool_name:
            # No prefix found, use full name
            server_name = "unknown"
            original_tool_name = tool_name

        start_time = time.time()
        try:
            result = await call_next(context)
            duration_ms = (time.time() - start_time) * 1000

            if self.enable_logging:
                self.proxy_logger.log_tool_call(
                    server_name=server_name,
                    tool_name=original_tool_name,
                    parameters=arguments,
                    response=str(result),
                    duration_ms=duration_ms,
                )
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            if self.enable_logging:
                self.proxy_logger.log_tool_call(
                    server_name=server_name,
                    tool_name=original_tool_name,
                    parameters=arguments,
                    error=str(e),
                    duration_ms=duration_ms,
                )
            raise

    async def on_read_resource(
        self,
        context: MiddlewareContext[mt.ReadResourceRequestParams],
        call_next: CallNext[mt.ReadResourceRequestParams, ResourceResult],
    ) -> ResourceResult:
        """Log resource reads with timing."""
        resource_uri = str(context.message.uri)
        # Extract server name from prefixed URI (format: server://original_uri)
        server_name = "unknown"
        if "://" in resource_uri:
            potential_server = resource_uri.split("://", 1)[0]
            # Only treat as server prefix if it looks like a server name
            # (not a standard scheme like http, https, file, etc.)
            if potential_server not in ("http", "https", "file", "ftp"):
                server_name = potential_server

        start_time = time.time()
        try:
            result = await call_next(context)
            duration_ms = (time.time() - start_time) * 1000

            if self.enable_logging:
                self.proxy_logger.log_resource_read(
                    server_name=server_name,
                    resource_uri=resource_uri,
                    response=str(result),
                    duration_ms=duration_ms,
                )
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            if self.enable_logging:
                self.proxy_logger.log_resource_read(
                    server_name=server_name,
                    resource_uri=resource_uri,
                    error=str(e),
                    duration_ms=duration_ms,
                )
            raise

    async def on_get_prompt(
        self,
        context: MiddlewareContext[mt.GetPromptRequestParams],
        call_next: CallNext[mt.GetPromptRequestParams, PromptResult],
    ) -> PromptResult:
        """Log prompt gets with timing."""
        prompt_name = context.message.name
        arguments = context.message.arguments or {}
        # Extract server name from prefixed prompt name (format: server_prompt)
        server_name, _, original_prompt_name = prompt_name.partition("_")
        if not original_prompt_name:
            server_name = "unknown"
            original_prompt_name = prompt_name

        start_time = time.time()
        try:
            result = await call_next(context)
            duration_ms = (time.time() - start_time) * 1000

            if self.enable_logging:
                self.proxy_logger.log_prompt_get(
                    server_name=server_name,
                    prompt_name=original_prompt_name,
                    parameters=dict(arguments),
                    response=str(result),
                    duration_ms=duration_ms,
                )
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            if self.enable_logging:
                self.proxy_logger.log_prompt_get(
                    server_name=server_name,
                    prompt_name=original_prompt_name,
                    parameters=dict(arguments),
                    error=str(e),
                    duration_ms=duration_ms,
                )
            raise


class ProxyServer:
    """MCP Proxy Server that aggregates multiple MCP servers using FastMCP v3 create_proxy()."""

    def __init__(
        self,
        servers: list[MCPServer],
        config: ProxyConfig,
        logger: ProxyLogger | None = None,
    ) -> None:
        """Initialize the proxy server.

        Args:
            servers: List of backend MCP servers
            config: Proxy configuration
            logger: Proxy logger instance
        """
        self.servers = servers
        self.config = config
        self.logger = logger or ProxyLogger(max_entries=config.max_log_entries)
        self._running = False
        self._server_task: asyncio.Task | None = None
        self._uvicorn_server: Any | None = None
        self._connected_clients: set[str] = set()

        # Build MCP config from enabled servers only
        mcp_config = self._build_mcp_config()

        # Create proxy using FastMCP v3 native create_proxy()
        # This handles tool/resource/prompt forwarding, elicitation, etc. automatically
        if mcp_config["mcpServers"]:
            self.mcp = create_proxy(mcp_config, name="mcp-explorer-proxy")
        else:
            # No servers enabled — create a bare FastMCP instance
            from fastmcp import FastMCP

            self.mcp = FastMCP("mcp-explorer-proxy")

        # Add middleware stack
        # NOTE: Tool-level and resource-level filtering could be done with transforms later.
        # Currently only server-level filtering is applied (at config construction time).
        self.mcp.add_middleware(
            ProxyLogMiddleware(
                proxy_logger=self.logger,
                enable_logging=config.enable_logging,
            )
        )
        self.mcp.add_middleware(
            ErrorHandlingMiddleware(include_traceback=False, transform_errors=True)
        )
        self.mcp.add_middleware(TimingMiddleware())
        self.mcp.add_middleware(PingMiddleware(interval_ms=30000))
        self.mcp.add_middleware(ResponseLimitingMiddleware(max_size=1_000_000))

        if config.rate_limit:
            from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

            self.mcp.add_middleware(
                RateLimitingMiddleware(max_requests_per_second=config.rate_limit)
            )

    def _build_mcp_config(self) -> dict[str, Any]:
        """Build an MCPConfig dict from enabled servers.

        Only servers that pass ProxyConfig.is_server_enabled() are included.
        """
        mcp_servers: dict[str, Any] = {}

        for server in self.servers:
            config_file_path = server.source_file or ""
            if not self.config.is_server_enabled(config_file_path, server.name):
                continue

            if server.server_type == ServerType.STDIO:
                entry: dict[str, Any] = {"command": server.command, "args": server.args}
                if server.env:
                    entry["env"] = server.env
                mcp_servers[server.name] = entry

            elif server.server_type == ServerType.HTTP:
                entry = {
                    "url": server.url,
                    "transport": "streamable-http",
                }
                if server.headers:
                    entry["headers"] = server.headers
                mcp_servers[server.name] = entry

            elif server.server_type == ServerType.SSE:
                entry = {
                    "url": server.url,
                    "transport": "sse",
                }
                if server.headers:
                    entry["headers"] = server.headers
                mcp_servers[server.name] = entry

        return {"mcpServers": mcp_servers}

    async def start(self) -> None:
        """Start the proxy server with both HTTP (/mcp) and SSE (/sse) endpoints."""
        self._running = True

        # Set up log file
        log_dir = Path.home() / ".mcp-explorer" / "proxy-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"proxy-{int(time.time())}.jsonl"
        self.logger.set_log_file(log_file)

        # Count enabled servers
        enabled_count = sum(
            1 for s in self.servers if self.config.is_server_enabled(s.source_file or "", s.name)
        )

        # Log server start
        if self.config.enable_logging:
            msg = (
                f"Proxy server starting on http://localhost:{self.config.port} "
                f"with {enabled_count} enabled servers\n"
                f"  HTTP endpoint: http://localhost:{self.config.port}/mcp\n"
                f"  SSE endpoint:  http://localhost:{self.config.port}/sse"
            )
            self.logger.log_server_started(
                port=self.config.port,
                enabled_servers=enabled_count,
                message=msg,
            )

        try:
            # Import required modules
            import uvicorn
            from fastmcp.server.http import create_sse_app
            from starlette.routing import Mount

            # Create SSE sub-app for legacy transport support
            sse_app = create_sse_app(server=self.mcp, message_path="/message", sse_path="/")

            # Use http_app() with default /mcp path — its lifespan manages the session manager
            app = self.mcp.http_app()

            # Add SSE endpoint for legacy transport support
            app.routes.append(Mount("/sse", app=sse_app))

            # Track SSE client connections
            app.add_middleware(SSEClientTrackingMiddleware, proxy_server=self)

            # Run the combined app with uvicorn
            config = uvicorn.Config(
                app,
                host="localhost",
                port=self.config.port,
                log_level="error",  # Reduce noise
            )
            server = uvicorn.Server(config)

            # Store server instance and task for cleanup
            self._uvicorn_server = server
            self._server_task = asyncio.create_task(server.serve())
            await self._server_task

        except Exception as e:
            # Log server error
            if self.config.enable_logging:
                self.logger.log_server_error(
                    error=str(e),
                    details={"port": self.config.port, "exception_type": type(e).__name__},
                )
            raise

    async def stop(self) -> None:
        """Stop the proxy server."""
        self._running = False

        # Log server stop
        if self.config.enable_logging:
            self.logger.log_server_stopped(
                message="Proxy server shutting down",
            )

        # Shut down the uvicorn server properly to release the port
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True
            # Wait for server to signal shutdown
            await asyncio.sleep(0.2)

        # Stop the server task
        if self._server_task and not self._server_task.done():
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
            except Exception as e:
                print(f"Error stopping server: {e}")

        # Give the OS time to release the socket
        await asyncio.sleep(0.3)

        self._server_task = None
        self._uvicorn_server = None

    def is_running(self) -> bool:
        """Check if the proxy server is running."""
        return self._running

    def get_connected_client_count(self) -> int:
        """Get the number of currently connected SSE clients.

        Returns:
            Number of connected clients
        """
        return len(self._connected_clients)

    def register_client(self, client_id: str, remote_addr: str | None = None) -> None:
        """Register a new connected client.

        Args:
            client_id: Unique client identifier
            remote_addr: Client's remote address
        """
        self._connected_clients.add(client_id)
        if self.config.enable_logging:
            self.logger.log_client_connected(client_id=client_id, remote_addr=remote_addr)

    def unregister_client(self, client_id: str, reason: str | None = None) -> None:
        """Unregister a disconnected client.

        Args:
            client_id: Unique client identifier
            reason: Disconnection reason
        """
        self._connected_clients.discard(client_id)
        if self.config.enable_logging:
            self.logger.log_client_disconnected(client_id=client_id, reason=reason)

    def enable_server(self, server_name: str) -> None:
        """Enable a specific backend server by name."""
        self.mcp.enable(names={server_name})

    def disable_server(self, server_name: str) -> None:
        """Disable a specific backend server by name."""
        self.mcp.disable(names={server_name})
