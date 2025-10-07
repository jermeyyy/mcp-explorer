"""Config file domain model."""

from typing import List

from pydantic import BaseModel, Field

from .server import MCPServer


class ConfigFile(BaseModel):
    """Represents a configuration file containing MCP servers."""

    path: str
    servers: List[MCPServer] = Field(default_factory=list)

    def get_server_by_name(self, name: str) -> MCPServer | None:
        """Get a server by name from this config file."""
        for server in self.servers:
            if server.name == name:
                return server
        return None

    def get_display_path(self) -> str:
        """Get shortened display path for UI."""
        from pathlib import Path

        try:
            path = Path(self.path)
            home = Path.home()
            if path.is_relative_to(home):
                return f"~/{path.relative_to(home)}"
        except (ValueError, Exception):
            pass

        return self.path

