"""Server domain model."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .prompt import MCPPrompt
from .resource import MCPResource
from .tool import MCPTool


class ServerType(str, Enum):
    """Enumeration of server types."""

    STDIO = "stdio"
    SSE = "sse"


class ServerStatus(str, Enum):
    """Enumeration of possible server statuses."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MCPServer(BaseModel):
    """Represents an MCP server with its capabilities."""

    name: str
    server_type: ServerType = ServerType.STDIO

    # For stdio servers
    command: Optional[str] = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

    # For SSE servers
    url: Optional[str] = None

    # Status and metadata
    status: ServerStatus = ServerStatus.DISCONNECTED
    error_message: Optional[str] = None
    description: Optional[str] = None
    source_file: Optional[str] = None

    # Capabilities
    tools: list[MCPTool] = Field(default_factory=list)
    resources: list[MCPResource] = Field(default_factory=list)
    prompts: list[MCPPrompt] = Field(default_factory=list)

    # Metadata
    server_info: dict[str, str] = Field(default_factory=dict)

    def get_status_display(self) -> str:
        """Get human-readable status."""
        status_map = {
            ServerStatus.CONNECTED: "✓ Connected",
            ServerStatus.DISCONNECTED: "○ Disconnected",
            ServerStatus.ERROR: "✗ Error",
        }
        return status_map.get(self.status, str(self.status))

    def get_capabilities_summary(self) -> str:
        """Get summary of server capabilities."""
        parts = []

        # Add type indicator
        parts.append(f"[{self.server_type.value.upper()}]")

        # Add capabilities
        capability_parts = []
        if self.tools:
            capability_parts.append(f"{len(self.tools)} tools")
        if self.resources:
            capability_parts.append(f"{len(self.resources)} resources")
        if self.prompts:
            capability_parts.append(f"{len(self.prompts)} prompts")

        if capability_parts:
            parts.append(", ".join(capability_parts))
        else:
            parts.append("No capabilities")

        return " ".join(parts)

    def mark_connected(self) -> None:
        """Mark server as connected."""
        self.status = ServerStatus.CONNECTED
        self.error_message = None

    def mark_error(self, error: str) -> None:
        """Mark server as having an error."""
        self.status = ServerStatus.ERROR
        self.error_message = error

    def mark_disconnected(self) -> None:
        """Mark server as disconnected."""
        self.status = ServerStatus.DISCONNECTED
        self.error_message = None
