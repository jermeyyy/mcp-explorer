"""Widgets for log viewer."""

import json
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Input, Label, ListItem, Static

from ..models import LogEntry


class LogEntryWidget(ListItem):
    """Claude-inspired expandable log entry widget with inline details."""

    MAX_PREVIEW_LINES = 3
    MAX_PREVIEW_CHARS = 150

    def __init__(self, entry: LogEntry, search_query: Optional[str] = None) -> None:
        """Initialize the log entry widget.

        Args:
            entry: Log entry to display
            search_query: Optional search query for highlighting
        """
        super().__init__()
        self.entry = entry
        self.search_query = search_query
        self.expanded = False

    def compose(self) -> ComposeResult:
        """Compose the log entry widget with Claude-inspired inline design."""
        # Apply card styling directly to the ListItem (no inner container)
        self.add_class("log-entry-card")

        # Header with timestamp, operation, and status
        with Horizontal(classes="log-entry-header"):
            # Status indicator dot
            status = self.entry.get_status()
            status_class = f"log-status-dot log-status-{status.lower()}"
            yield Static("●", classes=status_class)

            # Timestamp
            time_str = self.entry.timestamp.strftime("%H:%M:%S")
            yield Static(time_str, classes="log-time")

            # Type icon and operation
            yield Static(self.entry.get_display_name(), classes="log-operation")

            # Duration
            if self.entry.duration_ms is not None:
                duration_str = f"{self.entry.duration_ms:.0f}ms"
                yield Static(duration_str, classes="log-duration")

        # Content area - always show preview, expand for full details
        with Container(classes="log-entry-content"):
                # Show preview of content inline
                preview = self._get_content_preview()
                if preview:
                    yield Static(preview, classes="log-content-preview")

                # Show expand button if content is long
                if self._has_expandable_content():
                    expand_text = "Show less" if self.expanded else "Show more"
                    expand_icon = "▲" if self.expanded else "▼"
                    yield Button(
                        f"{expand_icon} {expand_text}",
                        id="toggle-expand",
                        classes="log-expand-btn",
                    )

                # Expanded view - shown when expanded
                if self.expanded:
                    with Container(classes="log-entry-details"):
                        # Parameters
                        if self.entry.parameters:
                            yield Static("Parameters", classes="log-detail-label")
                            params_json = json.dumps(self.entry.parameters, indent=2)
                            yield Static(params_json, classes="log-detail-json")

                        # Response
                        if self.entry.response is not None:
                            yield Static("Response", classes="log-detail-label")
                            if isinstance(self.entry.response, (dict, list)):
                                response_json = json.dumps(self.entry.response, indent=2)
                            else:
                                response_json = str(self.entry.response)
                            yield Static(response_json, classes="log-detail-json")

                        # Error
                        if self.entry.error:
                            yield Static("Error", classes="log-detail-label log-error-label")
                            yield Static(self.entry.error, classes="log-error-content")

    def _get_content_preview(self) -> str:
        """Get a preview of the log content.

        Returns:
            Preview text to display
        """
        # For errors, show error preview
        if self.entry.error:
            error_lines = self.entry.error.split("\n")
            if len(error_lines) > 1:
                return f"❌ Error: {error_lines[0][:100]}..."
            return f"❌ Error: {self.entry.error[:100]}"

        # For successful operations, show response preview
        if self.entry.response is not None:
            if isinstance(self.entry.response, str):
                lines = self.entry.response.split("\n")
                preview = "\n".join(lines[: self.MAX_PREVIEW_LINES])
                if len(lines) > self.MAX_PREVIEW_LINES or len(preview) > self.MAX_PREVIEW_CHARS:
                    return preview[: self.MAX_PREVIEW_CHARS] + "..."
                return preview
            elif isinstance(self.entry.response, (dict, list)):
                response_json = json.dumps(self.entry.response, indent=2)
                lines = response_json.split("\n")
                preview = "\n".join(lines[: self.MAX_PREVIEW_LINES])
                if len(lines) > self.MAX_PREVIEW_LINES:
                    return preview + "\n..."
                return preview

        # For pending or operations with parameters
        if self.entry.parameters:
            params_str = ", ".join(f"{k}={v}" for k, v in list(self.entry.parameters.items())[:3])
            if len(self.entry.parameters) > 3:
                params_str += ", ..."
            return f"⏳ {params_str}"

        return ""

    def _has_expandable_content(self) -> bool:
        """Check if content is long enough to warrant expand/collapse.

        Returns:
            True if content should be expandable
        """
        # Always expandable if we have parameters or detailed response
        if self.entry.parameters:
            return True

        if self.entry.response is not None:
            if isinstance(self.entry.response, str):
                lines = self.entry.response.split("\n")
                return (
                    len(lines) > self.MAX_PREVIEW_LINES
                    or len(self.entry.response) > self.MAX_PREVIEW_CHARS
                )
            elif isinstance(self.entry.response, (dict, list)):
                response_json = json.dumps(self.entry.response, indent=2)
                lines = response_json.split("\n")
                return len(lines) > self.MAX_PREVIEW_LINES

        if self.entry.error:
            return len(self.entry.error) > 100

        return False

    def toggle_expand(self) -> None:
        """Toggle expanded state."""
        self.expanded = not self.expanded
        self.refresh(recompose=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "toggle-expand":
            event.stop()
            self.toggle_expand()


class SearchBar(Container):
    """Search bar widget with navigation."""

    def __init__(self) -> None:
        """Initialize the search bar."""
        super().__init__(id="search-bar")
        self.query = ""
        self.result_count = 0
        self.current_result = 0

    def compose(self) -> ComposeResult:
        """Compose the search bar."""
        with Horizontal():
            yield Label("Search:", classes="search-label")
            yield Input(placeholder="Enter search query...", id="search-input")
            yield Button("Find", id="search-find", variant="primary")
            yield Button("Previous", id="search-prev")
            yield Button("Next (F3)", id="search-next")
            yield Label("", id="search-results", classes="search-results")

    def update_results(self, count: int, current: int) -> None:
        """Update search results display.

        Args:
            count: Total number of results
            current: Current result index (1-based)
        """
        self.result_count = count
        self.current_result = current

        results_label = self.query_one("#search-results", Label)
        if count > 0:
            results_label.update(f"{current}/{count}")
        elif self.query:
            results_label.update("No results")
        else:
            results_label.update("")

    def get_query(self) -> str:
        """Get current search query.

        Returns:
            Search query text
        """
        search_input = self.query_one("#search-input", Input)
        return search_input.value

    def clear_query(self) -> None:
        """Clear the search query."""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.query = ""
        self.update_results(0, 0)


class LogFilterBar(Container):
    """Filter bar for logs."""

    def __init__(self) -> None:
        """Initialize the filter bar."""
        super().__init__(id="filter-bar")

    def compose(self) -> ComposeResult:
        """Compose the filter bar."""
        with Horizontal():
            yield Label("Filter:", classes="filter-label")
            yield Button("All", id="filter-all", variant="primary")
            yield Button("Tools", id="filter-tools")
            yield Button("Resources", id="filter-resources")
            yield Button("Prompts", id="filter-prompts")
            yield Button("Errors Only", id="filter-errors")
            yield Button("Clear Logs", id="clear-logs", classes="filter-clear")

    def set_active_filter(self, filter_id: str) -> None:
        """Set the active filter button.

        Args:
            filter_id: ID of the filter button to activate
        """
        # Reset all buttons
        for button_id in [
            "filter-all",
            "filter-tools",
            "filter-resources",
            "filter-prompts",
            "filter-errors",
        ]:
            button = self.query_one(f"#{button_id}", Button)
            button.variant = "default" if button_id != filter_id else "primary"
