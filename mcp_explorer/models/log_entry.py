"""Models for proxy logging."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LogEntryType(str, Enum):
    """Type of log entry."""

    TOOL_CALL = "tool_call"
    RESOURCE_READ = "resource_read"
    PROMPT_GET = "prompt_get"
    SERVER_STARTED = "server_started"
    SERVER_STOPPED = "server_stopped"
    SERVER_ERROR = "server_error"
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"


class LogEntry(BaseModel):
    """A log entry for a proxied MCP operation."""

    id: str = Field(default_factory=lambda: str(datetime.now().timestamp()))
    timestamp: datetime = Field(default_factory=datetime.now)
    entry_type: LogEntryType
    server_name: str
    operation_name: str  # tool name, resource URI, or prompt name
    parameters: Dict[str, Any] = Field(default_factory=dict)
    response: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None

    def get_status(self) -> str:
        """Get human-readable status."""
        if self.error:
            return "ERROR"
        elif self.response is not None:
            return "SUCCESS"
        else:
            return "PENDING"

    def get_display_name(self) -> str:
        """Get display name for this entry."""
        type_icon = {
            LogEntryType.TOOL_CALL: "🔧",
            LogEntryType.RESOURCE_READ: "📄",
            LogEntryType.PROMPT_GET: "💬",
        }
        icon = type_icon.get(self.entry_type, "📌")
        return f"{icon} {self.server_name}/{self.operation_name}"

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
