"""Tool Terminal Screen - Chat-like UI for testing MCP server tools."""

import io
import json
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.client.transports import StreamableHttpTransport
from mcp.types import LoggingMessageNotificationParams
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Select, Static

from ..models import MCPServer, MCPTool, ProxyConfig


@contextmanager
def suppress_stdout_stderr():
    """Suppress stdout and stderr to prevent TUI glitches."""
    new_out, new_err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class ChatMessage(Static):
    """A single message in the chat interface."""

    def __init__(
        self,
        message_type: str,
        content: str,
        timestamp: datetime | None = None,
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


class ToolTerminalScreen(Screen[None]):
    """Interactive terminal for testing MCP server tools."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("ctrl+k", "scroll_up", "Scroll Up"),
        ("ctrl+j", "scroll_down", "Scroll Down"),
    ]

    def __init__(self, servers: list[MCPServer], proxy_config: ProxyConfig) -> None:
        """Initialize the tool terminal screen.
        Args:
            servers: List of available MCP servers (used for reference only)
            proxy_config: Proxy configuration with enabled servers/tools
        """
        super().__init__()
        self.servers = servers
        self.proxy_config = proxy_config
        self.selected_server: MCPServer | None = None
        self.selected_tool: MCPTool | None = None
        self.tool_params: dict[str, Any] = {}
        self.current_param_index = 0
        self.enabled_servers = self._get_enabled_servers()
        # Elicitation state
        self._elicitation_pending: bool = False
        self._elicitation_response: Any | None = None
        self._elicitation_action: str = "accept"
        self._elicitation_history: list[dict[str, Any]] = []
        # Elicitation field collection (like tool parameters)
        self._elicitation_fields: list[dict[str, Any]] = []
        self._elicitation_field_values: dict[str, Any] = {}
        self._current_elicitation_field_index: int = 0
        self._elicitation_collecting_fields: bool = False

    def _get_enabled_servers(self) -> list[MCPServer]:
        """Get list of servers that are enabled in the proxy configuration."""
        enabled = []
        for server in self.servers:
            config_file_path = server.source_file or ""
            if self.proxy_config.is_server_enabled(config_file_path, server.name):
                enabled_tools = [
                    tool
                    for tool in server.tools
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
                            classes="terminal-error",
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
                    yield Button(
                        "Execute", id="execute-btn", variant="success", classes="execute-button"
                    )

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
        self.selected_server = next(
            (s for s in self.enabled_servers if s.name == server_name), None
        )
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
            (
                f"Selected server: {self.selected_server.name} "
                f"with {len(self.selected_server.tools)} tools"
            ),
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
            (t for t in self.selected_server.tools if t.name == tool_name), None
        )
        if not self.selected_tool:
            return
        self.tool_params = {}
        self.current_param_index = 0
        self._update_tool_info()
        param_info = self.selected_tool.get_parameter_summary()
        description = self.selected_tool.description or "No description"
        self._add_message(
            "system",
            f"Selected tool: {self.selected_tool.name}\n{description}\n{param_info}",
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

    def _prompt_next_elicitation_field(self) -> None:
        """Prompt for the next elicitation field value.

        Similar to _prompt_next_parameter but for elicitation schema fields.
        When all fields are collected, sets _elicitation_collecting_fields to False.
        """
        if self._current_elicitation_field_index >= len(self._elicitation_fields):
            # All fields collected
            self._elicitation_collecting_fields = False
            self._elicitation_pending = False
            return

        field = self._elicitation_fields[self._current_elicitation_field_index]
        field_name = field["name"]
        field_type = field.get("type", "string")
        field_required = field.get("required", True)
        field_description = field.get("description", "")
        field_default = field.get("default")
        field_enum = field.get("enum")

        required_text = "[REQUIRED]" if field_required else "[optional]"
        prompt_text = f"🔔 Enter {field_name} ({field_type}) {required_text}"

        if field_description:
            prompt_text += f"\n   {field_description}"
        if field_default is not None:
            prompt_text += f"\n   Default: {field_default}"
        if field_enum:
            prompt_text += f"\n   Options: {', '.join(str(e) for e in field_enum)}"

        self._set_input_prompt(prompt_text)
        self._add_message("system", prompt_text)

        # Focus the input
        terminal_input = self.query_one("#terminal-input", Input)
        terminal_input.focus()

    def _parse_elicitation_schema(
        self, response_type: type | None, params: Any
    ) -> list[dict[str, Any]]:
        """Parse elicitation response_type to extract fields for user input.

        FastMCP provides a dataclass type that was generated from the JSON schema.
        We introspect this dataclass to get field information.

        Args:
            response_type: The dataclass type created by FastMCP from JSON schema
            params: ElicitRequestParams from MCP (contains raw schema as fallback)

        Returns:
            List of field dictionaries with name, type, required, description, etc.
        """
        import dataclasses
        from typing import Literal, get_args, get_origin, get_type_hints

        fields: list[dict[str, Any]] = []

        # If response_type is None, no fields needed (acknowledgment only)
        if response_type is None:
            return fields

        # Try to get fields from the dataclass
        if hasattr(response_type, "__dataclass_fields__"):
            try:
                type_hints = get_type_hints(response_type)
            except Exception:
                type_hints = {}

            for field_name, field_obj in response_type.__dataclass_fields__.items():
                field_type = type_hints.get(field_name, field_obj.type)

                # Determine the type string and enum values
                type_str = "string"
                enum_values: list[Any] | None = None

                # Check for Literal type (enum-like)
                origin = get_origin(field_type)
                if origin is Literal:
                    enum_values = list(get_args(field_type))
                    type_str = "enum"
                elif field_type is str or field_type == "str":
                    type_str = "string"
                elif field_type is int or field_type == "int":
                    type_str = "integer"
                elif field_type is float or field_type == "float":
                    type_str = "number"
                elif field_type is bool or field_type == "bool":
                    type_str = "boolean"
                elif hasattr(field_type, "__members__"):  # Python Enum
                    enum_values = list(field_type.__members__.keys())
                    type_str = "enum"
                else:
                    type_str = getattr(field_type, "__name__", str(field_type))

                # Check if field has a default value
                has_default = field_obj.default is not dataclasses.MISSING
                has_default_factory = field_obj.default_factory is not dataclasses.MISSING
                is_required = not (has_default or has_default_factory)

                default_value = None
                if has_default:
                    default_value = field_obj.default
                elif has_default_factory:
                    try:
                        default_value = field_obj.default_factory()
                    except Exception:
                        pass

                field_info: dict[str, Any] = {
                    "name": field_name,
                    "type": type_str,
                    "required": is_required,
                    "description": "",
                    "default": default_value,
                }

                if enum_values:
                    field_info["enum"] = enum_values

                fields.append(field_info)

        # Fallback: try to get fields from params.requestedSchema if no dataclass fields
        if not fields:
            schema = getattr(params, "requestedSchema", None)
            if schema and isinstance(schema, dict):
                properties = schema.get("properties", {})
                required_fields = schema.get("required", [])

                for field_name, field_schema in properties.items():
                    field_info = {
                        "name": field_name,
                        "type": field_schema.get("type", "string"),
                        "required": field_name in required_fields,
                        "description": field_schema.get(
                            "description", field_schema.get("title", "")
                        ),
                        "default": field_schema.get("default"),
                    }

                    if "enum" in field_schema:
                        field_info["enum"] = field_schema["enum"]
                    if "const" in field_schema:
                        field_info["const"] = field_schema["const"]

                    fields.append(field_info)

        return fields

    def _parse_elicitation_field_value(self, field: dict[str, Any], value: str) -> Any:
        """Parse a string value according to field type.

        Args:
            field: Field definition with type info
            value: Raw string value from user input

        Returns:
            Parsed value in appropriate type
        """
        field_type = field.get("type", "string")

        if field_type == "integer":
            return int(value)
        elif field_type == "number":
            return float(value)
        elif field_type == "boolean":
            return value.lower() in ["true", "1", "yes", "y"]
        elif field_type in ["object", "array"]:
            return json.loads(value)
        else:
            # Default to string
            return value

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
        if hasattr(result, "content"):
            result_parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    result_parts.append(item.text)
                elif hasattr(item, "type"):
                    if item.type == "text" and hasattr(item, "text"):
                        result_parts.append(item.text)
                    elif item.type == "image" and hasattr(item, "data"):
                        result_parts.append(f"[Image: {getattr(item, 'mimeType', 'unknown')}]")
                    elif item.type == "resource" and hasattr(item, "resource"):
                        result_parts.append(f"[Resource: {item.resource.get('uri', 'unknown')}]")
                    else:
                        result_parts.append(str(item))
                else:
                    result_parts.append(str(item))
            return "\n".join(result_parts) if result_parts else str(result)
        elif isinstance(result, (dict, list)):
            return json.dumps(result, indent=2, ensure_ascii=False)
        else:
            return str(result)

    def _format_execution_summary(self, result: Any) -> str:
        """Format a complete execution summary including elicitations and final result.

        Args:
            result: The final tool execution result

        Returns:
            Formatted string showing complete execution flow
        """
        parts = []

        # Add elicitation history if present
        if self._elicitation_history:
            parts.append("📋 Execution Summary:\n")

            for idx, elicitation in enumerate(self._elicitation_history, 1):
                parts.append(f"\n🔔 Elicitation #{idx}:")
                parts.append(f"   Request: {elicitation['message']}")

                if elicitation["action"] == "accept":
                    response_value = elicitation["response"]
                    # Format the response value nicely
                    if isinstance(response_value, dict):
                        response_str = json.dumps(response_value, indent=2)
                    else:
                        response_str = str(response_value)
                    parts.append(f"   ✓ Response: {response_str} (accepted)")
                elif elicitation["action"] == "decline":
                    parts.append("   ✗ Response: (declined)")
                elif elicitation["action"] == "cancel":
                    parts.append("   ⊘ Response: (cancelled)")

            parts.append("\n" + "─" * 50)

        # Add final result
        parts.append("\n📋 Final Result:")
        result_str = self._format_tool_result(result)
        parts.append(result_str)

        return "\n".join(parts)

    @on(Button.Pressed, "#send-btn")
    @on(Input.Submitted, "#terminal-input")
    async def handle_send(self, event: Button.Pressed | Input.Submitted) -> None:
        """Handle sending input (collecting parameter values or elicitation responses)."""
        terminal_input = self.query_one("#terminal-input", Input)
        value = terminal_input.value.strip()

        # Handle elicitation field collection (multi-field form)
        if self._elicitation_collecting_fields:
            # Check for special commands first
            if value.lower() == "decline":
                self._add_message("user", "Declining elicitation request")
                self._elicitation_action = "decline"
                self._elicitation_collecting_fields = False
                self._elicitation_pending = False
                terminal_input.value = ""
                return
            elif value.lower() == "cancel":
                self._add_message("user", "Cancelling elicitation request")
                self._elicitation_action = "cancel"
                self._elicitation_collecting_fields = False
                self._elicitation_pending = False
                terminal_input.value = ""
                return

            # Handle current field
            if self._current_elicitation_field_index < len(self._elicitation_fields):
                field = self._elicitation_fields[self._current_elicitation_field_index]
                field_name = field["name"]
                field_required = field.get("required", True)

                # Handle empty value for optional fields
                if not value:
                    if not field_required:
                        # Use default or skip
                        if field.get("default") is not None:
                            self._elicitation_field_values[field_name] = field["default"]
                            self._add_message(
                                "user", f"{field_name} = {field['default']} (default)"
                            )
                        else:
                            self._add_message("user", f"Skipping optional field: {field_name}")
                        self._current_elicitation_field_index += 1
                        terminal_input.value = ""
                        self._prompt_next_elicitation_field()
                        return
                    else:
                        # Required field, don't allow empty
                        return

                # Parse and store the value
                try:
                    parsed_value = self._parse_elicitation_field_value(field, value)

                    # Validate enum/const constraints
                    if "enum" in field and parsed_value not in field["enum"]:
                        valid_options = ", ".join(str(e) for e in field["enum"])
                        self._add_message(
                            "error",
                            f"Invalid value. Must be one of: {valid_options}",
                        )
                        return
                    if "const" in field and parsed_value != field["const"]:
                        self._add_message("error", f"Value must be: {field['const']}")
                        return

                    self._elicitation_field_values[field_name] = parsed_value
                    self._add_message("user", f"{field_name} = {value}")
                    self._current_elicitation_field_index += 1
                    terminal_input.value = ""
                    self._prompt_next_elicitation_field()

                except (ValueError, json.JSONDecodeError) as e:
                    self._add_message("error", f"Invalid value for {field_name}: {e}")
                    return

            return

        # Handle simple elicitation responses (legacy fallback for simple schemas)
        if self._elicitation_pending:
            if not value:
                return

            # Check for special commands
            if value.lower() == "decline":
                self._add_message("user", "Declining elicitation request")
                self._elicitation_action = "decline"
                self._elicitation_pending = False
            elif value.lower() == "cancel":
                self._add_message("user", "Cancelling elicitation request")
                self._elicitation_action = "cancel"
                self._elicitation_pending = False
            else:
                # Store the response
                self._add_message("user", f"Response: {value}")
                self._elicitation_response = value
                self._elicitation_action = "accept"
                self._elicitation_pending = False

            terminal_input.value = ""
            return

        # Original parameter collection logic
        if not self.selected_tool:
            return

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

    async def _elicitation_handler(
        self,
        message: str,
        response_type: type | None,
        params: Any,
        context: Any | None = None,
    ) -> Any:
        """Handle elicitation requests from MCP tools.

        This handler displays the elicitation message to the user and collects
        their response through the terminal UI. For multi-field schemas, it prompts
        for each field individually, similar to tool parameter collection.

        Users can:
        - Enter data for each field
        - Type 'decline' to decline the elicitation
        - Type 'cancel' to cancel the elicitation
        - Press Enter on optional fields to skip them

        Args:
            message: The elicitation message from the server
            response_type: The expected response type (dataclass or None for empty)
            params: ElicitRequestParams with requestedSchema
            context: Optional context information

        Returns:
            User's response in the appropriate type, or ElicitResult for explicit control
        """
        import asyncio

        # Create elicitation record
        type_name = (
            getattr(response_type, "__name__", str(response_type)) if response_type else "None"
        )
        elicitation_record: dict[str, Any] = {
            "message": message,
            "response_type": type_name,
            "params": str(params),
            "context": context,
            "timestamp": datetime.now(),
            "response": None,
            "action": "accept",
        }

        # Display elicitation message to user
        self._add_message("system", f"🔔 Tool Request:\n{message}")

        # Parse elicitation schema to get fields from response_type dataclass
        self._elicitation_fields = self._parse_elicitation_schema(response_type, params)
        self._elicitation_field_values = {}
        self._current_elicitation_field_index = 0

        # Enable input controls for elicitation
        send_btn = self.query_one("#send-btn", Button)
        terminal_input = self.query_one("#terminal-input", Input)

        send_btn.disabled = False
        terminal_input.disabled = False

        # Check if we have fields to collect
        if self._elicitation_fields:
            # Multi-field elicitation - show field overview
            fields_summary = "\n".join(
                f"  • {f['name']} ({f.get('type', 'string')})"
                + (" [required]" if f.get("required", True) else " [optional]")
                for f in self._elicitation_fields
            )
            self._add_message("system", f"Expected fields:\n{fields_summary}")
            self._add_message(
                "system",
                "Enter values for each field. Type 'decline' or 'cancel' to abort.",
            )

            # Start field collection
            self._elicitation_collecting_fields = True
            self._elicitation_pending = True
            self._elicitation_action = "accept"

            # Prompt for first field
            self._prompt_next_elicitation_field()

            try:
                # Wait for all fields to be collected
                while self._elicitation_pending or self._elicitation_collecting_fields:
                    await asyncio.sleep(0.1)
            finally:
                send_btn.disabled = True
                terminal_input.disabled = True

            # Check if user declined/cancelled during field collection
            if self._elicitation_action in ["decline", "cancel"]:
                elicitation_record["action"] = self._elicitation_action
                self._elicitation_history.append(elicitation_record)
                return ElicitResult(action=self._elicitation_action)

            # All fields collected - build response
            elicitation_record["action"] = "accept"
            elicitation_record["response"] = self._elicitation_field_values
            self._elicitation_history.append(elicitation_record)

            # Return the collected data
            if response_type and hasattr(response_type, "__dataclass_fields__"):
                try:
                    return response_type(**self._elicitation_field_values)
                except TypeError as e:
                    self._add_message("error", f"Failed to create response: {e}")
                    # Fall back to returning dict
                    return self._elicitation_field_values
            else:
                # Return as dict for other cases
                return self._elicitation_field_values

        else:
            # No fields / empty schema - use simple single-input mode
            if response_type is None:
                # Empty schema - just need acknowledgment
                self._add_message("system", "Press Enter or type 'ok' to acknowledge")
            else:
                self._add_message("system", f"Expected response type: {type_name}")
                self._add_message(
                    "system", "Type your response, or use 'decline' or 'cancel' commands"
                )

            self._set_input_prompt("⏳ Elicitation response")
            terminal_input.focus()

            # Set simple elicitation state
            self._elicitation_pending = True
            self._elicitation_response = None
            self._elicitation_action = "accept"

            try:
                while self._elicitation_pending:
                    await asyncio.sleep(0.1)
            finally:
                send_btn.disabled = True
                terminal_input.disabled = True

            # Update elicitation record
            elicitation_record["action"] = self._elicitation_action
            elicitation_record["response"] = self._elicitation_response
            self._elicitation_history.append(elicitation_record)

            # Check action and return appropriate result
            if self._elicitation_action == "decline":
                return ElicitResult(action="decline")
            elif self._elicitation_action == "cancel":
                return ElicitResult(action="cancel")
            else:
                response = self._elicitation_response

                # Handle empty schema (just acknowledge)
                if response_type is None:
                    return {}

                # Guard against None response
                if response is None:
                    return ElicitResult(action="decline")

                # Try to parse response based on response_type
                if hasattr(response_type, "__dataclass_fields__"):
                    if isinstance(response, str):
                        try:
                            response_data = json.loads(response)
                            return response_type(**response_data)
                        except (json.JSONDecodeError, TypeError) as e:
                            self._add_message("error", f"Failed to parse response: {e}")
                            return ElicitResult(action="decline")
                    elif isinstance(response, dict):
                        return response_type(**response)

                # For primitive types
                if response_type is str:
                    return str(response)
                elif response_type is int:
                    try:
                        return int(response)
                    except ValueError:
                        return ElicitResult(action="decline")
                elif response_type is float:
                    try:
                        return float(response)
                    except ValueError:
                        return ElicitResult(action="decline")
                elif response_type is bool:
                    return str(response).lower() in ["true", "1", "yes"]

                return response

    async def _log_handler(self, params: LoggingMessageNotificationParams) -> None:
        """Handle log messages from the server."""
        # Consume logs to prevent them from being printed to stdout
        # Optionally we could display them in the TUI:
        # self._add_message("system", f"Log [{params.level}]: {params.data}")
        pass

    @on(Button.Pressed, "#execute-btn")
    async def handle_execute(self, event: Button.Pressed) -> None:
        """Execute the selected tool with collected parameters.

        Uses run_worker to execute in background, allowing the event loop
        to continue processing events (like elicitation input) during execution.
        """
        if not self.selected_server or not self.selected_tool:
            self._add_message("error", "Please select a server and tool first")
            return
        required_params = {p.name for p in self.selected_tool.parameters if p.required}
        missing = required_params - set(self.tool_params.keys())
        if missing:
            self._add_message("error", f"Missing required parameters: {', '.join(missing)}")
            return

        # Clear elicitation history at start of execution
        self._elicitation_history = []

        params_str = json.dumps(self.tool_params, indent=2) if self.tool_params else "{}"
        self._add_message(
            "user",
            f"Executing {self.selected_tool.name} with parameters:\n{params_str}",
        )

        # Disable UI controls during execution
        send_btn = self.query_one("#send-btn", Button)
        execute_btn = self.query_one("#execute-btn", Button)
        terminal_input = self.query_one("#terminal-input", Input)
        server_select = self.query_one("#server-select", Select)
        tool_select = self.query_one("#tool-select", Select)

        send_btn.disabled = True
        execute_btn.disabled = True
        terminal_input.disabled = True
        server_select.disabled = True
        tool_select.disabled = True

        # Run tool execution in background worker to allow event loop to process
        # elicitation input events
        self.run_worker(
            self._execute_tool_async(),
            name="tool_execution",
            exclusive=True,
        )

    async def _execute_tool_async(self) -> None:
        """Execute the tool in background, allowing elicitation to work properly."""
        if not self.selected_server or not self.selected_tool:
            return

        send_btn = self.query_one("#send-btn", Button)
        execute_btn = self.query_one("#execute-btn", Button)
        terminal_input = self.query_one("#terminal-input", Input)
        server_select = self.query_one("#server-select", Select)
        tool_select = self.query_one("#tool-select", Select)

        try:
            # Use prefixed tool name for proxy
            prefixed_tool_name = f"{self.selected_server.name}_{self.selected_tool.name}"

            # Connect to the proxy server (which supports elicitation forwarding)
            proxy_url = f"http://localhost:{self.proxy_config.port}/mcp"
            transport = StreamableHttpTransport(url=proxy_url)

            # Create client with elicitation handler support
            client = Client(
                transport,
                elicitation_handler=self._elicitation_handler,
                log_handler=self._log_handler,
            )

            start_time = datetime.now()
            async with client:
                result = await client.call_tool(prefixed_tool_name, self.tool_params)
            duration = (datetime.now() - start_time).total_seconds()

            # Format result with execution summary if elicitations occurred
            if self._elicitation_history:
                result_str = self._format_execution_summary(result)
            else:
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
            terminal_input.disabled = False
            server_select.disabled = False
            tool_select.disabled = False

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
