"""Custom widgets for MCP Explorer."""

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Label, ListItem, ListView, Static

from ..models import MCPPrompt, MCPResource, MCPServer, MCPTool


class ServerListItem(ListItem):
    """A list item representing an MCP server."""

    def __init__(self, server: MCPServer) -> None:
        """Initialize the server list item."""
        super().__init__()
        self.server = server

    def compose(self) -> ComposeResult:
        """Compose the server list item."""
        with Vertical():
            # Server name
            yield Static(self.server.name, classes="server-name")

            # Description
            if self.server.description:
                yield Static(self.server.description, classes="item-description")

            # Status and capabilities
            status_class = (
                "server-status-error" if self.server.status.value == "error" else "server-status"
            )

            # Build status line
            status_parts = [self.server.get_status_display()]
            if self.server.tools:
                status_parts.append(f"Tools: {len(self.server.tools)}")
            if self.server.resources:
                status_parts.append(f"Resources: {len(self.server.resources)}")
            if self.server.prompts:
                status_parts.append(f"Prompts: {len(self.server.prompts)}")

            yield Static(" | ".join(status_parts), classes=status_class)

            # Error message if present
            if self.server.error_message:
                yield Static(f"Error: {self.server.error_message}", classes="server-status-error")


class ToolListItem(ListItem):
    """A list item representing an MCP tool."""

    def __init__(self, tool: MCPTool) -> None:
        """Initialize the tool list item."""
        super().__init__()
        self.tool = tool

    def compose(self) -> ComposeResult:
        """Compose the tool list item."""
        with Vertical():
            yield Static(self.tool.name, classes="item-name")
            if self.tool.description:
                yield Static(self.tool.description, classes="item-description")

            param_summary = self.tool.get_parameter_summary()
            if param_summary and param_summary != "No parameters":
                yield Static(param_summary, classes="item-params")


class ResourceListItem(ListItem):
    """A list item representing an MCP resource."""

    def __init__(self, resource: MCPResource) -> None:
        """Initialize the resource list item."""
        super().__init__()
        self.resource = resource

    def compose(self) -> ComposeResult:
        """Compose the resource list item."""
        with Vertical():
            yield Static(self.resource.get_display_name(), classes="item-name")
            yield Static(self.resource.uri, classes="item-description")

            if self.resource.description:
                yield Static(self.resource.description, classes="item-description")

            if self.resource.mime_type:
                yield Static(f"Type: {self.resource.mime_type}", classes="item-params")


class PromptListItem(ListItem):
    """A list item representing an MCP prompt."""

    def __init__(self, prompt: MCPPrompt) -> None:
        """Initialize the prompt list item."""
        super().__init__()
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        """Compose the prompt list item."""
        with Vertical():
            yield Static(self.prompt.name, classes="item-name")
            if self.prompt.description:
                yield Static(self.prompt.description, classes="item-description")

            arg_summary = self.prompt.get_argument_summary()
            if arg_summary and arg_summary != "No arguments":
                yield Static(arg_summary, classes="item-params")


class ConfigFileHeader(ListItem):
    """A header item representing a configuration file source."""

    def __init__(self, config_file: str, server_count: int) -> None:
        """Initialize the config file header."""
        super().__init__()
        self.config_file = config_file
        self.server_count = server_count
        self.can_focus = False  # Headers cannot be selected

    def compose(self) -> ComposeResult:
        """Compose the config file header."""
        from pathlib import Path

        # Shorten path if it's in home directory
        display_path = self.config_file
        try:
            path = Path(self.config_file)
            home = Path.home()
            if path.is_relative_to(home):
                display_path = f"~/{path.relative_to(home)}"
        except (ValueError, Exception):
            pass

        header_text = f"📁 {display_path}"
        count_text = f"({self.server_count} server{'s' if self.server_count != 1 else ''})"

        yield Static(f"{header_text} {count_text}", classes="config-file-header")


class DetailPanel(Container):
    """A panel for displaying detailed information."""

    def __init__(self, title: str, content: str, **kwargs) -> None:  # type: ignore
        """Initialize the detail panel."""
        super().__init__(**kwargs)
        self.title = title
        self.content = content

    def compose(self) -> ComposeResult:
        """Compose the detail panel."""
        yield Static(self.title.upper(), classes="detail-title")
        yield Static(self.content, classes="detail-content")
