"""Logging system for MCP proxy operations."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..models import LogEntry, LogEntryType


class ProxyLogger:
    """Logger for MCP proxy operations."""

    def __init__(self, max_entries: int = 1000) -> None:
        """Initialize the proxy logger.

        Args:
            max_entries: Maximum number of log entries to keep in memory
        """
        self.max_entries = max_entries
        self.entries: List[LogEntry] = []
        self._log_file: Optional[Path] = None
        self._update_callbacks: List[Callable[[LogEntry], None]] = []

    def set_log_file(self, log_file: Path) -> None:
        """Set the file to persist logs to.

        Args:
            log_file: Path to log file
        """
        self._log_file = log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_tool_call(
        self,
        server_name: str,
        tool_name: str,
        parameters: Dict[str, Any],
        response: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> LogEntry:
        """Log a tool call.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool
            parameters: Tool parameters
            response: Tool response (if completed)
            error: Error message (if failed)
            duration_ms: Duration in milliseconds

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.TOOL_CALL,
            server_name=server_name,
            operation_name=tool_name,
            parameters=parameters,
            response=response,
            error=error,
            duration_ms=duration_ms,
        )
        self._add_entry(entry)
        return entry

    def log_resource_read(
        self,
        server_name: str,
        resource_uri: str,
        response: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> LogEntry:
        """Log a resource read.

        Args:
            server_name: Name of the server
            resource_uri: Resource URI
            response: Resource response (if completed)
            error: Error message (if failed)
            duration_ms: Duration in milliseconds

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.RESOURCE_READ,
            server_name=server_name,
            operation_name=resource_uri,
            response=response,
            error=error,
            duration_ms=duration_ms,
        )
        self._add_entry(entry)
        return entry

    def log_prompt_get(
        self,
        server_name: str,
        prompt_name: str,
        parameters: Dict[str, Any],
        response: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> LogEntry:
        """Log a prompt get.

        Args:
            server_name: Name of the server
            prompt_name: Name of the prompt
            parameters: Prompt parameters
            response: Prompt response (if completed)
            error: Error message (if failed)
            duration_ms: Duration in milliseconds

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.PROMPT_GET,
            server_name=server_name,
            operation_name=prompt_name,
            parameters=parameters,
            response=response,
            error=error,
            duration_ms=duration_ms,
        )
        self._add_entry(entry)
        return entry

    def log_server_started(
        self,
        port: int,
        enabled_servers: int,
        message: Optional[str] = None,
    ) -> LogEntry:
        """Log server start event.

        Args:
            port: Port number the server is listening on
            enabled_servers: Number of enabled backend servers
            message: Optional additional message

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.SERVER_STARTED,
            server_name="proxy",
            operation_name="start",
            parameters={"port": port, "enabled_servers": enabled_servers},
            response=message or f"Proxy server started on port {port}",
        )
        self._add_entry(entry)
        return entry

    def log_server_stopped(
        self,
        message: Optional[str] = None,
    ) -> LogEntry:
        """Log server stop event.

        Args:
            message: Optional additional message

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.SERVER_STOPPED,
            server_name="proxy",
            operation_name="stop",
            parameters={},
            response=message or "Proxy server stopped",
        )
        self._add_entry(entry)
        return entry

    def log_server_error(
        self,
        error: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        """Log server error event.

        Args:
            error: Error message
            details: Optional error details

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.SERVER_ERROR,
            server_name="proxy",
            operation_name="error",
            parameters=details or {},
            error=error,
        )
        self._add_entry(entry)
        return entry

    def log_client_connected(
        self,
        client_id: str,
        remote_addr: Optional[str] = None,
    ) -> LogEntry:
        """Log client connection event.

        Args:
            client_id: Unique client identifier
            remote_addr: Client's remote address

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.CLIENT_CONNECTED,
            server_name="proxy",
            operation_name="client_connect",
            parameters={"client_id": client_id, "remote_addr": remote_addr or "unknown"},
            response=f"Client {client_id} connected from {remote_addr or 'unknown'}",
        )
        self._add_entry(entry)
        return entry

    def log_client_disconnected(
        self,
        client_id: str,
        reason: Optional[str] = None,
    ) -> LogEntry:
        """Log client disconnection event.

        Args:
            client_id: Unique client identifier
            reason: Optional disconnection reason

        Returns:
            The created log entry
        """
        entry = LogEntry(
            entry_type=LogEntryType.CLIENT_DISCONNECTED,
            server_name="proxy",
            operation_name="client_disconnect",
            parameters={"client_id": client_id, "reason": reason or "normal"},
            response=f"Client {client_id} disconnected: {reason or 'normal'}",
        )
        self._add_entry(entry)
        return entry

    def _add_entry(self, entry: LogEntry) -> None:
        """Add an entry to the log.

        Args:
            entry: Log entry to add
        """
        self.entries.append(entry)

        # Trim to max entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries :]

        # Persist to file if configured
        if self._log_file:
            self._persist_entry(entry)

        # Notify callbacks
        for callback in self._update_callbacks:
            try:
                callback(entry)
            except Exception:
                # Ignore callback errors
                pass

    def add_update_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """Add a callback to be notified of new log entries.

        Args:
            callback: Function to call when a new entry is added
        """
        self._update_callbacks.append(callback)

    def remove_update_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """Remove a previously registered callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._update_callbacks:
            self._update_callbacks.remove(callback)

    def _persist_entry(self, entry: LogEntry) -> None:
        """Persist an entry to the log file.

        Args:
            entry: Log entry to persist
        """
        if not self._log_file:
            return

        try:
            with open(self._log_file, "a") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception:
            # Ignore persistence errors
            pass

    def get_entries(
        self,
        server_name: Optional[str] = None,
        entry_type: Optional[LogEntryType] = None,
        search_query: Optional[str] = None,
    ) -> List[LogEntry]:
        """Get log entries with optional filtering.

        Args:
            server_name: Filter by server name
            entry_type: Filter by entry type
            search_query: Search in operation names, parameters, and responses

        Returns:
            Filtered list of log entries
        """
        entries = self.entries

        if server_name:
            entries = [e for e in entries if e.server_name == server_name]

        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]

        if search_query:
            query_lower = search_query.lower()
            filtered = []
            for entry in entries:
                # Search in operation name
                if query_lower in entry.operation_name.lower():
                    filtered.append(entry)
                    continue

                # Search in parameters
                params_str = json.dumps(entry.parameters).lower()
                if query_lower in params_str:
                    filtered.append(entry)
                    continue

                # Search in response
                if entry.response:
                    response_str = json.dumps(entry.response).lower()
                    if query_lower in response_str:
                        filtered.append(entry)
                        continue

            entries = filtered

        return entries

    def clear(self) -> None:
        """Clear all log entries."""
        self.entries.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about logged operations.

        Returns:
            Dictionary with statistics
        """
        total = len(self.entries)
        success = sum(1 for e in self.entries if e.response is not None and not e.error)
        errors = sum(1 for e in self.entries if e.error is not None)

        by_server: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for entry in self.entries:
            by_server[entry.server_name] = by_server.get(entry.server_name, 0) + 1
            by_type[entry.entry_type.value] = by_type.get(entry.entry_type.value, 0) + 1

        # Calculate connected clients
        connected_clients = self._get_connected_clients_count()

        return {
            "total": total,
            "success": success,
            "errors": errors,
            "by_server": by_server,
            "by_type": by_type,
            "connected_clients": connected_clients,
        }

    def _get_connected_clients_count(self) -> int:
        """Get the count of currently connected clients based on log entries.

        Returns:
            Number of currently connected clients
        """
        # Track client IDs by analyzing connection/disconnection events
        connected = set()

        for entry in self.entries:
            if entry.entry_type == LogEntryType.CLIENT_CONNECTED:
                client_id = entry.parameters.get("client_id")
                if client_id:
                    connected.add(client_id)
            elif entry.entry_type == LogEntryType.CLIENT_DISCONNECTED:
                client_id = entry.parameters.get("client_id")
                if client_id:
                    connected.discard(client_id)

        return len(connected)

