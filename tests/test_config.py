#!/usr/bin/env python3
"""Test script to validate MCP configuration discovery."""

from pathlib import Path
from mcp_explorer.services.config_loader import MCPConfigLoader


def main() -> None:
    """Test configuration loading and validation."""
    loader = MCPConfigLoader()

    print("🔍 Searching for MCP configuration files...\n")

    config_paths = loader.get_config_paths()

    if not config_paths:
        print("❌ No configuration files found.")
        print("\nSearched locations:")
        for path in [
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json",
            Path.home() / ".config" / "github-copilot" / "intellij" / "mcp.json",
            Path.home() / ".config" / "mcp" / "config.json",
            Path.home() / ".mcp" / "config.json",
            Path.cwd() / "mcp.json",
            Path.cwd() / ".mcp.json",
        ]:
            print(f"  • {path}")
        return

    print(f"✓ Found {len(config_paths)} configuration file(s):\n")

    for config_path in config_paths:
        print(f"📄 {config_path}")

        # Validate JSON syntax
        is_valid, error_msg = loader.validate_json_syntax(config_path)
        if not is_valid:
            print(f"  ❌ JSON validation failed:")
            print(f"     {error_msg}\n")
            continue

        print(f"  ✓ Valid JSON")

        # Load and validate servers
        config = loader.load_config_file(config_path)
        if not config:
            print(f"  ⚠ Failed to load configuration\n")
            continue

        # Extract servers
        if "mcpServers" in config:
            servers = config["mcpServers"]
        elif "servers" in config:
            servers = config["servers"]
        else:
            servers = config

        if not isinstance(servers, dict):
            print(f"  ⚠ Invalid servers format\n")
            continue

        print(f"  ✓ Found {len(servers)} server(s):\n")

        for name, server_config in servers.items():
            print(f"    • {name}")

            if not isinstance(server_config, dict):
                print(f"      ❌ Invalid configuration")
                continue

            # Validate server config
            is_valid, error_msg = loader.validate_server_config(name, server_config)
            if not is_valid:
                print(f"      ❌ Validation failed: {error_msg}")
            else:
                server_type = server_config.get("type", "stdio")
                print(f"      ✓ Type: {server_type}")

                if server_type == "stdio":
                    command = server_config.get("command", "")
                    print(f"      ✓ Command: {command}")
                elif server_type == "sse":
                    url = server_config.get("url", "")
                    print(f"      ✓ URL: {url}")

                if "description" in server_config:
                    print(f"      ✓ Description: {server_config['description']}")

        print()

    # Discover all servers
    print("\n🌐 Discovering all servers...")
    all_servers = loader.discover_servers()

    print(f"\n✓ Total servers discovered: {len(all_servers)}")
    for name in all_servers.keys():
        print(f"  • {name}")


if __name__ == "__main__":
    main()
