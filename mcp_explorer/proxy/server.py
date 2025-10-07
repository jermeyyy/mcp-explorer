"""MCP Proxy Server implementation."""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..models import MCPServer, ProxyConfig
from ..services import MCPClientService
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


class ProxyServer:
    """MCP Proxy Server that aggregates multiple MCP servers."""

    def __init__(
        self,
        servers: List[MCPServer],
        config: ProxyConfig,
        logger: Optional[ProxyLogger] = None,
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
        self.client_service = MCPClientService()
        self._running = False
        self._server_task: Optional[asyncio.Task] = None
        self._uvicorn_server: Optional[Any] = None
        self._connected_clients: set[str] = set()

        # Initialize FastMCP server
        self.mcp = FastMCP("mcp-explorer-proxy")

        # Register dynamic handlers
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP server request handlers."""
        # Create a proxy tool for each enabled server's tools
        for server in self.servers:
            config_file_path = server.source_file or ""
            if not self.config.is_server_enabled(config_file_path, server.name):
                continue

            for tool in server.tools:
                if not self.config.is_tool_enabled(config_file_path, server.name, tool.name):
                    continue

                # Create a closure to capture server_name and tool_name
                self._register_tool(server.name, tool)

            # Register resources
            for resource in server.resources:
                if not self.config.is_resource_enabled(config_file_path, server.name, resource.uri):
                    continue
                self._register_resource(server.name, resource)

            # Register prompts
            for prompt in server.prompts:
                if not self.config.is_prompt_enabled(config_file_path, server.name, prompt.name):
                    continue
                self._register_prompt(server.name, prompt)

    def _create_tool_handler(self, server_name: str, tool_name: str):
        """Create a tool handler closure for a specific server and tool."""

        async def handler(kwargs: dict) -> str:
            start_time = time.time()
            try:
                # Find the server
                server = next((s for s in self.servers if s.name == server_name), None)
                if not server:
                    raise ValueError(f"Server {server_name} not found")

                # Call the tool on the backend server using the client service
                result = await self.client_service.call_tool(
                    server=server,
                    tool_name=tool_name,
                    tool_args=kwargs
                )

                duration_ms = (time.time() - start_time) * 1000

                # Format the result for logging and return
                # The result from MCP typically has content array
                if hasattr(result, 'content'):
                    # Extract text from content array
                    result_text = []
                    for item in result.content:
                        if hasattr(item, 'text'):
                            result_text.append(item.text)
                        else:
                            result_text.append(str(item))
                    formatted_result = '\n'.join(result_text)
                else:
                    formatted_result = str(result)

                if self.config.enable_logging:
                    self.logger.log_tool_call(
                        server_name=server_name,
                        tool_name=tool_name,
                        parameters=kwargs,
                        response=formatted_result,
                        duration_ms=duration_ms,
                    )

                return formatted_result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)

                if self.config.enable_logging:
                    self.logger.log_tool_call(
                        server_name=server_name,
                        tool_name=tool_name,
                        parameters=kwargs,
                        error=error_msg,
                        duration_ms=duration_ms,
                    )

                return f"Error: {error_msg}"

        return handler

    def _register_tool(self, server_name: str, tool: Any) -> None:
        """Register a single tool with the FastMCP server."""
        # Create prefixed name
        prefixed_name = f"{server_name}__{tool.name}"
        description = f"[{server_name}] {tool.description or tool.name}"

        # Get the input schema
        schema = tool.input_schema or {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Build parameter list for the dynamic function
        param_types = []

        for param_name, param_def in properties.items():
            param_type = param_def.get("type", "string")

            # Map JSON schema types to Python types
            python_type = str  # default
            if param_type == "integer":
                python_type = int
            elif param_type == "number":
                python_type = float
            elif param_type == "boolean":
                python_type = bool
            elif param_type == "array":
                python_type = list
            elif param_type == "object":
                python_type = dict

            is_required = param_name in required
            param_types.append((param_name, python_type, is_required))

        # Sort parameters: required first, then optional
        param_types.sort(key=lambda x: (not x[2], x[0]))

        # Create a dynamic function with proper signature
        # Build the parameter string
        param_str_parts = []
        for param_name, python_type, is_required in param_types:
            type_name = python_type.__name__
            if is_required:
                param_str_parts.append(f"{param_name}: {type_name}")
            else:
                param_str_parts.append(f"{param_name}: {type_name} = None")

        param_str = ", ".join(param_str_parts)

        # Create the function body that calls our handler
        func_code = f"""
async def tool_handler({param_str}) -> str:
    # Collect all parameters
    kwargs = {{{", ".join(f'"{p[0]}": {p[0]}' for p in param_types)}}}
    # Remove None values
    kwargs = {{k: v for k, v in kwargs.items() if v is not None}}
    return await _call_handler(kwargs)
"""

        # Create a namespace with the handler
        namespace = {"_call_handler": self._create_tool_handler(server_name, tool.name)}

        # Execute the function definition
        exec(func_code, namespace)
        tool_handler_func = namespace["tool_handler"]

        # Register with FastMCP using the tool decorator
        self.mcp.tool(name=prefixed_name, description=description)(tool_handler_func)

    def _register_resource(self, server_name: str, resource: Any) -> None:
        """Register a single resource with the FastMCP server."""
        # Create prefixed URI
        prefixed_uri = f"{server_name}://{resource.uri}"

        async def resource_handler() -> str:
            start_time = time.time()
            try:
                # Read the resource from the backend server
                # Note: This is simplified - full implementation would use the client service
                result = f"Read resource {resource.uri} from {server_name}"

                duration_ms = (time.time() - start_time) * 1000

                if self.config.enable_logging:
                    self.logger.log_resource_read(
                        server_name=server_name,
                        resource_uri=resource.uri,
                        response=result,
                        duration_ms=duration_ms,
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = str(e)

                if self.config.enable_logging:
                    self.logger.log_resource_read(
                        server_name=server_name,
                        resource_uri=resource.uri,
                        error=error_msg,
                        duration_ms=duration_ms,
                    )

                return f"Error: {error_msg}"

        # Register with FastMCP
        description = f"[{server_name}] {resource.description or ''}"
        self.mcp.resource(
            uri=prefixed_uri,
            name=resource.name or resource.uri,
            description=description,
            mime_type=resource.mime_type,
        )(resource_handler)

    def _register_prompt(self, server_name: str, prompt: Any) -> None:
        """Register a single prompt with the FastMCP server."""
        # Create prefixed name
        prefixed_name = f"{server_name}__{prompt.name}"
        description = f"[{server_name}] {prompt.description or prompt.name}"

        # Build parameter list from prompt arguments
        param_types = []
        for arg in prompt.arguments:
            param_types.append((arg.name, str, arg.required))

        # Sort parameters: required first, then optional
        param_types.sort(key=lambda x: (not x[2], x[0]))

        # Create a closure to handle the prompt call
        def _create_prompt_handler():
            async def handler(kwargs: dict) -> str:
                return f"Prompt {prompt.name} from {server_name} with args: {kwargs}"
            return handler

        # If there are no parameters, create a simple handler
        if not param_types:
            async def prompt_handler() -> str:
                return await _create_prompt_handler()({})

            self.mcp.prompt(name=prefixed_name, description=description)(prompt_handler)
            return

        # Build the parameter string for the dynamic function
        param_str_parts = []
        for param_name, python_type, is_required in param_types:
            type_name = python_type.__name__
            if is_required:
                param_str_parts.append(f"{param_name}: {type_name}")
            else:
                param_str_parts.append(f"{param_name}: {type_name} = None")

        param_str = ", ".join(param_str_parts)

        # Create the function body
        func_code = f"""
async def prompt_handler({param_str}) -> str:
    # Collect all parameters
    kwargs = {{{", ".join(f'"{p[0]}": {p[0]}' for p in param_types)}}}
    # Remove None values
    kwargs = {{k: v for k, v in kwargs.items() if v is not None}}
    return await _call_handler(kwargs)
"""

        # Create a namespace with the handler
        namespace = {"_call_handler": _create_prompt_handler()}

        # Execute the function definition
        exec(func_code, namespace)
        prompt_handler_func = namespace["prompt_handler"]

        # Register with FastMCP
        self.mcp.prompt(name=prefixed_name, description=description)(prompt_handler_func)

    async def start(self) -> None:
        """Start the proxy server with both HTTP (/mcp) and SSE (/sse) endpoints."""
        self._running = True

        # Set up log file
        log_dir = Path.home() / ".mcp-explorer" / "proxy-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"proxy-{int(time.time())}.jsonl"
        self.logger.set_log_file(log_file)

        # Count enabled servers
        enabled_count = sum(1 for s in self.servers if self.config.is_server_enabled(s.source_file or "", s.name))

        # Log server start
        if self.config.enable_logging:
            self.logger.log_server_started(
                port=self.config.port,
                enabled_servers=enabled_count,
                message=f"Proxy server starting on http://localhost:{self.config.port} with {enabled_count} enabled servers\n"
                f"  HTTP endpoint: http://localhost:{self.config.port}/mcp\n"
                f"  SSE endpoint:  http://localhost:{self.config.port}/sse",
            )

        try:
            # Import required modules
            from starlette.applications import Starlette
            from starlette.routing import Mount
            from fastmcp.server.http import create_sse_app
            import uvicorn

            # Create main Starlette app with both transports
            # Use http_app() for modern HTTP transport at /mcp
            # Use create_sse_app() for legacy SSE support at /sse
            app = Starlette(
                routes=[
                    Mount("/mcp", app=self.mcp.http_app()),
                    Mount(
                        "/sse",
                        app=create_sse_app(server=self.mcp, message_path="/message", sse_path="/"),
                    ),
                ]
            )

            # Add middleware to track SSE client connections
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

    def register_client(self, client_id: str, remote_addr: Optional[str] = None) -> None:
        """Register a new connected client.

        Args:
            client_id: Unique client identifier
            remote_addr: Client's remote address
        """
        self._connected_clients.add(client_id)
        if self.config.enable_logging:
            self.logger.log_client_connected(client_id=client_id, remote_addr=remote_addr)

    def unregister_client(self, client_id: str, reason: Optional[str] = None) -> None:
        """Unregister a disconnected client.

        Args:
            client_id: Unique client identifier
            reason: Disconnection reason
        """
        self._connected_clients.discard(client_id)
        if self.config.enable_logging:
            self.logger.log_client_disconnected(client_id=client_id, reason=reason)
