"""MCP Client service for connecting to and querying MCP servers."""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from fastmcp import Client
from fastmcp.client.transports import SSETransport, StdioTransport, StreamableHttpTransport

from ..models import MCPPrompt, MCPResource, MCPServer, MCPTool, ServerType


class MCPClientService:
    """Service for interacting with MCP servers using fastmcp 2.0."""

    def __init__(self) -> None:
        """Initialize the MCP client service."""
        self._active_clients: Dict[str, Client] = {}

    def _create_client(self, server: MCPServer) -> Client:
        """Create a fastmcp Client based on server configuration.

        Args:
            server: MCP server configuration

        Returns:
            Configured fastmcp Client instance

        Raises:
            ValueError: If server configuration is invalid
        """
        if server.server_type == ServerType.STDIO:
            if not server.command:
                raise ValueError("No command specified for stdio server")

            transport = StdioTransport(
                command=server.command,
                args=server.args,
                env=server.env or {},
            )
            return Client(transport)

        elif server.server_type == ServerType.HTTP:
            if not server.url:
                raise ValueError("No URL specified for HTTP server")

            transport = StreamableHttpTransport(
                url=server.url,
                headers=server.headers or {},
            )
            return Client(transport)

        elif server.server_type == ServerType.SSE:
            if not server.url:
                raise ValueError("No URL specified for SSE server")

            transport = SSETransport(
                url=server.url,
                headers=server.headers or {},
            )
            return Client(transport)

        else:
            raise ValueError(f"Unknown server type: {server.server_type}")

    @asynccontextmanager
    async def connect_to_server(self, server: MCPServer) -> AsyncIterator[Client]:
        """Connect to an MCP server and yield the client.

        Args:
            server: MCP server to connect to

        Yields:
            Connected fastmcp Client instance
        """
        client = self._create_client(server)
        self._active_clients[server.name] = client

        try:
            async with client:
                yield client
        finally:
            if server.name in self._active_clients:
                del self._active_clients[server.name]

    async def query_server_capabilities(self, server: MCPServer) -> MCPServer:
        """Query a server for its complete capabilities.

        Args:
            server: MCP server to query

        Returns:
            Updated server with capabilities populated
        """
        try:
            async with self.connect_to_server(server) as client:
                # Get server info from client
                if hasattr(client, "server_name") and hasattr(client, "server_version"):
                    server.server_info = {
                        "name": client.server_name or "",
                        "version": client.server_version or "",
                    }

                # Query tools
                try:
                    tools_result = await client.list_tools()
                    server.tools = [MCPTool.from_mcp_tool(tool) for tool in tools_result]
                except Exception as e:
                    print(f"Error fetching tools from {server.name}: {e}")

                # Query resources
                try:
                    resources_result = await client.list_resources()
                    server.resources = [
                        MCPResource.from_mcp_resource(res) for res in resources_result
                    ]
                except Exception as e:
                    print(f"Error fetching resources from {server.name}: {e}")

                # Query prompts
                try:
                    prompts_result = await client.list_prompts()
                    server.prompts = [
                        MCPPrompt.from_mcp_prompt(prompt) for prompt in prompts_result
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
        async with self.connect_to_server(server) as client:
            result = await client.call_tool(tool_name, tool_args or {})
            return result

    async def get_prompt_preview(
        self,
        server: MCPServer,
        prompt_name: str,
        prompt_args: Optional[Dict[str, str]] = None,
    ) -> str:
        """Get a preview of a prompt with given arguments.

        Args:
            server: MCP server to query
            prompt_name: Name of the prompt to preview
            prompt_args: Arguments to pass to the prompt

        Returns:
            Formatted prompt preview string
        """
        try:
            async with self.connect_to_server(server) as client:
                result = await client.get_prompt(prompt_name, prompt_args or {})

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
        """Cleanup any active clients."""
        self._active_clients.clear()
