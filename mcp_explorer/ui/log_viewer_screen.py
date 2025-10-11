"""Log viewer screen for MCP proxy."""

from typing import List, Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static

from ..models import LogEntry, LogEntryType
from ..proxy import ProxyLogger
from .log_widgets import LogEntryWidget


class LogViewerScreen(Screen):
    """Screen for viewing MCP proxy logs."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "quit", "Quit"),
        ("f3", "search_next", "Next Result"),
        Binding("shift+f3", "search_prev", "Previous Result"),
        ("ctrl+f", "toggle_filters", "Toggle Filters"),
    ]

    def __init__(self, logger: ProxyLogger) -> None:
        """Initialize the log viewer screen.

        Args:
            logger: Proxy logger instance
        """
        super().__init__()
        self.logger = logger
        self.current_filter: Optional[LogEntryType] = None
        self.errors_only = False
        self.search_query = ""
        self.search_results: List[LogEntry] = []
        self.current_search_index = 0
        self.filters_visible = True
        self.auto_refresh = True
        self.last_entry_count = 0
        self.active_filter_id = "filter-all"  # Track which filter button is active

    def compose(self) -> ComposeResult:
        """Compose the log viewer screen."""
        yield Header(show_clock=True)
        yield Footer()

        with Container(id="log-viewer-container"):
            # Top search bar
            with Horizontal(id="log-search-bar"):
                yield Input(placeholder="Search logs... (Press Enter to search)", id="search-input")
                yield Button("◀", id="search-prev", classes="search-nav-btn")
                yield Button("▶", id="search-next", classes="search-nav-btn")
                yield Label("", id="search-results", classes="search-results")

            # Main content area with logs and optional filter sidebar
            with Horizontal(id="log-content"):
                # Logs list (main content)
                with Container(id="log-list-container"):
                    # Stats header
                    yield Static("", id="log-stats", classes="log-stats")
                    # Log entries
                    yield ListView(id="log-list", classes="log-list")

                # Filter sidebar (always composed, but can be hidden)
                with VerticalScroll(id="filter-sidebar"):
                    yield Label("FILTERS", classes="filter-sidebar-title")

                    # Type filters
                    yield Label("Type", classes="filter-section-label")
                    yield Button(
                        "All", id="filter-all", variant="primary", classes="filter-btn"
                    )
                    yield Button("Tools", id="filter-tools", classes="filter-btn")
                    yield Button("Resources", id="filter-resources", classes="filter-btn")
                    yield Button("Prompts", id="filter-prompts", classes="filter-btn")

                    # Server status filters
                    yield Label("Server Status", classes="filter-section-label")
                    yield Button("Server Events", id="filter-server", classes="filter-btn")
                    yield Button("Client Events", id="filter-client", classes="filter-btn")
                    yield Button("Errors Only", id="filter-errors", classes="filter-btn")

                    # Actions
                    yield Label("Actions", classes="filter-section-label")
                    yield Button(
                        "Clear Logs", id="clear-logs", variant="error", classes="filter-btn"
                    )
                    yield Button("Hide Filters", id="toggle-filters", classes="filter-btn")

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        self.last_entry_count = len(self.logger.entries)
        self.refresh_logs()
        self.update_stats()
        # Register callback for live updates
        self.logger.add_update_callback(self._on_new_log_entry)
        # Set up auto-refresh timer (every 0.5 seconds to catch any missed updates)
        self.set_interval(0.5, self._check_for_updates)

    def on_unmount(self) -> None:
        """Clean up when screen is unmounted."""
        # Remove callback to prevent memory leaks
        self.logger.remove_update_callback(self._on_new_log_entry)

    def _on_new_log_entry(self, entry: LogEntry) -> None:
        """Handle new log entry from logger callback.

        Args:
            entry: New log entry
        """
        # Schedule UI update on the main thread
        self.call_later(self.refresh_logs)
        self.call_later(self.update_stats)

    def _check_for_updates(self) -> None:
        """Check for new log entries and update UI if needed."""
        if not self.auto_refresh:
            return

        current_count = len(self.logger.entries)
        if current_count != self.last_entry_count:
            self.last_entry_count = current_count
            self.refresh_logs()
            self.update_stats()

    def refresh_logs(self) -> None:
        """Refresh the log list based on current filters."""
        # Get filtered entries
        entries = self.logger.get_entries(
            entry_type=self.current_filter, search_query=self.search_query or None
        )

        # Filter errors only if enabled
        if self.errors_only:
            entries = [e for e in entries if e.error is not None]

        self._display_entries(entries)

    def _display_entries(self, entries: list) -> None:
        """Display filtered log entries in the list view.

        Args:
            entries: List of LogEntry objects to display
        """
        # Update search results
        self.search_results = entries

        # Populate list
        log_list = self.query_one("#log-list", ListView)
        log_list.clear()

        if not entries:
            # Create a ListItem with empty state message
            empty_item = ListItem()
            empty_item.compose_add_child(Static("No log entries found", classes="empty-state"))
            log_list.append(empty_item)
        else:
            for entry in reversed(entries):  # Most recent first
                log_list.append(LogEntryWidget(entry, self.search_query or None))

        # Update search results count
        if self.search_query:
            results_label = self.query_one("#search-results", Label)
            if len(entries) > 0:
                results_label.update(
                    f"{min(self.current_search_index + 1, len(entries))}/{len(entries)}"
                )
            else:
                results_label.update("No results")

    def update_stats(self) -> None:
        """Update the statistics display."""
        stats = self.logger.get_stats()

        # Display connected clients prominently
        connected_clients = stats.get('connected_clients', 0)
        stats_text = (
            f"Connected Clients: {connected_clients} | "
            f"Total: {stats['total']} | Success: {stats['success']} | Errors: {stats['errors']}"
        )

        if stats["by_type"]:
            type_stats = " | ".join(f"{t.title()}: {c}" for t, c in stats["by_type"].items())
            stats_text += f" | {type_stats}"

        stats_widget = self.query_one("#log-stats", Static)
        stats_widget.update(stats_text)

    # Filter actions
    @on(Button.Pressed, "#filter-all")
    def filter_all(self) -> None:
        """Show all log entries."""
        self.current_filter = None
        self.errors_only = False
        self.set_active_filter("filter-all")
        self.refresh_logs()

    @on(Button.Pressed, "#filter-tools")
    def filter_tools(self) -> None:
        """Show only tool calls."""
        self.current_filter = LogEntryType.TOOL_CALL
        self.errors_only = False
        self.set_active_filter("filter-tools")
        self.refresh_logs()

    @on(Button.Pressed, "#filter-resources")
    def filter_resources(self) -> None:
        """Show only resource reads."""
        self.current_filter = LogEntryType.RESOURCE_READ
        self.errors_only = False
        self.set_active_filter("filter-resources")
        self.refresh_logs()

    @on(Button.Pressed, "#filter-prompts")
    def filter_prompts(self) -> None:
        """Show only prompt gets."""
        self.current_filter = LogEntryType.PROMPT_GET
        self.errors_only = False
        self.set_active_filter("filter-prompts")
        self.refresh_logs()

    @on(Button.Pressed, "#filter-server")
    def filter_server(self) -> None:
        """Show only server status events."""
        # Show server-related events (started, stopped, error)
        self.current_filter = LogEntryType.SERVER_STARTED  # Using as a marker
        self.errors_only = False
        self.set_active_filter("filter-server")
        # Custom filter for all server events
        entries = self.logger.get_entries(search_query=self.search_query or None)
        entries = [
            e
            for e in entries
            if e.entry_type
            in [
                LogEntryType.SERVER_STARTED,
                LogEntryType.SERVER_STOPPED,
                LogEntryType.SERVER_ERROR,
            ]
        ]
        self._display_entries(entries)

    @on(Button.Pressed, "#filter-client")
    def filter_client(self) -> None:
        """Show only client connection events."""
        # Show client-related events (connected, disconnected)
        self.current_filter = LogEntryType.CLIENT_CONNECTED  # Using as a marker
        self.errors_only = False
        self.set_active_filter("filter-client")
        # Custom filter for all client events
        entries = self.logger.get_entries(search_query=self.search_query or None)
        entries = [
            e
            for e in entries
            if e.entry_type
            in [
                LogEntryType.CLIENT_CONNECTED,
                LogEntryType.CLIENT_DISCONNECTED,
            ]
        ]
        self._display_entries(entries)

    @on(Button.Pressed, "#filter-errors")
    def filter_errors(self) -> None:
        """Show only errors."""
        self.errors_only = True
        self.set_active_filter("filter-errors")
        self.refresh_logs()

    def set_active_filter(self, filter_id: str) -> None:
        """Set the active filter button.

        Args:
            filter_id: ID of the filter button to activate
        """
        # Save the active filter ID
        self.active_filter_id = filter_id

        # Reset all buttons
        for button_id in [
            "filter-all",
            "filter-tools",
            "filter-resources",
            "filter-prompts",
            "filter-server",
            "filter-client",
            "filter-errors",
        ]:
            try:
                button = self.query_one(f"#{button_id}", Button)
                button.variant = "default" if button_id != filter_id else "primary"
            except:
                pass  # Handle case where button might not exist yet

    @on(Button.Pressed, "#clear-logs")
    def clear_logs(self) -> None:
        """Clear all logs."""
        self.logger.clear()
        self.refresh_logs()
        self.update_stats()

    # Search actions
    @on(Input.Submitted, "#search-input")
    def search_submitted(self) -> None:
        """Handle search input submission."""
        search_input = self.query_one("#search-input", Input)
        self.search_query = search_input.value
        self.current_search_index = 0
        self.refresh_logs()

    @on(Button.Pressed, "#search-next")
    def action_search_next(self) -> None:
        """Go to next search result."""
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.highlight_current_result()

    @on(Button.Pressed, "#search-prev")
    def action_search_prev(self) -> None:
        """Go to previous search result."""
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            self.highlight_current_result()

    def highlight_current_result(self) -> None:
        """Highlight the current search result."""
        if not self.search_results:
            return

        # Update search results label
        results_label = self.query_one("#search-results", Label)
        if len(self.search_results) > 0:
            results_label.update(f"{self.current_search_index + 1}/{len(self.search_results)}")
        else:
            results_label.update("No results")

        # Scroll to current result
        log_list = self.query_one("#log-list", ListView)
        if 0 <= self.current_search_index < len(log_list.children):
            log_list.index = len(log_list.children) - 1 - self.current_search_index

    def action_toggle_filters(self) -> None:
        """Toggle filter sidebar visibility."""
        self.filters_visible = not self.filters_visible
        # Toggle visibility using CSS display property
        sidebar = self.query_one("#filter-sidebar", VerticalScroll)
        sidebar.display = self.filters_visible
        
        # Update the toggle button text
        try:
            toggle_btn = self.query_one("#toggle-filters", Button)
            toggle_btn.label = "Hide Filters" if self.filters_visible else "Show Filters"
        except:
            pass  # Button might not exist

    @on(Button.Pressed, "#toggle-filters")
    def handle_toggle_filters(self) -> None:
        """Handle toggle filters button press."""
        self.action_toggle_filters()

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
