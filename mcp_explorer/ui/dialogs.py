"""Dialog screens for MCP Explorer."""

import asyncio

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea

from ..models import MCPPrompt, MCPServer
from ..services import MCPClientService


class PromptPreviewDialog(ModalScreen[None]):
    """Modal dialog for previewing a prompt."""

    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, server: MCPServer, prompt: MCPPrompt) -> None:
        """Initialize the prompt preview dialog."""
        super().__init__()
        self.server = server
        self.prompt = prompt
        self.client_service = MCPClientService()

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Container(id="preview-container"):
            yield Static(f"Preview: {self.prompt.name}", classes="detail-title")
            yield TextArea(
                "Loading preview...",
                id="preview-content",
                read_only=True,
            )
            with Horizontal(id="preview-buttons"):
                yield Button("Close", id="close-button", variant="primary")

    async def on_mount(self) -> None:
        """Load the prompt preview when mounted."""
        preview_area = self.query_one("#preview-content", TextArea)

        try:
            preview_text = await self.client_service.get_prompt_preview(
                self.server,
                self.prompt.name,
                None,  # TODO: Support prompt arguments
            )
            preview_area.load_text(preview_text)
        except Exception as e:
            preview_area.load_text(f"Error loading preview: {e}")

    @on(Button.Pressed, "#close-button")
    def action_close(self) -> None:
        """Close the dialog."""
        self.dismiss(None)
