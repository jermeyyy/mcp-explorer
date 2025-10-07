"""Proxy configuration screen."""

import asyncio
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static, Tree
from textual.widgets._tree import TreeNode

from ..models import MCPServer, ProxyConfig, ConfigFile


class ProxyConfigScreen(Screen[None]):
    """Screen for configuring the MCP proxy."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, config_files: list[ConfigFile], config: ProxyConfig) -> None:
        """Initialize the proxy config screen.

        Args:
            config_files: List of config files with servers
            config: Current proxy configuration
        """
        super().__init__()
        self.config_files = config_files
        self.config = config

        # Flatten servers for backward compatibility with existing proxy logic
        self.servers: list[MCPServer] = []
        for config_file in config_files:
            self.servers.extend(config_file.servers)

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
                        yield Button("⏹ Stop Proxy", id="toggle-proxy", variant="error")
                    else:
                        yield Button("▶ Start Proxy", id="toggle-proxy", variant="success")

            # Server configurations as unified tree
            yield Label("Select Servers and Capabilities to Proxy", classes="section-title")
            with VerticalScroll(id="server-configs"):
                if not self.servers:
                    yield Static("No servers available", classes="empty-state")
                else:
                    # Create single tree with all servers grouped by config file
                    tree: Tree[dict[str, Any]] = Tree("Servers", id="servers-tree")
                    tree.root.expand()
                    tree.show_root = False  # Hide root node
                    # Note: Tree remains interactive for scrolling even when proxy is running
                    # The selection handler prevents actual changes when proxy is enabled

                    # Use hierarchical config file structure
                    for config_file in self.config_files:
                        # Count connected servers in this config
                        connected_servers = [s for s in config_file.servers if s.status.value == "connected"]
                        
                        # Count enabled servers in this config
                        enabled_server_count = self._count_enabled_servers(config_file)
                        
                        # Determine if all servers/capabilities in this config are enabled
                        all_enabled = self._is_config_file_fully_enabled(config_file)
                        button_text = "[bold red][Disable All][/bold red]" if all_enabled else "[bold green][Enable All][/bold green]"
                        
                        # Add config file node with enable/disable button and x/y counter
                        config_node = tree.root.add(
                            f"📁 {config_file.get_display_path()} ({enabled_server_count}/{len(connected_servers)}) {button_text}",
                            data={"type": "config_file", "path": config_file.path, "config_file": config_file},
                            expand=True,
                        )

                        # Add servers under this config (only connected ones)
                        for server in connected_servers:
                            self._add_server_to_tree(config_node, config_file.path, server)

                    yield tree

    def _format_label(self, text: str, enabled: bool) -> str:
        """Format a tree node label with Rich markup for visual distinction.

        Args:
            text: The text to format
            enabled: Whether the item is enabled

        Returns:
            Formatted text with Rich markup
        """
        if enabled:
            # Green and bold for enabled items
            return f"[bold green]{text}[/bold green]"
        else:
            # Dim gray for disabled items
            return f"[dim]{text}[/dim]"

    def _count_enabled_servers(self, config_file: ConfigFile) -> int:
        """Count how many servers in a config file have at least one enabled capability.
        
        Args:
            config_file: The config file to check
            
        Returns:
            Number of servers with at least one enabled tool, resource, or prompt
        """
        enabled_count = 0
        
        for server in config_file.servers:
            if server.status.value != "connected":
                continue
            
            has_enabled = False
            
            # Check if any tool is enabled
            for tool in server.tools:
                if self.config.is_tool_enabled(config_file.path, server.name, tool.name):
                    has_enabled = True
                    break
            
            # Check if any resource is enabled
            if not has_enabled:
                for resource in server.resources:
                    if self.config.is_resource_enabled(config_file.path, server.name, resource.uri):
                        has_enabled = True
                        break
            
            # Check if any prompt is enabled
            if not has_enabled:
                for prompt in server.prompts:
                    if self.config.is_prompt_enabled(config_file.path, server.name, prompt.name):
                        has_enabled = True
                        break
            
            if has_enabled:
                enabled_count += 1
        
        return enabled_count

    def _is_config_file_fully_enabled(self, config_file: ConfigFile) -> bool:
        """Check if all servers and their capabilities in a config file are enabled.
        
        Args:
            config_file: The config file to check
            
        Returns:
            True if all capabilities are enabled, False otherwise
        """
        has_any_capability = False
        
        for server in config_file.servers:
            if server.status.value != "connected":
                continue
                
            # Check all tools
            for tool in server.tools:
                has_any_capability = True
                if not self.config.is_tool_enabled(config_file.path, server.name, tool.name):
                    return False
            
            # Check all resources
            for resource in server.resources:
                has_any_capability = True
                if not self.config.is_resource_enabled(config_file.path, server.name, resource.uri):
                    return False
            
            # Check all prompts
            for prompt in server.prompts:
                has_any_capability = True
                if not self.config.is_prompt_enabled(config_file.path, server.name, prompt.name):
                    return False
        
        # If there are no capabilities at all, consider it disabled
        return has_any_capability

    def _add_server_to_tree(self, parent: TreeNode[dict[str, Any]], config_file_path: str, server: MCPServer) -> None:
        """Add a server and its capabilities to the tree.

        Args:
            parent: Parent tree node
            config_file_path: Path to the config file this server is from
            server: MCP server to add
        """
        # Add server as first-level node (no checkbox, no color formatting)
        server_node = parent.add(
            server.name,
            data={"type": "server", "name": server.name, "config_path": config_file_path},
            expand=True,
        )

        # Add tools
        if server.tools:
            # Count enabled tools
            enabled_tools = sum(1 for t in server.tools if self.config.is_tool_enabled(config_file_path, server.name, t.name))
            
            # Add category with enable/disable buttons and x/y counter
            all_enabled = all(self.config.is_tool_enabled(config_file_path, server.name, t.name) for t in server.tools)
            button_text = "[bold red][Disable All][/bold red]" if all_enabled else "[bold green][Enable All][/bold green]"
            tools_category = server_node.add(
                f"Tools ({enabled_tools}/{len(server.tools)}) {button_text}",
                data={"type": "category", "category": "tools", "server": server.name, "config_path": config_file_path},
                expand=False,
            )
            for tool in server.tools:
                tool_enabled = self.config.is_tool_enabled(config_file_path, server.name, tool.name)
                tool_checkbox = "☑" if tool_enabled else "☐"
                label = self._format_label(f"{tool_checkbox} {tool.name}", tool_enabled)
                tools_category.add_leaf(
                    label,
                    data={
                        "type": "tool",
                        "server": server.name,
                        "name": tool.name,
                        "config_path": config_file_path,
                    },
                )

        # Add resources
        if server.resources:
            # Count enabled resources
            enabled_resources = sum(1 for r in server.resources if self.config.is_resource_enabled(config_file_path, server.name, r.uri))
            
            all_enabled = all(self.config.is_resource_enabled(config_file_path, server.name, r.uri) for r in server.resources)
            button_text = "[bold red][Disable All][/bold red]" if all_enabled else "[bold green][Enable All][/bold green]"
            resources_category = server_node.add(
                f"Resources ({enabled_resources}/{len(server.resources)}) {button_text}",
                data={"type": "category", "category": "resources", "server": server.name, "config_path": config_file_path},
                expand=False,
            )
            for resource in server.resources:
                resource_enabled = self.config.is_resource_enabled(config_file_path, server.name, resource.uri)
                resource_checkbox = "☑" if resource_enabled else "☐"
                label = self._format_label(f"{resource_checkbox} {resource.get_display_name()}", resource_enabled)
                resources_category.add_leaf(
                    label,
                    data={
                        "type": "resource",
                        "server": server.name,
                        "uri": resource.uri,
                        "config_path": config_file_path,
                    },
                )

        # Add prompts
        if server.prompts:
            # Count enabled prompts
            enabled_prompts = sum(1 for p in server.prompts if self.config.is_prompt_enabled(config_file_path, server.name, p.name))
            
            all_enabled = all(self.config.is_prompt_enabled(config_file_path, server.name, p.name) for p in server.prompts)
            button_text = "[bold red][Disable All][/bold red]" if all_enabled else "[bold green][Enable All][/bold green]"
            prompts_category = server_node.add(
                f"Prompts ({enabled_prompts}/{len(server.prompts)}) {button_text}",
                data={"type": "category", "category": "prompts", "server": server.name, "config_path": config_file_path},
                expand=False,
            )
            for prompt in server.prompts:
                prompt_enabled = self.config.is_prompt_enabled(config_file_path, server.name, prompt.name)
                prompt_checkbox = "☑" if prompt_enabled else "☐"
                label = self._format_label(f"{prompt_checkbox} {prompt.name}", prompt_enabled)
                prompts_category.add_leaf(
                    label,
                    data={
                        "type": "prompt",
                        "server": server.name,
                        "name": prompt.name,
                        "config_path": config_file_path,
                    },
                )

    @on(Input.Changed, "#proxy-port")
    def update_port(self, event: Input.Changed) -> None:
        """Update proxy port."""
        try:
            port = int(event.value)
            if 1 <= port <= 65535:
                self.config.port = port
                self._auto_save_config()
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

    @on(Tree.NodeSelected)
    def handle_tree_node_selected(self, event: Tree.NodeSelected[dict[str, Any]]) -> None:
        """Handle tree node selection for toggling capabilities."""
        # Prevent changes when proxy is running
        if self.config.enabled:
            self.notify("Stop the proxy server before making changes to the configuration", severity="warning")
            return

        node = event.node
        if not node or not node.data:
            return

        node_type = node.data.get("type")

        # Handle config file node - toggle all servers in this config
        if node_type == "config_file":
            config_file = node.data.get("config_file")
            if not isinstance(config_file, ConfigFile):
                return
            
            # Determine if we should enable or disable all
            all_enabled = self._is_config_file_fully_enabled(config_file)
            new_enabled = not all_enabled
            
            # Toggle all capabilities for all servers in this config
            for server in config_file.servers:
                if server.status.value != "connected":
                    continue
                
                # Get the server key for this config
                server_key = self.config.make_server_key(config_file.path, server.name)
                
                # Initialize server in config if needed
                if server_key not in self.config.enabled_tools:
                    self.config.enabled_tools[server_key] = set()
                if server_key not in self.config.enabled_resources:
                    self.config.enabled_resources[server_key] = set()
                if server_key not in self.config.enabled_prompts:
                    self.config.enabled_prompts[server_key] = set()
                
                # Toggle all tools
                for tool in server.tools:
                    if new_enabled:
                        self.config.enabled_tools[server_key].add(tool.name)
                    else:
                        self.config.enabled_tools[server_key].discard(tool.name)
                
                # Toggle all resources
                for resource in server.resources:
                    if new_enabled:
                        self.config.enabled_resources[server_key].add(resource.uri)
                    else:
                        self.config.enabled_resources[server_key].discard(resource.uri)
                
                # Toggle all prompts
                for prompt in server.prompts:
                    if new_enabled:
                        self.config.enabled_prompts[server_key].add(prompt.name)
                    else:
                        self.config.enabled_prompts[server_key].discard(prompt.name)
            
            # Update config file node label
            connected_servers = [s for s in config_file.servers if s.status.value == "connected"]
            enabled_server_count = self._count_enabled_servers(config_file)
            button_text = "[bold red][Disable All][/bold red]" if new_enabled else "[bold green][Enable All][/bold green]"
            node.set_label(f"📁 {config_file.get_display_path()} ({enabled_server_count}/{len(connected_servers)}) {button_text}")
            
            # Update all child nodes recursively
            self._update_tree_branch(node, new_enabled)
            
            # Auto-save configuration
            self._auto_save_config()
            return

        # Handle category node - toggle all items in category
        if node_type == "category":
            category = node.data.get("category")
            server_name = node.data.get("server")
            config_path = node.data.get("config_path")
            if not isinstance(server_name, str) or not isinstance(category, str) or not isinstance(config_path, str):
                return

            # Get the server object
            server = next((s for s in self.servers if s.name == server_name and s.source_file == config_path), None)
            if not server:
                return

            # Get server key
            server_key = self.config.make_server_key(config_path, server_name)

            # Determine if we should enable or disable all
            if category == "tools":
                all_enabled = all(self.config.is_tool_enabled(config_path, server_name, t.name) for t in server.tools)
                new_enabled = not all_enabled
                
                if server_key not in self.config.enabled_tools:
                    self.config.enabled_tools[server_key] = set()
                
                for tool in server.tools:
                    if new_enabled:
                        self.config.enabled_tools[server_key].add(tool.name)
                    else:
                        self.config.enabled_tools[server_key].discard(tool.name)
                
                # Update child nodes
                for child in node.children:
                    self._update_node_label(child, new_enabled)
                
            elif category == "resources":
                all_enabled = all(self.config.is_resource_enabled(config_path, server_name, r.uri) for r in server.resources)
                new_enabled = not all_enabled
                
                if server_key not in self.config.enabled_resources:
                    self.config.enabled_resources[server_key] = set()
                
                for resource in server.resources:
                    if new_enabled:
                        self.config.enabled_resources[server_key].add(resource.uri)
                    else:
                        self.config.enabled_resources[server_key].discard(resource.uri)
                
                # Update child nodes
                for child in node.children:
                    self._update_node_label(child, new_enabled)
                    
            elif category == "prompts":
                all_enabled = all(self.config.is_prompt_enabled(config_path, server_name, p.name) for p in server.prompts)
                new_enabled = not all_enabled
                
                if server_key not in self.config.enabled_prompts:
                    self.config.enabled_prompts[server_key] = set()
                
                for prompt in server.prompts:
                    if new_enabled:
                        self.config.enabled_prompts[server_key].add(prompt.name)
                    else:
                        self.config.enabled_prompts[server_key].discard(prompt.name)
                
                # Update child nodes
                for child in node.children:
                    self._update_node_label(child, new_enabled)
            
            # Update category label with x/y counter
            enabled_count = len(node.children) if new_enabled else 0
            button_text = "[bold red][Disable All][/bold red]" if new_enabled else "[bold green][Enable All][/bold green]"
            node.set_label(f"{category.title()} ({enabled_count}/{len(node.children)}) {button_text}")
            
            # Auto-save configuration
            self._auto_save_config()

        # Handle tool node
        elif node_type == "tool":
            server_name = node.data.get("server")
            tool_name = node.data.get("name")
            config_path = node.data.get("config_path")
            if not isinstance(server_name, str) or not isinstance(tool_name, str) or not isinstance(config_path, str):
                return

            server_key = self.config.make_server_key(config_path, server_name)
            if server_key not in self.config.enabled_tools:
                self.config.enabled_tools[server_key] = set()

            tool_enabled = self.config.is_tool_enabled(config_path, server_name, tool_name)
            if tool_enabled:
                self.config.enabled_tools[server_key].discard(tool_name)
            else:
                self.config.enabled_tools[server_key].add(tool_name)

            # Update node label
            self._update_node_label(node, not tool_enabled)

            # Auto-save configuration after tool toggle
            self._auto_save_config()

        # Handle resource node
        elif node_type == "resource":
            server_name = node.data.get("server")
            resource_uri = node.data.get("uri")
            config_path = node.data.get("config_path")
            if not isinstance(server_name, str) or not isinstance(resource_uri, str) or not isinstance(config_path, str):
                return

            server_key = self.config.make_server_key(config_path, server_name)
            if server_key not in self.config.enabled_resources:
                self.config.enabled_resources[server_key] = set()

            resource_enabled = self.config.is_resource_enabled(config_path, server_name, resource_uri)
            if resource_enabled:
                self.config.enabled_resources[server_key].discard(resource_uri)
            else:
                self.config.enabled_resources[server_key].add(resource_uri)

            # Update node label
            self._update_node_label(node, not resource_enabled)

            # Auto-save configuration after resource toggle
            self._auto_save_config()

        # Handle prompt node
        elif node_type == "prompt":
            server_name = node.data.get("server")
            prompt_name = node.data.get("name")
            config_path = node.data.get("config_path")
            if not isinstance(server_name, str) or not isinstance(prompt_name, str) or not isinstance(config_path, str):
                return

            server_key = self.config.make_server_key(config_path, server_name)
            if server_key not in self.config.enabled_prompts:
                self.config.enabled_prompts[server_key] = set()

            prompt_enabled = self.config.is_prompt_enabled(config_path, server_name, prompt_name)
            if prompt_enabled:
                self.config.enabled_prompts[server_key].discard(prompt_name)
            else:
                self.config.enabled_prompts[server_key].add(prompt_name)

            # Update node label
            self._update_node_label(node, not prompt_enabled)

            # Auto-save configuration after prompt toggle
            self._auto_save_config()

    def _auto_save_config(self) -> None:
        """Automatically save configuration after changes."""
        try:
            self.config.save()
        except Exception as e:
            self.app.notify(f"Error auto-saving configuration: {e}", severity="error")

    def _update_node_label(self, node: TreeNode[dict[str, Any]], enabled: bool) -> None:
        """Update a node's checkbox in its label.

        Args:
            node: Tree node to update
            enabled: Whether the item is enabled
        """
        label = str(node.label)

        # Remove Rich markup tags if present
        label = label.replace("[bold green]", "").replace("[/bold green]", "")
        label = label.replace("[dim]", "").replace("[/dim]", "")

        # Remove existing checkbox
        if label.startswith("☑ ") or label.startswith("☐ "):
            label = label[2:]

        # Add new checkbox
        checkbox = "☑" if enabled else "☐"
        new_label = f"{checkbox} {label}"

        # Apply Rich markup formatting
        node.set_label(self._format_label(new_label, enabled))

    def _update_tree_branch(self, node: TreeNode[dict[str, Any]], enabled: bool) -> None:
        """Recursively update all child nodes in a tree branch.
        
        Args:
            node: Parent tree node
            enabled: Whether items should be enabled
        """
        for child in node.children:
            child_type = child.data.get("type") if child.data else None
            
            if child_type == "category":
                # Update category button with x/y counter
                category = child.data.get("category", "")
                enabled_count = len(child.children) if enabled else 0
                button_text = "[bold red][Disable All][/bold red]" if enabled else "[bold green][Enable All][/bold green]"
                child.set_label(f"{category.title()} ({enabled_count}/{len(child.children)}) {button_text}")
                # Recursively update category children
                self._update_tree_branch(child, enabled)
            elif child_type in ["tool", "resource", "prompt"]:
                # Update individual item checkbox
                self._update_node_label(child, enabled)
            else:
                # Recursively update any other children (like server nodes)
                self._update_tree_branch(child, enabled)

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
