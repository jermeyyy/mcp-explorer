"""Configuration loader for MCP servers."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pyjson5

    JSON5_AVAILABLE = True
except ImportError:
    JSON5_AVAILABLE = False


class ConfigValidationError(Exception):
    """Raised when config validation fails."""

    pass


class MCPConfigLoader:
    """Loads MCP server configurations from various sources."""

    @staticmethod
    def get_config_paths() -> List[Path]:
        """Get potential MCP configuration file paths."""
        paths = []

        # Claude Code configuration
        home = Path.home()
        claude_config = (
            home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        )
        if claude_config.exists():
            paths.append(claude_config)

        # Alternative config locations
        alt_paths = [
            home / ".config" / "github-copilot" / "intellij" / "mcp.json",
            home / ".config" / "mcp" / "config.json",
            home / ".mcp" / "config.json",
            Path.cwd() / "mcp.json",
            Path.cwd() / ".mcp.json",
        ]

        for path in alt_paths:
            if path.exists():
                paths.append(path)

        return paths

    @staticmethod
    def validate_json_syntax(config_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate JSON/JSON5 syntax of a config file.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(config_path, "r") as f:
                content = f.read()

            # Try strict JSON first
            try:
                json.loads(content)
                return True, None
            except json.JSONDecodeError as json_err:
                # If strict JSON fails, try JSON5
                if JSON5_AVAILABLE:
                    try:
                        pyjson5.loads(content)
                        return True, None
                    except Exception as json5_err:
                        # Both failed, report JSON5 error if available, else JSON error
                        return False, f"Invalid JSON/JSON5: {str(json5_err)}"
                else:
                    # No JSON5 support, report JSON error
                    return (
                        False,
                        f"Invalid JSON at line {json_err.lineno}, column {json_err.colno}: {json_err.msg}",
                    )

        except IOError as e:
            return False, f"Cannot read file: {e}"

    @staticmethod
    def load_config_file(config_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from a JSON/JSON5 file with validation."""
        # First validate JSON syntax
        is_valid, error_msg = MCPConfigLoader.validate_json_syntax(config_path)
        if not is_valid:
            print(f"⚠ Config validation failed for {config_path}:")
            print(f"  {error_msg}")
            return None

        try:
            with open(config_path, "r") as f:
                content = f.read()

            # Try strict JSON first
            try:
                config = json.loads(content)
            except json.JSONDecodeError:
                # Fall back to JSON5 if available
                if JSON5_AVAILABLE:
                    config = pyjson5.loads(content)
                else:
                    raise

            # Validate basic structure
            if not isinstance(config, dict):
                print(f"⚠ Config must be a JSON object: {config_path}")
                return None

            return config

        except Exception as e:
            print(f"⚠ Error loading config from {config_path}: {e}")
            return None

    @staticmethod
    def validate_server_config(name: str, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a server configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check server type
        server_type = config.get("type", "stdio")
        if server_type not in ["stdio", "sse"]:
            return False, f"Invalid server type: {server_type}"

        if server_type == "stdio":
            # Validate stdio server
            if "command" not in config:
                return False, "stdio server must have 'command' field"

            if not isinstance(config.get("args", []), list):
                return False, "'args' must be a list"

            if "env" in config and not isinstance(config["env"], dict):
                return False, "'env' must be an object"

        elif server_type == "sse":
            # Validate sse server
            if "url" not in config:
                return False, "sse server must have 'url' field"

        return True, None

    @classmethod
    def discover_servers(cls) -> Dict[str, Dict[str, Any]]:
        """Discover all configured MCP servers with validation."""
        all_servers: Dict[str, Dict[str, Any]] = {}

        for config_path in cls.get_config_paths():
            config = cls.load_config_file(config_path)
            if not config:
                continue

            # Handle different config formats
            if "mcpServers" in config:
                servers = config["mcpServers"]
            elif "servers" in config:
                servers = config["servers"]
            else:
                servers = config

            if not isinstance(servers, dict):
                print(f"⚠ Invalid servers format in {config_path}")
                continue

            # Validate and merge servers
            for name, server_config in servers.items():
                if not isinstance(server_config, dict):
                    print(f"⚠ Invalid config for server '{name}' in {config_path}")
                    continue

                # Validate server config
                is_valid, error_msg = cls.validate_server_config(name, server_config)
                if not is_valid:
                    print(f"⚠ Invalid config for server '{name}': {error_msg}")
                    # Still add it but mark the error
                    server_config["_validation_error"] = error_msg

                # Add source file for debugging
                server_config["_source_file"] = str(config_path)

                # Merge (later configs override earlier ones)
                all_servers[name] = server_config

        return all_servers

    @classmethod
    def get_server_config(cls, server_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific server."""
        servers = cls.discover_servers()
        return servers.get(server_name)
