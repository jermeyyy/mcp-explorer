"""Discovery service for finding and loading MCP servers."""

import asyncio
from typing import Any, Dict, List

from ..models import MCPServer, ServerType
from .client import MCPClientService
from .config_loader import MCPConfigLoader


class MCPDiscoveryService:
    """Service for discovering and initializing MCP servers."""

    def __init__(self) -> None:
        """Initialize the discovery service."""
        self.config_loader = MCPConfigLoader()
        self.client_service = MCPClientService()

    async def discover_all_servers(self) -> List[MCPServer]:
        """Discover and initialize all configured MCP servers."""
        server_configs = self.config_loader.discover_servers()

        if not server_configs:
            return []

        # Create tasks for parallel server discovery
        tasks = [self._init_server(name, config) for name, config in server_configs.items()]

        servers = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successful servers
        return [server for server in servers if isinstance(server, MCPServer)]

    async def _init_server(self, name: str, config: Dict[str, Any]) -> MCPServer:
        """Initialize a single server from its configuration."""
        try:
            # Determine server type
            server_type_str = config.get("type", "stdio")
            try:
                server_type = ServerType(server_type_str)
            except ValueError:
                server = MCPServer(name=name)
                server.mark_error(f"Invalid server type: {server_type_str}")
                return server

            # Check for validation errors from config loading
            if "_validation_error" in config:
                server = MCPServer(name=name, server_type=server_type)
                server.mark_error(config["_validation_error"])
                server.source_file = config.get("_source_file")
                return server

            # Extract common fields
            description = config.get("description")
            source_file = config.get("_source_file")

            # Build server based on type
            if server_type == ServerType.STDIO:
                command = config.get("command", "")
                args = config.get("args", [])
                env = config.get("env", {})

                server = MCPServer(
                    name=name,
                    server_type=server_type,
                    command=command,
                    args=args,
                    env=env,
                    description=description,
                    source_file=source_file,
                )

                if not command:
                    server.mark_error("No command specified in configuration")
                    return server

            elif server_type == ServerType.HTTP:
                url = config.get("url", "")
                headers = config.get("headers", {})

                server = MCPServer(
                    name=name,
                    server_type=server_type,
                    url=url,
                    headers=headers,
                    description=description,
                    source_file=source_file,
                )

                if not url:
                    server.mark_error("No URL specified in configuration")
                    return server

            elif server_type == ServerType.SSE:
                url = config.get("url", "")
                headers = config.get("headers", {})

                server = MCPServer(
                    name=name,
                    server_type=server_type,
                    url=url,
                    headers=headers,
                    description=description,
                    source_file=source_file,
                )

                if not url:
                    server.mark_error("No URL specified in configuration")
                    return server
            else:
                server = MCPServer(name=name, server_type=server_type)
                server.mark_error(f"Unsupported server type: {server_type}")
                return server

            # Query the server for its capabilities
            return await self.client_service.query_server_capabilities(server)

        except Exception as e:
            # Catch any unexpected errors during server initialization
            print(f"Unexpected error initializing server '{name}': {e}")
            import traceback

            traceback.print_exc()

            # Return a server in error state
            server = MCPServer(name=name)
            server.mark_error(f"Initialization failed: {str(e)}")
            return server

    async def refresh_server(self, server: MCPServer) -> MCPServer:
        """Refresh a server's capabilities."""
        return await self.client_service.query_server_capabilities(server)

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.client_service.cleanup()
