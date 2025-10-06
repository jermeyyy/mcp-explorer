"""MCP Client service for connecting to and querying MCP servers."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

try:
    from mcp.client.sse import sse_client

    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False

from ..models import MCPPrompt, MCPResource, MCPServer, MCPTool, ServerType


class MCPClientService:
    """Service for interacting with MCP servers."""

    def __init__(self) -> None:
        """Initialize the MCP client service."""
        self._active_sessions: Dict[str, ClientSession] = {}

    @asynccontextmanager
    async def connect_to_stdio_server(
        self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[ClientSession]:
        """Connect to a stdio MCP server and yield the session."""
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env or {},
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._active_sessions[server_name] = session
                try:
                    yield session
                finally:
                    if server_name in self._active_sessions:
                        del self._active_sessions[server_name]

    @asynccontextmanager
    async def connect_to_sse_server(
        self, server_name: str, url: str
    ) -> AsyncIterator[ClientSession]:
        """Connect to an SSE MCP server and yield the session."""
        if not SSE_AVAILABLE:
            raise RuntimeError("SSE client not available. Install mcp with SSE support.")

        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._active_sessions[server_name] = session
                try:
                    yield session
                finally:
                    if server_name in self._active_sessions:
                        del self._active_sessions[server_name]

    async def query_server_capabilities(self, server: MCPServer) -> MCPServer:
        """Query a server for its complete capabilities."""
        try:
            # Connect based on server type
            if server.server_type == ServerType.STDIO:
                if not server.command:
                    server.mark_error("No command specified for stdio server")
                    return server

                context = self.connect_to_stdio_server(
                    server.name, server.command, server.args, server.env
                )
            elif server.server_type == ServerType.SSE:
                if not server.url:
                    server.mark_error("No URL specified for SSE server")
                    return server

                context = self.connect_to_sse_server(server.name, server.url)
            else:
                server.mark_error(f"Unknown server type: {server.server_type}")
                return server

            async with context as session:
                # Get server info - check for the correct attribute
                server_info = {}
                if hasattr(session, "server_capabilities"):
                    # Newer MCP API
                    caps = session.server_capabilities
                    if caps and hasattr(caps, "serverInfo"):
                        server_info = {
                            "name": getattr(caps.serverInfo, "name", ""),
                            "version": getattr(caps.serverInfo, "version", ""),
                        }
                elif hasattr(session, "_server_info"):
                    # Alternative attribute name
                    info = session._server_info
                    if info:
                        server_info = {
                            "name": info.get("name", ""),
                            "version": info.get("version", ""),
                        }

                if server_info:
                    server.server_info = server_info

                # Query tools
                try:
                    tools_result = await session.list_tools()
                    server.tools = [MCPTool.from_mcp_tool(tool) for tool in tools_result.tools]
                except Exception as e:
                    print(f"Error fetching tools from {server.name}: {e}")

                # Query resources
                try:
                    resources_result = await session.list_resources()
                    server.resources = [
                        MCPResource.from_mcp_resource(res) for res in resources_result.resources
                    ]
                except Exception as e:
                    print(f"Error fetching resources from {server.name}: {e}")

                # Query prompts
                try:
                    prompts_result = await session.list_prompts()
                    server.prompts = [
                        MCPPrompt.from_mcp_prompt(prompt) for prompt in prompts_result.prompts
                    ]
                except Exception as e:
                    print(f"Error fetching prompts from {server.name}: {e}")

                server.mark_connected()

        except Exception as e:
            # Extract actual error from ExceptionGroup/TaskGroup if present
            error_msg = str(e)

            # Check if this is an ExceptionGroup (Python 3.11+)
            if hasattr(e, "exceptions"):
                # Get the actual exceptions from the group
                actual_errors = []
                for exc in e.exceptions:
                    actual_errors.append(f"{type(exc).__name__}: {exc}")
                error_msg = "; ".join(actual_errors) if actual_errors else str(e)

            server.mark_error(error_msg)

        return server

    async def call_tool(
        self,
        server: MCPServer,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call a tool on a backend MCP server.

        Args:
            server: MCP server to call the tool on
            tool_name: Name of the tool to call
            tool_args: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            Exception: If tool execution fails
        """
        # Connect based on server type
        if server.server_type == ServerType.STDIO:
            if not server.command:
                raise ValueError("No command specified for stdio server")

            context = self.connect_to_stdio_server(
                server.name, server.command, server.args, server.env
            )
        elif server.server_type == ServerType.SSE:
            if not server.url:
                raise ValueError("No URL specified for SSE server")

            context = self.connect_to_sse_server(server.name, server.url)
        else:
            raise ValueError(f"Unknown server type: {server.server_type}")

        async with context as session:
            result = await session.call_tool(tool_name, arguments=tool_args or {})
            return result

    async def get_prompt_preview(
        self,
        server: MCPServer,
        prompt_name: str,
        prompt_args: Optional[Dict[str, str]] = None,
    ) -> str:
        """Get a preview of a prompt with given arguments."""
        try:
            # Connect based on server type
            if server.server_type == ServerType.STDIO:
                if not server.command:
                    return "Error: No command specified for stdio server"

                context = self.connect_to_stdio_server(
                    server.name, server.command, server.args, server.env
                )
            elif server.server_type == ServerType.SSE:
                if not server.url:
                    return "Error: No URL specified for SSE server"

                context = self.connect_to_sse_server(server.name, server.url)
            else:
                return f"Error: Unknown server type: {server.server_type}"

            async with context as session:
                result = await session.get_prompt(prompt_name, arguments=prompt_args or {})

                # Format the preview
                preview_parts = []
                for message in result.messages:
                    role = getattr(message, "role", "unknown")
                    content = getattr(message, "content", "")

                    # Handle content that might be a list or dict
                    if isinstance(content, list):
                        content_str = "\n".join(
                            str(item.get("text", item)) if isinstance(item, dict) else str(item)
                            for item in content
                        )
                    elif isinstance(content, dict):
                        content_str = content.get("text", str(content))
                    else:
                        content_str = str(content)

                    preview_parts.append(f"[{role.upper()}]\n{content_str}")

                return "\n\n".join(preview_parts)

        except Exception as e:
            return f"Error previewing prompt: {e}"

    def cleanup(self) -> None:
        """Cleanup any active sessions."""
        self._active_sessions.clear()
