"""Discovery service for finding and loading MCP servers."""

import asyncio
from typing import Any

from ..models import ConfigFile, MCPServer, ServerType
from .client import MCPClientService
from .config_loader import MCPConfigLoader

try:
    from fastmcp.cli.discovery import (
        DiscoveredServer,
    )
    from fastmcp.cli.discovery import (
        discover_servers as fastmcp_discover_servers,
    )
    from fastmcp.mcp_config import RemoteMCPServer, StdioMCPServer

    HAS_FASTMCP_DISCOVERY = True
except ImportError:
    HAS_FASTMCP_DISCOVERY = False


class MCPDiscoveryService:
    """Service for discovering and initializing MCP servers."""

    def __init__(self) -> None:
        """Initialize the discovery service."""
        self.config_loader = MCPConfigLoader()
        self.client_service = MCPClientService()

    async def discover_all_servers_hierarchical(self) -> list[ConfigFile]:
        """Discover and initialize all configured MCP servers maintaining hierarchy.

        Returns:
            List of ConfigFile objects, each containing initialized MCPServer objects.
        """
        config_files_data = self.config_loader.discover_servers_hierarchical()

        if not config_files_data:
            return []

        # Process each config file
        initialized_config_files: list[ConfigFile] = []

        for config_file_data in config_files_data:
            path = config_file_data["path"]
            servers_data = config_file_data["servers"]

            # Create tasks for parallel server initialization within this config
            tasks = []
            for server_data in servers_data:
                name = server_data["name"]
                config = server_data["config"]
                tasks.append(self._init_server(name, config))

            if tasks:
                # Initialize all servers from this config file in parallel
                servers = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out exceptions and create new ConfigFile with initialized servers
                initialized_servers = [s for s in servers if isinstance(s, MCPServer)]

                if initialized_servers:
                    initialized_config_file = ConfigFile(path=path, servers=initialized_servers)
                    initialized_config_files.append(initialized_config_file)

        return initialized_config_files

    async def discover_all_servers(self) -> list[MCPServer]:
        """Discover and initialize all configured MCP servers (flattened list).

        Returns:
            Flat list of all MCPServer objects from all config files.
        """
        config_files = await self.discover_all_servers_hierarchical()

        # Flatten the hierarchy into a single list
        all_servers: list[MCPServer] = []
        for config_file in config_files:
            all_servers.extend(config_file.servers)

        # Add FastMCP-discovered servers (de-duplicate by name)
        existing_names = {s.name for s in all_servers}
        for server in self._discover_fastmcp_servers():
            if server.name not in existing_names:
                all_servers.append(server)
                existing_names.add(server.name)

        return all_servers

    def _discover_fastmcp_servers(self) -> list[MCPServer]:
        """Discover MCP servers using FastMCP's built-in discovery.

        Scans Claude Desktop, Cursor, Goose, and other supported clients.
        """
        if not HAS_FASTMCP_DISCOVERY:
            return []

        try:
            discovered = fastmcp_discover_servers()
        except Exception:
            return []

        servers: list[MCPServer] = []
        for entry in discovered:
            try:
                server = self._convert_discovered_server(entry)
                if server:
                    servers.append(server)
            except Exception:
                continue
        return servers

    def _convert_discovered_server(self, entry: "DiscoveredServer") -> MCPServer | None:
        """Convert a FastMCP DiscoveredServer to our MCPServer model."""
        config = entry.config
        if isinstance(config, StdioMCPServer):
            return MCPServer(
                name=entry.name,
                server_type=ServerType.STDIO,
                command=config.command,
                args=config.args,
                env={k: str(v) for k, v in config.env.items()} if config.env else {},
                source_file=str(entry.config_path),
            )
        elif isinstance(config, RemoteMCPServer):
            transport = config.transport
            if transport == "sse":
                server_type = ServerType.SSE
            else:
                server_type = ServerType.HTTP
            return MCPServer(
                name=entry.name,
                server_type=server_type,
                url=str(config.url),
                headers=config.headers or {},
                source_file=str(entry.config_path),
            )
        return None

    async def _init_server(self, name: str, config: dict[str, Any]) -> MCPServer:
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
