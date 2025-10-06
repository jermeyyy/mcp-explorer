"""Main TUI application for MCP Explorer."""

import asyncio
from pathlib import Path
from typing import List, Optional

from textual.app import App

from ..models import MCPServer, ProxyConfig
from ..proxy import ProxyLogger, ProxyServer
from ..services import MCPDiscoveryService
from .screens import LoadingScreen, ServerListScreen, SplashScreen
from .log_viewer_screen import LogViewerScreen
from .proxy_config_screen import ProxyConfigScreen


class MCPExplorerApp(App):
    """TUI application for exploring MCP servers."""

    TITLE = "MCP Explorer - Model Context Protocol Browser & Proxy"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_servers", "Refresh"),
        ("p", "show_proxy_config", "Proxy Config"),
        ("l", "show_logs", "View Logs"),
    ]

    def __init__(self) -> None:
        """Initialize the MCP Explorer app."""
        super().__init__()
        self.discovery_service = MCPDiscoveryService()
        self.servers: List[MCPServer] = []

        # Proxy components - load config from file
        self.proxy_config = ProxyConfig.load()
        # Always start with proxy disabled - user must explicitly start it
        self.proxy_config.enabled = False
        self.proxy_logger = ProxyLogger()
        self.proxy_server: Optional[ProxyServer] = None

        # Set initial subtitle
        self.update_subtitle()

    def update_subtitle(self) -> None:
        """Update subtitle with current proxy status."""
        if self.proxy_config.enabled:
            self.sub_title = f"Proxy: ON @localhost:{self.proxy_config.port}"
        else:
            self.sub_title = "Proxy: OFF"

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        # Start the initialization process
        self.run_worker(self._run_initialization, exclusive=True)

    async def _run_initialization(self) -> None:
        """Run the initialization sequence with splash screen."""
        # Create and push splash screen
        splash = SplashScreen()
        await self.push_screen(splash)

        # Wait for splash screen to fully render and start animating
        await asyncio.sleep(0.3)

        try:
            # Update splash: Loading configuration
            splash.update_status("Loading configuration files", 25)
            await asyncio.sleep(0.1)

            # Update splash: Discovering servers
            splash.update_status("Scanning for MCP servers", 50)
            await asyncio.sleep(0.1)

            # Discover servers with progress updates
            await self._discover_with_progress(splash)

            # Update splash: Complete (initialization is done)
            splash.update_status("System ready", 100)
            await asyncio.sleep(0.5)

        except Exception as e:
            # Handle any unexpected errors during startup
            print(f"Error during app initialization: {e}")
            import traceback

            traceback.print_exc()
            splash.update_status("Initialization completed with errors", 100)
            await asyncio.sleep(0.5)

        # Pop splash screen and show server list
        await self.pop_screen()
        await self.push_screen(ServerListScreen(self.servers))

    async def _discover_with_progress(self, splash: SplashScreen) -> None:
        """Discover servers and update progress in real-time.

        Args:
            splash: The splash screen to update with progress
        """
        # Get server configurations
        server_configs = self.discovery_service.config_loader.discover_servers()

        if not server_configs:
            self.servers = []
            return

        total_servers = len(server_configs)
        self.servers = []

        # Process servers one by one to show progress
        for idx, (name, config) in enumerate(server_configs.items(), 1):
            # Update progress: 50% (scan complete) + up to 25% for connection progress
            progress = 50 + int((idx / total_servers) * 25)

            # Update UI
            splash.update_status(
                f"Connecting to {name} ({idx}/{total_servers})",
                progress
            )

            # Yield control to the event loop to keep animations smooth
            await asyncio.sleep(0.05)

            # Initialize the server
            try:
                server = await self.discovery_service._init_server(name, config)
                self.servers.append(server)
            except Exception as e:
                print(f"Error initializing {name}: {e}")

            # Yield control again after processing
            await asyncio.sleep(0.05)

    async def load_servers(self) -> None:
        """Load all MCP servers."""
        try:
            self.servers = await self.discovery_service.discover_all_servers()
        except Exception as e:
            print(f"Error loading servers: {e}")
            import traceback

            traceback.print_exc()
            # Initialize with empty list if discovery fails completely
            self.servers = []

    async def action_refresh_servers(self) -> None:
        """Refresh the server list."""
        # Show splash screen
        splash = SplashScreen()
        await self.push_screen(splash)

        # Give splash screen time to render
        await asyncio.sleep(0.3)

        try:
            # Update splash: Refreshing
            splash.update_status("Refreshing server list", 25)
            await asyncio.sleep(0.1)

            # Update splash: Scanning
            splash.update_status("Scanning for MCP servers", 50)
            await asyncio.sleep(0.1)

            # Reload servers with progress updates
            await self._discover_with_progress(splash)

            # Update splash: Complete
            splash.update_status("System ready", 100)
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Error refreshing servers: {e}")
            import traceback

            traceback.print_exc()
            splash.update_status("Refresh completed with errors", 100)
            await asyncio.sleep(0.5)

        # Pop splash screen and show updated server list
        await self.pop_screen()
        await self.push_screen(ServerListScreen(self.servers))

    def action_show_proxy_config(self) -> None:
        """Show the proxy configuration screen."""
        self.push_screen(ProxyConfigScreen(self.servers, self.proxy_config))

    def action_show_logs(self) -> None:
        """Show the log viewer screen."""
        self.push_screen(LogViewerScreen(self.proxy_logger))

    def action_quit(self) -> None:
        """Quit the application."""
        # Stop proxy if running
        if self.proxy_server and self.proxy_server.is_running():
            asyncio.create_task(self.proxy_server.stop())

        self.discovery_service.cleanup()
        self.exit()
