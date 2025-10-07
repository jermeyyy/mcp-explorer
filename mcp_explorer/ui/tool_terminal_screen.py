"""Tool Terminal Screen - Chat-like UI for testing MCP server tools."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastmcp import Client
from fastmcp.client.transports import SSETransport
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Select, Static
from ..models import MCPServer, MCPTool, ProxyConfig
class ChatMessage(Static):
    """A single message in the chat interface."""
    def __init__(
        self,
        message_type: str,
        content: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Initialize a chat message.
        Args:
            message_type: Type of message ('user', 'system', 'result', 'error')
            content: Message content
            timestamp: Message timestamp (defaults to now)
        """
        super().__init__()
        self.message_type = message_type
        self.content = content
        self.timestamp = timestamp or datetime.now()
    def compose(self) -> ComposeResult:
        """Compose the chat message."""
        # Format timestamp
        time_str = self.timestamp.strftime("%H:%M:%S")
        # Create styled message based on type
        with Container(classes=f"chat-message chat-message-{self.message_type}"):
            yield Static(time_str, classes="message-timestamp")
            if self.message_type == "user":
                yield Static("❯ User", classes="message-sender")
            elif self.message_type == "system":
                yield Static("⚙ System", classes="message-sender")
            elif self.message_type == "result":
                yield Static("✓ Result", classes="message-sender")
            elif self.message_type == "error":
                yield Static("✗ Error", classes="message-sender")
            yield Static(self.content, classes="message-content")
class ToolTerminalScreen(Screen):
    """Interactive terminal for testing MCP server tools."""
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("ctrl+k", "scroll_up", "Scroll Up"),
        ("ctrl+j", "scroll_down", "Scroll Down"),
    ]
    def __init__(self, servers: List[MCPServer], proxy_config: ProxyConfig) -> None:
        """Initialize the tool terminal screen.
        Args:
            servers: List of available MCP servers (used for reference only)
            proxy_config: Proxy configuration with enabled servers/tools
        """
        super().__init__()
        self.servers = servers
        self.proxy_config = proxy_config
        self.selected_server: Optional[MCPServer] = None
        self.selected_tool: Optional[MCPTool] = None
        self.tool_params: Dict[str, Any] = {}
        self.current_param_index = 0
        self.enabled_servers = self._get_enabled_servers()
    def _get_enabled_servers(self) -> List[MCPServer]:
        """Get list of servers that are enabled in the proxy configuration."""
        enabled = []
        for server in self.servers:
            config_file_path = server.source_file or ""
            if self.proxy_config.is_server_enabled(config_file_path, server.name):
                enabled_tools = [
                    tool for tool in server.tools
                    if self.proxy_config.is_tool_enabled(config_file_path, server.name, tool.name)
                ]
                if enabled_tools:
                    from copy import copy
                    server_copy = copy(server)
                    server_copy.tools = enabled_tools
                    enabled.append(server_copy)
        return enabled
    def compose(self) -> ComposeResult:
        """Compose the tool terminal screen."""
        yield Header(show_clock=True)
        yield Footer()
        with Container(id="terminal-container"):
            with Container(id="terminal-control-panel"):
                yield Static("Tool Terminal", classes="terminal-title")
                with Horizontal(id="terminal-selectors"):
                    server_options = [
                        (f"{s.name} ({len(s.tools)} tools)", s.name)
                        for s in self.enabled_servers
                        if s.tools
                    ]
                    if server_options:
                        yield Select(
                            options=server_options,
                            prompt="Select Server",
                            id="server-select",
                            classes="terminal-select",
                        )
                    else:
                        yield Static(
                            "No servers with tools enabled in proxy configuration",
                            classes="terminal-error"
                        )
                    yield Select(
                        options=[],
                        prompt="Select Tool",
                        id="tool-select",
                        classes="terminal-select",
                    )
                yield Static("", id="tool-info", classes="tool-info")
            with VerticalScroll(id="chat-area"):
                yield ChatMessage(
                    "system",
                    "Welcome to the Tool Terminal! Select a server and tool to begin testing.",
                )
            with Container(id="terminal-input-area"):
                yield Static("", id="input-prompt", classes="input-prompt-text")
                with Horizontal(id="input-controls"):
                    yield Input(
                        placeholder="Type parameter value or command...",
                        id="terminal-input",
                        classes="terminal-input-field",
                    )
                    yield Button("Send", id="send-btn", variant="primary", classes="send-button")
                    yield Button("Execute", id="execute-btn", variant="success", classes="execute-button")
    def on_mount(self) -> None:
        """Set up initial state when screen is mounted."""
        # Only try to focus server select if it exists (when there are enabled servers)
        try:
            server_select = self.query_one("#server-select", Select)
            if server_select:
                self.call_after_refresh(lambda: server_select.focus())
        except Exception:
            # No server select widget (no enabled servers), that's ok
            pass
    @on(Select.Changed, "#server-select")
    def handle_server_change(self, event: Select.Changed) -> None:
        """Handle server selection change."""
        if event.value == Select.BLANK:
            return
        server_name = str(event.value)
        self.selected_server = next((s for s in self.enabled_servers if s.name == server_name), None)
        if not self.selected_server:
            return
        tool_select = self.query_one("#tool-select", Select)
        tool_options = [
            (f"{t.name} - {t.description or 'No description'}"[:50], t.name)
            for t in self.selected_server.tools
        ]
        tool_select.set_options(tool_options)
        self._add_message(
            "system",
            f"Selected server: {self.selected_server.name} with {len(self.selected_server.tools)} tools",
        )
        self.selected_tool = None
        self.tool_params = {}
        self.current_param_index = 0
        self._update_tool_info()
    @on(Select.Changed, "#tool-select")
    def handle_tool_change(self, event: Select.Changed) -> None:
        """Handle tool selection change."""
        if event.value == Select.BLANK or not self.selected_server:
            return
        tool_name = str(event.value)
        self.selected_tool = next(
            (t for t in self.selected_server.tools if t.name == tool_name),
            None
        )
        if not self.selected_tool:
            return
        self.tool_params = {}
        self.current_param_index = 0
        self._update_tool_info()
        param_info = self.selected_tool.get_parameter_summary()
        self._add_message(
            "system",
            f"Selected tool: {self.selected_tool.name}\n{self.selected_tool.description or 'No description'}\n{param_info}",
        )
        if self.selected_tool.parameters:
            self._prompt_next_parameter()
        else:
            self._set_input_prompt("Tool has no parameters. Click 'Execute' to run.")
            execute_btn = self.query_one("#execute-btn", Button)
            execute_btn.focus()
    def _update_tool_info(self) -> None:
        """Update the tool info display."""
        tool_info = self.query_one("#tool-info", Static)
        if self.selected_tool:
            info_text = f"Tool: {self.selected_tool.name}"
            if self.selected_tool.parameters:
                required = sum(1 for p in self.selected_tool.parameters if p.required)
                optional = len(self.selected_tool.parameters) - required
                info_text += f" | Params: {required} required, {optional} optional"
            else:
                info_text += " | No parameters"
            tool_info.update(info_text)
        else:
            tool_info.update("")
    def _prompt_next_parameter(self) -> None:
        """Prompt for the next parameter value."""
        if not self.selected_tool or self.current_param_index >= len(self.selected_tool.parameters):
            self._set_input_prompt("All parameters collected. Click 'Execute' to run.")
            return
        param = self.selected_tool.parameters[self.current_param_index]
        required_text = "[REQUIRED]" if param.required else "[optional]"
        prompt_text = f"Enter {param.name} ({param.type}) {required_text}"
        if param.description:
            prompt_text += f"\n{param.description}"
        self._set_input_prompt(prompt_text)
        self._add_message("system", prompt_text)
        terminal_input = self.query_one("#terminal-input", Input)
        terminal_input.focus()
    def _set_input_prompt(self, text: str) -> None:
        """Set the input prompt text."""
        prompt = self.query_one("#input-prompt", Static)
        prompt.update(text)
    def _add_message(self, message_type: str, content: str) -> None:
        """Add a message to the chat area."""
        chat_area = self.query_one("#chat-area", VerticalScroll)
        message = ChatMessage(message_type, content)
        chat_area.mount(message)
        self.call_after_refresh(lambda: chat_area.scroll_end(animate=True))
    def _format_tool_result(self, result: Any) -> str:
        """Format a tool result for display, handling MCP protocol response format."""
        if hasattr(result, 'content'):
            result_parts = []
            for item in result.content:
                if hasattr(item, 'text'):
                    result_parts.append(item.text)
                elif hasattr(item, 'type'):
                    if item.type == 'text' and hasattr(item, 'text'):
                        result_parts.append(item.text)
                    elif item.type == 'image' and hasattr(item, 'data'):
                        result_parts.append(f"[Image: {getattr(item, 'mimeType', 'unknown')}]")
                    elif item.type == 'resource' and hasattr(item, 'resource'):
                        result_parts.append(f"[Resource: {item.resource.get('uri', 'unknown')}]")
                    else:
                        result_parts.append(str(item))
                else:
                    result_parts.append(str(item))
            return '\n'.join(result_parts) if result_parts else str(result)
        elif isinstance(result, (dict, list)):
            return json.dumps(result, indent=2, ensure_ascii=False)
        else:
            return str(result)
    @on(Button.Pressed, "#send-btn")
    @on(Input.Submitted, "#terminal-input")
    async def handle_send(self, event: Button.Pressed | Input.Submitted) -> None:
        """Handle sending input (collecting parameter values)."""
        if not self.selected_tool:
            return
        terminal_input = self.query_one("#terminal-input", Input)
        value = terminal_input.value.strip()
        if not value:
            if self.current_param_index < len(self.selected_tool.parameters):
                param = self.selected_tool.parameters[self.current_param_index]
                if not param.required:
                    self._add_message("user", f"Skipping optional parameter: {param.name}")
                    self.current_param_index += 1
                    terminal_input.value = ""
                    self._prompt_next_parameter()
                    return
            return
        if self.current_param_index < len(self.selected_tool.parameters):
            param = self.selected_tool.parameters[self.current_param_index]
            parsed_value: Any = value
            if param.type in ["object", "array"]:
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    self._add_message("error", f"Invalid JSON for {param.type} parameter")
                    return
            elif param.type == "number":
                try:
                    parsed_value = float(value)
                except ValueError:
                    self._add_message("error", f"Invalid number: {value}")
                    return
            elif param.type == "integer":
                try:
                    parsed_value = int(value)
                except ValueError:
                    self._add_message("error", f"Invalid integer: {value}")
                    return
            elif param.type == "boolean":
                parsed_value = value.lower() in ["true", "1", "yes"]
            self.tool_params[param.name] = parsed_value
            self._add_message("user", f"{param.name} = {value}")
            self.current_param_index += 1
            terminal_input.value = ""
            self._prompt_next_parameter()
    @on(Button.Pressed, "#execute-btn")
    async def handle_execute(self, event: Button.Pressed) -> None:
        """Execute the selected tool with collected parameters."""
        if not self.selected_server or not self.selected_tool:
            self._add_message("error", "Please select a server and tool first")
            return
        required_params = {p.name for p in self.selected_tool.parameters if p.required}
        missing = required_params - set(self.tool_params.keys())
        if missing:
            self._add_message("error", f"Missing required parameters: {', '.join(missing)}")
            return
        params_str = json.dumps(self.tool_params, indent=2) if self.tool_params else "{}"
        self._add_message(
            "user",
            f"Executing {self.selected_tool.name} with parameters:\n{params_str}",
        )
        send_btn = self.query_one("#send-btn", Button)
        execute_btn = self.query_one("#execute-btn", Button)
        send_btn.disabled = True
        execute_btn.disabled = True
        try:
            prefixed_tool_name = f"{self.selected_server.name}__{self.selected_tool.name}"
            start_time = datetime.now()
            proxy_url = f"http://localhost:{self.proxy_config.port}/sse"
            transport = SSETransport(url=proxy_url)
            client = Client(transport)
            async with client:
                result = await client.call_tool(prefixed_tool_name, self.tool_params)
            duration = (datetime.now() - start_time).total_seconds()
            result_str = self._format_tool_result(result)
            self._add_message(
                "result",
                f"Success! (took {duration:.2f}s)\n{result_str}",
            )
        except Exception as e:
            self._add_message("error", f"Tool execution failed: {str(e)}")
        finally:
            send_btn.disabled = False
            execute_btn.disabled = False
            self.tool_params = {}
            self.current_param_index = 0
            self._prompt_next_parameter()
    def action_clear_chat(self) -> None:
        """Clear the chat history."""
        chat_area = self.query_one("#chat-area", VerticalScroll)
        chat_area.remove_children()
        chat_area.mount(
            ChatMessage(
                "system",
                "Chat cleared. Select a server and tool to begin testing.",
            )
        )
    def action_scroll_up(self) -> None:
        """Scroll chat area up."""
        chat_area = self.query_one("#chat-area", VerticalScroll)
        chat_area.scroll_up()
    def action_scroll_down(self) -> None:
        """Scroll chat area down."""
        chat_area = self.query_one("#chat-area", VerticalScroll)
        chat_area.scroll_down()
    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
