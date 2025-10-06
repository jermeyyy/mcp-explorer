"""Models for proxy configuration."""

import tomllib
from pathlib import Path
from typing import Any, Dict, List, Set

import tomli_w
from pydantic import BaseModel, Field


class ProxyConfig(BaseModel):
    """Configuration for the MCP proxy server."""

    enabled: bool = False
    port: int = 3000

    # Server filtering
    enabled_servers: Set[str] = Field(default_factory=set)  # Server names to expose

    # Tool filtering per server
    enabled_tools: Dict[str, Set[str]] = Field(default_factory=dict)  # server -> tool names

    # Resource filtering per server
    enabled_resources: Dict[str, Set[str]] = Field(default_factory=dict)  # server -> resource URIs

    # Prompt filtering per server
    enabled_prompts: Dict[str, Set[str]] = Field(default_factory=dict)  # server -> prompt names

    # Logging
    enable_logging: bool = True
    max_log_entries: int = 1000

    def is_server_enabled(self, server_name: str) -> bool:
        """Check if a server is enabled."""
        return server_name in self.enabled_servers if self.enabled_servers else True

    def is_tool_enabled(self, server_name: str, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        if server_name not in self.enabled_tools:
            return True  # All tools enabled by default
        return tool_name in self.enabled_tools[server_name]

    def is_resource_enabled(self, server_name: str, resource_uri: str) -> bool:
        """Check if a resource is enabled."""
        if server_name not in self.enabled_resources:
            return True
        return resource_uri in self.enabled_resources[server_name]

    def is_prompt_enabled(self, server_name: str, prompt_name: str) -> bool:
        """Check if a prompt is enabled."""
        if server_name not in self.enabled_prompts:
            return True
        return prompt_name in self.enabled_prompts[server_name]

    def enable_all_for_server(self, server_name: str) -> None:
        """Enable all tools/resources/prompts for a server."""
        self.enabled_servers.add(server_name)
        if server_name in self.enabled_tools:
            del self.enabled_tools[server_name]
        if server_name in self.enabled_resources:
            del self.enabled_resources[server_name]
        if server_name in self.enabled_prompts:
            del self.enabled_prompts[server_name]

    def disable_server(self, server_name: str) -> None:
        """Disable a server completely."""
        self.enabled_servers.discard(server_name)

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

            return cls(**data)
        except Exception as e:
            print(f"Error loading proxy config: {e}")
            return cls()

    def save(self) -> None:
        """Save configuration to TOML file."""
        config_path = self.get_config_path()

        # Convert sets to lists for TOML serialization
        data: Dict[str, Any] = {
            "enabled": self.enabled,
            "port": self.port,
            "enabled_servers": list(self.enabled_servers),
            "enabled_tools": {k: list(v) for k, v in self.enabled_tools.items()},
            "enabled_resources": {k: list(v) for k, v in self.enabled_resources.items()},
            "enabled_prompts": {k: list(v) for k, v in self.enabled_prompts.items()},
            "enable_logging": self.enable_logging,
            "max_log_entries": self.max_log_entries,
        }

        try:
            with open(config_path, "wb") as f:
                tomli_w.dump(data, f)
        except Exception as e:
            print(f"Error saving proxy config: {e}")
