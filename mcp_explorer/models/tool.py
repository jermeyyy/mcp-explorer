"""Tool domain model."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Represents a parameter for an MCP tool."""

    name: str
    type: str
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None

    @classmethod
    def from_json_schema(
        cls, name: str, schema: Dict[str, Any], required: list[str]
    ) -> "ToolParameter":
        """Create a ToolParameter from JSON schema definition."""
        return cls(
            name=name,
            type=schema.get("type", "any"),
            description=schema.get("description"),
            required=name in required,
            default=schema.get("default"),
        )


class MCPTool(BaseModel):
    """Represents an MCP tool with its metadata and parameters."""

    name: str
    description: Optional[str] = None
    parameters: list[ToolParameter] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=dict)

    def get_parameter_summary(self) -> str:
        """Get a human-readable summary of parameters."""
        if not self.parameters:
            return "No parameters"

        required_params = [p.name for p in self.parameters if p.required]
        optional_params = [p.name for p in self.parameters if not p.required]

        parts = []
        if required_params:
            parts.append(f"Required: {', '.join(required_params)}")
        if optional_params:
            parts.append(f"Optional: {', '.join(optional_params)}")

        return " | ".join(parts)

    @classmethod
    def from_mcp_tool(cls, tool_data: Any) -> "MCPTool":
        """Create MCPTool from MCP tool data."""
        input_schema = tool_data.inputSchema if hasattr(tool_data, "inputSchema") else {}
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        parameters = [
            ToolParameter.from_json_schema(name, schema, required)
            for name, schema in properties.items()
        ]

        return cls(
            name=tool_data.name,
            description=tool_data.description,
            parameters=parameters,
            input_schema=input_schema,
        )
