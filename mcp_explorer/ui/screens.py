"""Screens for MCP Explorer TUI."""

from typing import Optional

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ListView,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
)

from ..models import MCPPrompt, MCPServer, MCPTool, MCPResource
from .widgets import (
    DetailPanel,
    PromptListItem,
    ResourceListItem,
    ServerListItem,
    ToolListItem,
)


class ServerListScreen(Screen):
    """Screen displaying the list of MCP servers."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, servers: list[MCPServer]) -> None:
        """Initialize the server list screen."""
        super().__init__()
        self.servers = servers

    def compose(self) -> ComposeResult:
        """Compose the server list screen."""
        yield Header(show_clock=True)
        yield Footer()

        if not self.servers:
            yield Container(
                Static("No MCP servers found. Check your configuration.", classes="empty-state"),
                id="empty-state",
            )
        else:
            yield ListView(*[ServerListItem(server) for server in self.servers], id="server-list")

    @on(ListView.Selected, "#server-list")
    def show_server_detail(self, event: ListView.Selected) -> None:
        """Show detail view for selected server."""
        if isinstance(event.item, ServerListItem):
            self.app.push_screen(ServerDetailScreen(event.item.server))  # type: ignore

    def action_refresh(self) -> None:
        """Refresh the server list."""
        self.app.action_refresh_servers()  # type: ignore


class ServerDetailScreen(Screen):
    """Screen displaying details of a single MCP server."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, server: MCPServer) -> None:
        """Initialize the server detail screen."""
        super().__init__()
        self.server = server

    def compose(self) -> ComposeResult:
        """Compose the server detail screen."""
        yield Header(show_clock=True)
        yield Footer()

        with Container(id="detail-container"):
            # Server info panel
            with VerticalScroll(id="server-info"):
                # Server name header
                yield Static(self.server.name, classes="server-detail-name")

                # Description if available
                if self.server.description:
                    yield Static(self.server.description, classes="server-detail-description")

                # Status Section
                yield Static("STATUS", classes="info-section-header")
                with Container(classes="info-section"):
                    status_class = (
                        "server-status-error"
                        if self.server.status.value == "error"
                        else "server-status"
                    )
                    yield Static(self.server.get_status_display(), classes=status_class)

                    # Show error if present
                    if self.server.error_message:
                        yield Static(f"Error: {self.server.error_message}", classes="server-status-error")

                # Type Section
                yield Static("TYPE", classes="info-section-header")
                with Container(classes="info-section"):
                    yield Static(self.server.server_type.value.upper(), classes="info-value")

                # Connection Section
                if self.server.command or self.server.url:
                    yield Static("CONNECTION", classes="info-section-header")
                    with Container(classes="info-section"):
                        if self.server.command:
                            yield Static("Command", classes="info-label")
                            yield Static(self.server.command, classes="info-value-mono")
                            if self.server.args:
                                yield Static("Arguments", classes="info-label")
                                yield Static(' '.join(self.server.args), classes="info-value-mono")
                        if self.server.url:
                            yield Static("URL", classes="info-label")
                            yield Static(self.server.url, classes="info-value-mono")

                # Server Info Section
                if self.server.server_info:
                    yield Static("SERVER INFO", classes="info-section-header")
                    with Container(classes="info-section"):
                        for key, value in self.server.server_info.items():
                            if value:
                                yield Static(key.title(), classes="info-label")
                                yield Static(str(value), classes="info-value")

                # Configuration Section
                if self.server.source_file:
                    yield Static("CONFIGURATION", classes="info-section-header")
                    with Container(classes="info-section"):
                        yield Static("Source File", classes="info-label")
                        yield Static(self.server.source_file, classes="info-value-mono")

            # Capabilities tabs
            with TabbedContent(id="capability-tabs"):
                with TabPane("Tools", id="tools-tab"):
                    if self.server.tools:
                        yield ListView(
                            *[ToolListItem(tool) for tool in self.server.tools],
                            classes="capability-list",
                        )
                    else:
                        yield Static("No tools available", classes="empty-state")

                with TabPane("Resources", id="resources-tab"):
                    if self.server.resources:
                        yield ListView(
                            *[ResourceListItem(resource) for resource in self.server.resources],
                            classes="capability-list",
                        )
                    else:
                        yield Static("No resources available", classes="empty-state")

                with TabPane("Prompts", id="prompts-tab"):
                    if self.server.prompts:
                        yield ListView(
                            *[PromptListItem(prompt) for prompt in self.server.prompts],
                            classes="capability-list",
                        )
                    else:
                        yield Static("No prompts available", classes="empty-state")

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    @on(ListView.Selected, ".capability-list")
    def show_capability_detail(self, event: ListView.Selected) -> None:
        """Show detailed view of a capability."""
        if isinstance(event.item, ToolListItem):
            self.app.push_screen(ToolDetailScreen(event.item.tool))  # type: ignore
        elif isinstance(event.item, ResourceListItem):
            self.app.push_screen(ResourceDetailScreen(event.item.resource))  # type: ignore
        elif isinstance(event.item, PromptListItem):
            self.app.push_screen(PromptDetailScreen(self.server, event.item.prompt))  # type: ignore


class ToolDetailScreen(Screen):
    """Screen displaying detailed information about a tool."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, tool: MCPTool) -> None:
        """Initialize the tool detail screen."""
        super().__init__()
        self.tool = tool

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        """Compose the tool detail screen."""
        yield Header(show_clock=True)
        yield Footer()

        with VerticalScroll(id="tool-detail-container"):
            # Tool name header
            yield Static(self.tool.name, classes="detail-screen-title")

            # Description section
            if self.tool.description:
                yield Static("DESCRIPTION", classes="detail-section-header")
                yield Static(self.tool.description, classes="detail-section-content")

            # Parameters section
            yield Static("PARAMETERS", classes="detail-section-header")
            if self.tool.parameters:
                for param in self.tool.parameters:
                    # Parameter card
                    requirement_badge = "[REQUIRED]" if param.required else "[OPTIONAL]"
                    requirement_class = "param-required" if param.required else "param-optional"

                    with Container(classes="parameter-item"):
                        # Parameter name with requirement badge
                        yield Static(
                            f"• {param.name} {requirement_badge}",
                            classes=f"param-name {requirement_class}"
                        )

                        # Type
                        yield Static(f"Type: {param.type}", classes="param-type")

                        # Description
                        if param.description:
                            yield Static(param.description, classes="param-description")
            else:
                yield Static("No parameters", classes="detail-section-empty")

            # Input schema section
            if self.tool.input_schema:
                yield Static("INPUT SCHEMA", classes="detail-section-header")
                import json
                # Pretty-print JSON with 2-space indentation and sorted keys for readability
                schema_text = json.dumps(self.tool.input_schema, indent=2, sort_keys=True, ensure_ascii=False)
                yield Static(schema_text, classes="detail-section-json")


class ResourceDetailScreen(Screen):
    """Screen displaying detailed information about a resource."""

    BINDINGS = [("escape", "go_back", "Back")]

    def __init__(self, resource: MCPResource) -> None:
        """Initialize the resource detail screen."""
        super().__init__()
        self.resource = resource

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        """Compose the resource detail screen."""
        yield Header(show_clock=True)
        yield Footer()

        with VerticalScroll():
            yield DetailPanel("Resource Name", self.resource.name, classes="detail-panel")
            yield DetailPanel("URI", self.resource.uri, classes="detail-panel")

            if self.resource.description:
                yield DetailPanel("Description", self.resource.description, classes="detail-panel")

            if self.resource.mime_type:
                yield DetailPanel("MIME Type", self.resource.mime_type, classes="detail-panel")


class PromptDetailScreen(Screen):
    """Screen displaying detailed information about a prompt."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("p", "preview", "Preview"),
    ]

    def __init__(self, server: MCPServer, prompt: MCPPrompt) -> None:
        """Initialize the prompt detail screen."""
        super().__init__()
        self.server = server
        self.prompt = prompt

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        """Compose the prompt detail screen."""
        yield Header(show_clock=True)
        yield Footer()

        with VerticalScroll():
            yield DetailPanel("Prompt Name", self.prompt.name, classes="detail-panel")

            if self.prompt.description:
                yield DetailPanel("Description", self.prompt.description, classes="detail-panel")

            if self.prompt.arguments:
                args_text = "\n\n".join(
                    f"• {arg.name}"
                    + (f" - {arg.description}" if arg.description else "")
                    + (" [REQUIRED]" if arg.required else " [optional]")
                    for arg in self.prompt.arguments
                )
                yield DetailPanel("Arguments", args_text, classes="detail-panel")

            with Horizontal(id="preview-buttons"):
                yield Button("Preview Prompt", id="preview-button", variant="primary")

    @on(Button.Pressed, "#preview-button")
    def action_preview(self) -> None:
        """Preview the prompt."""
        from .dialogs import PromptPreviewDialog

        self.app.push_screen(PromptPreviewDialog(self.server, self.prompt))  # type: ignore


class LoadingScreen(Screen):
    """Screen displayed while loading servers."""

    def __init__(self, message: str = "Loading MCP servers...") -> None:
        """Initialize the loading screen."""
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Compose the loading screen."""
        yield Container(
            Static(self.message, classes="loading-text"),
            id="loading",
        )


class SplashScreen(Screen):
    """Animated splash screen with initialization progress."""

    # ASCII art for MCP-EXPLORER (each line is a row of the logo)
    ASCII_LOGO = [
        "███╗   ███╗ ██████╗██████╗       ███████╗██╗  ██╗██████╗ ██╗      ██████╗ ██████╗ ███████╗██████╗ ",
        "████╗ ████║██╔════╝██╔══██╗      ██╔════╝╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██╔══██╗██╔════╝██╔══██╗",
        "██╔████╔██║██║     ██████╔╝█████╗█████╗   ╚███╔╝ ██████╔╝██║     ██║   ██║██████╔╝█████╗  ██████╔╝",
        "██║╚██╔╝██║██║     ██╔═══╝ ╚════╝██╔══╝   ██╔██╗ ██╔═══╝ ██║     ██║   ██║██╔══██╗██╔══╝  ██╔══██╗",
        "██║ ╚═╝ ██║╚██████╗██║           ███████╗██╔╝ ██╗██║     ███████╗╚██████╔╝██║  ██║███████╗██║  ██║",
        "╚═╝     ╚═╝ ╚═════╝╚═╝           ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝",
    ]

    # Color palette for the animated gradient effect (muted colors for dark theme)
    COLORS = [
        "#569cd6",  # Soft blue
        "#4ec9b0",  # Teal
        "#4fc1ff",  # Sky blue
        "#68a3d4",  # Medium blue
        "#5ba3d0",  # Steel blue
        "#4db8c9",  # Cyan blue
        "#52b788",  # Sea green
        "#74c69d",  # Mint green
        "#95d5b2",  # Light green
        "#6ba8c4",  # Ocean blue
    ]

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self) -> None:
        """Initialize the splash screen."""
        super().__init__()
        self._color_offset = 0
        self._spinner_frame = 0
        self._logo_animation_task = None
        self._spinner_animation_task = None

    def _generate_animated_logo(self) -> Text:
        """Generate the ASCII art logo with animated gradient colors."""
        result = Text()

        for row in self.ASCII_LOGO:
            row_text = Text()
            # Apply colors to each character in the row
            for i, char in enumerate(row):
                # Create a smoother wave by using a larger step size
                # This makes adjacent characters have more distinct colors
                color_index = ((i // 3) + self._color_offset) % len(self.COLORS)
                row_text.append(char, style=f"bold {self.COLORS[color_index]}")
            result.append(row_text)
            result.append("\n")

        return result

    def compose(self) -> ComposeResult:
        """Compose the splash screen."""
        with Container(id="splash-container"):
            yield Static(self._generate_animated_logo(), id="splash-logo")
            yield Static("Model Context Protocol Server Browser", id="splash-subtitle")
            yield Static("", id="splash-spacer")
            yield Static("⠋ Initializing...", id="splash-status")
            with Container(id="splash-progress-container"):
                yield ProgressBar(total=100, show_eta=False, show_percentage=False, id="splash-progress")
                yield Static("0%", id="splash-progress-percent")

    def on_mount(self) -> None:
        """Start animations when screen is mounted."""
        # Start separate animation tasks that run independently
        self._logo_animation_task = self.run_worker(self._animate_logo_loop, exclusive=False)
        self._spinner_animation_task = self.run_worker(self._animate_spinner_loop, exclusive=False)

    def on_unmount(self) -> None:
        """Stop animations when screen is unmounted."""
        # Tasks will be automatically cancelled when screen unmounts
        pass

    async def _animate_logo_loop(self) -> None:
        """Continuously animate the logo colors in a separate async loop."""
        import asyncio

        while True:
            try:
                # Update color offset for the gradient effect
                self._color_offset = (self._color_offset + 1) % len(self.COLORS)

                # Generate new logo with updated colors
                logo_widget = self.query_one("#splash-logo", Static)
                logo_widget.renderable = self._generate_animated_logo()
                logo_widget.refresh()

                # Wait before next frame (10 FPS)
                await asyncio.sleep(0.1)
            except Exception:
                # If widget query fails (screen closing), exit gracefully
                break

    async def _animate_spinner_loop(self) -> None:
        """Continuously animate the spinner in a separate async loop."""
        import asyncio

        while True:
            try:
                # Update spinner frame
                self._spinner_frame = (self._spinner_frame + 1) % len(self.SPINNER_FRAMES)

                # Update the spinner without changing the message
                status = self.query_one("#splash-status", Static)
                current_text = status.renderable
                if isinstance(current_text, str) and " " in current_text:
                    message = current_text.split(" ", 1)[1]
                    status.update(f"{self.SPINNER_FRAMES[self._spinner_frame]} {message}")

                # Wait before next frame (10 FPS)
                await asyncio.sleep(0.1)
            except Exception:
                # If widget query fails (screen closing), exit gracefully
                break

    def update_status(self, message: str, progress: float = 0) -> None:
        """Update the status message and progress.

        Args:
            message: Status message to display
            progress: Progress value (0-100)
        """
        status_label = self.query_one("#splash-status", Static)
        status_label.update(f"{self.SPINNER_FRAMES[self._spinner_frame]} {message}")

        progress_bar = self.query_one("#splash-progress", ProgressBar)
        progress_bar.update(progress=progress)

        # Update percentage display
        percent_label = self.query_one("#splash-progress-percent", Static)
        percent_label.update(f"{int(progress)}%")

        self.refresh()
