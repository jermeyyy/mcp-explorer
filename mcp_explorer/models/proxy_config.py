"""Models for proxy configuration."""

import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from pydantic import BaseModel, Field


class ProxyConfig(BaseModel):
    """Configuration for the MCP proxy server."""

    enabled: bool = False
    port: int = 3000

    # Server filtering - using composite key: "config_file_path:server_name"
    enabled_servers: set[str] = Field(default_factory=set)  # Server keys to expose

    # Tool filtering per server - using composite key: "config_file_path:server_name"
    enabled_tools: dict[str, set[str]] = Field(default_factory=dict)  # server_key -> tool names

    # Resource filtering per server - using composite key: "config_file_path:server_name"
    enabled_resources: dict[str, set[str]] = Field(
        default_factory=dict
    )  # server_key -> resource URIs

    # Prompt filtering per server - using composite key: "config_file_path:server_name"
    enabled_prompts: dict[str, set[str]] = Field(default_factory=dict)  # server_key -> prompt names

    # Logging
    enable_logging: bool = True
    max_log_entries: int = 1000

    # Rate limiting
    rate_limit: float | None = None  # Max requests per second, None = no limit

    @staticmethod
    def make_server_key(config_file_path: str, server_name: str) -> str:
        """Create a unique key for a server from a specific config file.

        Args:
            config_file_path: Path to the config file
            server_name: Name of the server

        Returns:
            Composite key in format "config_file_path:server_name"
        """
        return f"{config_file_path}:{server_name}"

    def is_server_enabled(self, config_file_path: str, server_name: str) -> bool:
        """Check if a server is enabled.

        Args:
            config_file_path: Path to the config file
            server_name: Name of the server
        """
        server_key = self.make_server_key(config_file_path, server_name)
        return server_key in self.enabled_servers if self.enabled_servers else True

    def is_tool_enabled(self, config_file_path: str, server_name: str, tool_name: str) -> bool:
        """Check if a tool is enabled.

        Args:
            config_file_path: Path to the config file
            server_name: Name of the server
            tool_name: Name of the tool
        """
        server_key = self.make_server_key(config_file_path, server_name)
        if server_key not in self.enabled_tools:
            return False  # No tools enabled by default for this server
        return tool_name in self.enabled_tools[server_key]

    def is_resource_enabled(
        self, config_file_path: str, server_name: str, resource_uri: str
    ) -> bool:
        """Check if a resource is enabled.

        Args:
            config_file_path: Path to the config file
            server_name: Name of the server
            resource_uri: URI of the resource
        """
        server_key = self.make_server_key(config_file_path, server_name)
        if server_key not in self.enabled_resources:
            return False  # No resources enabled by default
        return resource_uri in self.enabled_resources[server_key]

    def is_prompt_enabled(self, config_file_path: str, server_name: str, prompt_name: str) -> bool:
        """Check if a prompt is enabled.

        Args:
            config_file_path: Path to the config file
            server_name: Name of the server
            prompt_name: Name of the prompt
        """
        server_key = self.make_server_key(config_file_path, server_name)
        if server_key not in self.enabled_prompts:
            return False  # No prompts enabled by default
        return prompt_name in self.enabled_prompts[server_key]

    def enable_all_for_server(self, config_file_path: str, server_name: str) -> None:
        """Enable all tools/resources/prompts for a server.

        Args:
            config_file_path: Path to the config file
            server_name: Name of the server
        """
        server_key = self.make_server_key(config_file_path, server_name)
        self.enabled_servers.add(server_key)
        if server_key in self.enabled_tools:
            del self.enabled_tools[server_key]
        if server_key in self.enabled_resources:
            del self.enabled_resources[server_key]
        if server_key in self.enabled_prompts:
            del self.enabled_prompts[server_key]

    def disable_server(self, config_file_path: str, server_name: str) -> None:
        """Disable a server completely.

        Args:
            config_file_path: Path to the config file
            server_name: Name of the server
        """
        server_key = self.make_server_key(config_file_path, server_name)
        self.enabled_servers.discard(server_key)

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the path to the config file.

        Returns:
            Path to ~/.config/mcp-explorer/proxy-config.toml
        """
        config_dir = Path.home() / ".config" / "mcp-explorer"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "proxy-config.toml"

    @classmethod
    def load(cls) -> "ProxyConfig":
        """Load configuration from TOML file.

        Returns:
            Loaded ProxyConfig, or default if file doesn't exist
        """
        config_path = cls.get_config_path()
        if not config_path.exists():
            return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            # Convert lists to sets
            if "enabled_servers" in data:
                data["enabled_servers"] = set(data["enabled_servers"])

            if "enabled_tools" in data:
                data["enabled_tools"] = {k: set(v) for k, v in data["enabled_tools"].items()}

            if "enabled_resources" in data:
                data["enabled_resources"] = {
                    k: set(v) for k, v in data["enabled_resources"].items()
                }

            if "enabled_prompts" in data:
                data["enabled_prompts"] = {k: set(v) for k, v in data["enabled_prompts"].items()}

            if "rate_limit" in data and data["rate_limit"] is None:
                del data["rate_limit"]

            return cls(**data)
        except Exception as e:
            print(f"Error loading proxy config: {e}")
            return cls()

    def save(self) -> None:
        """Save configuration to TOML file."""
        config_path = self.get_config_path()

        # Convert sets to lists for TOML serialization
        data: dict[str, Any] = {
            "enabled": self.enabled,
            "port": self.port,
            "enabled_servers": list(self.enabled_servers),
            "enabled_tools": {k: list(v) for k, v in self.enabled_tools.items()},
            "enabled_resources": {k: list(v) for k, v in self.enabled_resources.items()},
            "enabled_prompts": {k: list(v) for k, v in self.enabled_prompts.items()},
            "enable_logging": self.enable_logging,
            "max_log_entries": self.max_log_entries,
        }

        if self.rate_limit is not None:
            data["rate_limit"] = self.rate_limit

        try:
            with open(config_path, "wb") as f:
                tomli_w.dump(data, f)
        except Exception as e:
            print(f"Error saving proxy config: {e}")
