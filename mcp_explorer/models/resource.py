"""Resource domain model."""

from typing import Any, Optional

from pydantic import BaseModel


class MCPResource(BaseModel):
    """Represents an MCP resource."""

    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None

    def get_display_name(self) -> str:
        """Get display name for the resource."""
        return self.name or self.uri

    @classmethod
    def from_mcp_resource(cls, resource_data: Any) -> "MCPResource":
        """Create MCPResource from MCP resource data."""
        return cls(
            uri=resource_data.uri,
            name=resource_data.name,
            description=resource_data.description,
            mime_type=getattr(resource_data, "mimeType", None),
        )
