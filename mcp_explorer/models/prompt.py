"""Prompt domain model."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class PromptArgument(BaseModel):
    """Represents an argument for an MCP prompt."""

    name: str
    description: Optional[str] = None
    required: bool = False

    @classmethod
    def from_mcp_argument(cls, arg_data: Any) -> "PromptArgument":
        """Create PromptArgument from MCP argument data."""
        return cls(
            name=arg_data.name,
            description=arg_data.description,
            required=arg_data.required,
        )


class MCPPrompt(BaseModel):
    """Represents an MCP prompt template."""

    name: str
    description: Optional[str] = None
    arguments: list[PromptArgument] = Field(default_factory=list)

    def get_argument_summary(self) -> str:
        """Get a human-readable summary of arguments."""
        if not self.arguments:
            return "No arguments"

        required_args = [a.name for a in self.arguments if a.required]
        optional_args = [a.name for a in self.arguments if not a.required]

        parts = []
        if required_args:
            parts.append(f"Required: {', '.join(required_args)}")
        if optional_args:
            parts.append(f"Optional: {', '.join(optional_args)}")

        return " | ".join(parts)

    @classmethod
    def from_mcp_prompt(cls, prompt_data: Any) -> "MCPPrompt":
        """Create MCPPrompt from MCP prompt data."""
        arguments = []
        if hasattr(prompt_data, "arguments") and prompt_data.arguments:
            arguments = [PromptArgument.from_mcp_argument(arg) for arg in prompt_data.arguments]

        return cls(
            name=prompt_data.name,
            description=prompt_data.description,
            arguments=arguments,
        )
