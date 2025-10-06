"""Proxy configuration screen."""

import asyncio
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static, Tree
from textual.widgets._tree import TreeNode

from ..models import MCPServer, ProxyConfig


class ProxyConfigScreen(Screen[None]):
    """Screen for configuring the MCP proxy."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "quit", "Quit"),
        ("s", "save_config", "Save"),
    ]

    def __init__(self, servers: list[MCPServer], config: ProxyConfig) -> None:
        """Initialize the proxy config screen.

        Args:
            servers: List of available servers
            config: Current proxy configuration
        """
        super().__init__()
        self.servers = servers
        self.config = config

    def compose(self) -> ComposeResult:
        """Compose the proxy config screen."""
        yield Header(show_clock=True)
        yield Footer()

        with Container(id="proxy-config-container"):
            # Top control panel
            with Vertical(id="proxy-control-panel"):
                yield Label("Proxy Server Configuration", classes="proxy-config-title")

                # Port and status
                with Horizontal(classes="proxy-settings-row"):
                    yield Label("Port:", classes="setting-label")
                    yield Input(
                        value=str(self.config.port),
                        placeholder="3000",
                        id="proxy-port",
                        classes="port-input",
                    )

                    yield Label("Status:", classes="setting-label status-label")
                    if self.config.enabled:
                        yield Label("● RUNNING", classes="proxy-status proxy-running")
                    else:
                        yield Label("○ STOPPED", classes="proxy-status proxy-stopped")

                # Control buttons
                with Horizontal(classes="proxy-buttons-row"):
                    if self.config.enabled:
                        yield Button("⬛ Stop Proxy", id="toggle-proxy", variant="error")
                    else:
                        yield Button("▶ Start Proxy", id="toggle-proxy", variant="success")

                    yield Button("💾 Save Configuration", id="save-config", variant="primary")

            # Server configurations as unified tree
            yield Label("Select Servers and Capabilities to Proxy", classes="section-title")
            with VerticalScroll(id="server-configs"):
                if not self.servers:
                    yield Static("No servers available", classes="empty-state")
                else:
                    # Create single tree with all servers
                    tree: Tree[dict[str, Any]] = Tree("Servers", id="servers-tree")
                    tree.root.expand()
                    tree.show_root = False  # Hide root node

                    for server in self.servers:
                        # Only show connected servers
                        if server.status.value == "connected":
                            self._add_server_to_tree(tree.root, server)

                    yield tree

    def _add_server_to_tree(self, parent: TreeNode[dict[str, Any]], server: MCPServer) -> None:
        """Add a server and its capabilities to the tree.

        Args:
            parent: Parent tree node
            server: MCP server to add
        """
        # Add server as first-level node
        server_enabled = self.config.is_server_enabled(server.name)
        server_checkbox = "☑" if server_enabled else "☐"
        server_node = parent.add(
            f"{server_checkbox} {server.name}",
            data={"type": "server", "name": server.name},
            expand=True,
        )

        # Add tools
        if server.tools:
            tools_category = server_node.add(
                f"Tools ({len(server.tools)})",
                data={"type": "category", "category": "tools"},
                expand=server_enabled,
            )
            for tool in server.tools:
                tool_enabled = self.config.is_tool_enabled(server.name, tool.name)
                tool_checkbox = "☑" if tool_enabled else "☐"
                tools_category.add_leaf(
                    f"{tool_checkbox} {tool.name}",
                    data={
                        "type": "tool",
                        "server": server.name,
                        "name": tool.name,
                    },
                )

        # Add resources
        if server.resources:
            resources_category = server_node.add(
                f"Resources ({len(server.resources)})",
                data={"type": "category", "category": "resources"},
                expand=server_enabled,
            )
            for resource in server.resources:
                resource_enabled = self.config.is_resource_enabled(server.name, resource.uri)
                resource_checkbox = "☑" if resource_enabled else "☐"
                resources_category.add_leaf(
                    f"{resource_checkbox} {resource.get_display_name()}",
                    data={
                        "type": "resource",
                        "server": server.name,
                        "uri": resource.uri,
                    },
                )

        # Add prompts
        if server.prompts:
            prompts_category = server_node.add(
                f"Prompts ({len(server.prompts)})",
                data={"type": "category", "category": "prompts"},
                expand=server_enabled,
            )
            for prompt in server.prompts:
                prompt_enabled = self.config.is_prompt_enabled(server.name, prompt.name)
                prompt_checkbox = "☑" if prompt_enabled else "☐"
                prompts_category.add_leaf(
                    f"{prompt_checkbox} {prompt.name}",
                    data={
                        "type": "prompt",
                        "server": server.name,
                        "name": prompt.name,
                    },
                )

    @on(Input.Changed, "#proxy-port")
    def update_port(self, event: Input.Changed) -> None:
        """Update proxy port."""
        try:
            port = int(event.value)
            if 1 <= port <= 65535:
                self.config.port = port
        except ValueError:
            pass  # Invalid port number, ignore

    @on(Button.Pressed, "#toggle-proxy")
    async def toggle_proxy(self) -> None:
        """Toggle proxy running state."""
        from ..proxy import ProxyServer

        self.config.enabled = not self.config.enabled

        # Start or stop the proxy server
        if self.config.enabled:
            # Stop any existing proxy server first
            if self.app.proxy_server:
                if self.app.proxy_server.is_running():
                    await self.app.proxy_server.stop()
                self.app.proxy_server = None

            # Create and start new proxy server
            self.app.proxy_server = ProxyServer(
                servers=self.servers,
                config=self.config,
                logger=self.app.proxy_logger,
            )
            # Start server in background task
            asyncio.create_task(self.app.proxy_server.start())
            self.notify(f"Proxy server started on port {self.config.port}", severity="information")
        else:
            # Stop proxy server
            if self.app.proxy_server:
                if self.app.proxy_server.is_running():
                    await self.app.proxy_server.stop()
                self.app.proxy_server = None
                self.notify("Proxy server stopped", severity="information")

        # Update app subtitle
        if hasattr(self.app, "update_subtitle"):
            self.app.update_subtitle()
        # Refresh to update UI
        self.refresh(recompose=True)

    @on(Button.Pressed, "#save-config")
    def action_save_config(self) -> None:
        """Save the configuration."""
        try:
            self.config.save()
            # Update app subtitle in case status changed
            if hasattr(self.app, "update_subtitle"):
                self.app.update_subtitle()
            self.app.notify(
                f"Configuration saved to {self.config.get_config_path()}", severity="information"
            )
        except Exception as e:
            self.app.notify(f"Error saving configuration: {e}", severity="error")

    @on(Tree.NodeSelected)
    def handle_tree_node_selected(self, event: Tree.NodeSelected[dict[str, Any]]) -> None:
        """Handle tree node selection for toggling capabilities."""
        node = event.node
        if not node or not node.data:
            return

        node_type = node.data.get("type")

        # Handle server node - toggle entire server and all children
        if node_type == "server":
            server_name = node.data.get("name")
            if not isinstance(server_name, str):
                return

            # Get the server object
            server = next((s for s in self.servers if s.name == server_name), None)
            if not server:
                return

            # Toggle server state
            current_enabled = self.config.is_server_enabled(server_name)
            new_enabled = not current_enabled

            if new_enabled:
                self.config.enabled_servers.add(server_name)
            else:
                self.config.enabled_servers.discard(server_name)

            # Update all tools
            for tool in server.tools:
                if new_enabled:
                    if server_name not in self.config.enabled_tools:
                        self.config.enabled_tools[server_name] = set()
                    self.config.enabled_tools[server_name].add(tool.name)
                else:
                    if server_name in self.config.enabled_tools:
                        self.config.enabled_tools[server_name].discard(tool.name)

            # Update all resources
            for resource in server.resources:
                if new_enabled:
                    if server_name not in self.config.enabled_resources:
                        self.config.enabled_resources[server_name] = set()
                    self.config.enabled_resources[server_name].add(resource.uri)
                else:
                    if server_name in self.config.enabled_resources:
                        self.config.enabled_resources[server_name].discard(resource.uri)

            # Update all prompts
            for prompt in server.prompts:
                if new_enabled:
                    if server_name not in self.config.enabled_prompts:
                        self.config.enabled_prompts[server_name] = set()
                    self.config.enabled_prompts[server_name].add(prompt.name)
                else:
                    if server_name in self.config.enabled_prompts:
                        self.config.enabled_prompts[server_name].discard(prompt.name)

            # Update UI
            self._update_node_label(node, new_enabled)

            # Update children and expand/collapse
            for child in node.children:
                if child.data and child.data.get("type") == "category":
                    # Expand/collapse category nodes
                    if new_enabled:
                        child.expand()
                    else:
                        child.collapse()

                    # Update all items in category
                    for item_node in child.children:
                        self._update_node_label(item_node, new_enabled)

        # Handle tool node
        elif node_type == "tool":
            server_name = node.data.get("server")
            tool_name = node.data.get("name")
            if not isinstance(server_name, str) or not isinstance(tool_name, str):
                return

            if server_name not in self.config.enabled_tools:
                self.config.enabled_tools[server_name] = set()

            tool_enabled = self.config.is_tool_enabled(server_name, tool_name)
            if tool_enabled:
                self.config.enabled_tools[server_name].discard(tool_name)
            else:
                self.config.enabled_tools[server_name].add(tool_name)

            # Update node label
            self._update_node_label(node, not tool_enabled)

        # Handle resource node
        elif node_type == "resource":
            server_name = node.data.get("server")
            resource_uri = node.data.get("uri")
            if not isinstance(server_name, str) or not isinstance(resource_uri, str):
                return

            if server_name not in self.config.enabled_resources:
                self.config.enabled_resources[server_name] = set()

            resource_enabled = self.config.is_resource_enabled(server_name, resource_uri)
            if resource_enabled:
                self.config.enabled_resources[server_name].discard(resource_uri)
            else:
                self.config.enabled_resources[server_name].add(resource_uri)

            # Update node label
            self._update_node_label(node, not resource_enabled)

        # Handle prompt node
        elif node_type == "prompt":
            server_name = node.data.get("server")
            prompt_name = node.data.get("name")
            if not isinstance(server_name, str) or not isinstance(prompt_name, str):
                return

            if server_name not in self.config.enabled_prompts:
                self.config.enabled_prompts[server_name] = set()

            prompt_enabled = self.config.is_prompt_enabled(server_name, prompt_name)
            if prompt_enabled:
                self.config.enabled_prompts[server_name].discard(prompt_name)
            else:
                self.config.enabled_prompts[server_name].add(prompt_name)

            # Update node label
            self._update_node_label(node, not prompt_enabled)

    def _update_node_label(self, node: TreeNode[dict[str, Any]], enabled: bool) -> None:
        """Update a node's checkbox in its label.

        Args:
            node: Tree node to update
            enabled: Whether the item is enabled
        """
        label = str(node.label)
        # Remove existing checkbox
        if label.startswith("☑ ") or label.startswith("☐ "):
            label = label[2:]
        # Add new checkbox
        checkbox = "☑" if enabled else "☐"
        node.set_label(f"{checkbox} {label}")

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
