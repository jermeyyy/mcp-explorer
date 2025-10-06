#!/usr/bin/env python3
"""Test script to verify MCP server discovery from both Claude and GitHub Copilot configs."""

import asyncio
from pathlib import Path
from mcp_explorer.services.discovery import MCPDiscoveryService


async def test_discovery():
    """Test server discovery."""
    print("🔍 Testing MCP Server Discovery\n")
    print("=" * 70)

    service = MCPDiscoveryService()

    # Show discovered configs
    print("\n📄 Configuration Files Found:")
    print("-" * 70)
    config_paths = service.config_loader.get_config_paths()
    for path in config_paths:
        print(f"  ✓ {path}")

    # Show all servers from configs
    print("\n🔧 Servers in Configurations:")
    print("-" * 70)
    all_configs = service.config_loader.discover_servers()

    for name, config in all_configs.items():
        server_type = config.get("type", "stdio")
        print(f"\n  • {name}")
        print(f"    Type: {server_type}")

        if server_type == "stdio":
            print(f"    Command: {config.get('command', 'N/A')}")
            if config.get('args'):
                print(f"    Args: {' '.join(config['args'][:3])}{'...' if len(config['args']) > 3 else ''}")
        else:
            print(f"    URL: {config.get('url', 'N/A')}")

        if config.get('description'):
            print(f"    Description: {config['description']}")

        if config.get('_source_file'):
            print(f"    Source: {config['_source_file']}")

        if config.get('_validation_error'):
            print(f"    ⚠ Validation Error: {config['_validation_error']}")

    # Discover servers (this will attempt to connect)
    print("\n\n🌐 Attempting to Connect to Servers...")
    print("-" * 70)
    print("Note: This may take a few seconds per server.\n")

    servers = await service.discover_all_servers()

    print(f"\n✅ Discovery Complete: {len(servers)} servers")
    print("=" * 70)

    # Show results
    for server in servers:
        print(f"\n🖥  {server.name}")
        print(f"   Type: {server.server_type.value.upper()}")
        print(f"   Status: {server.get_status_display()}")

        if server.description:
            print(f"   Description: {server.description}")

        if server.server_type.value == "stdio" and server.command:
            print(f"   Command: {server.command}")
        elif server.server_type.value == "sse" and server.url:
            print(f"   URL: {server.url}")

        # Show capabilities
        print(f"   Capabilities: {server.get_capabilities_summary()}")

        if server.tools:
            print(f"   Tools ({len(server.tools)}):")
            for tool in server.tools[:3]:
                print(f"     - {tool.name}")
            if len(server.tools) > 3:
                print(f"     ... and {len(server.tools) - 3} more")

        if server.resources:
            print(f"   Resources ({len(server.resources)}):")
            for resource in server.resources[:3]:
                print(f"     - {resource.name}")
            if len(server.resources) > 3:
                print(f"     ... and {len(server.resources) - 3} more")

        if server.prompts:
            print(f"   Prompts ({len(server.prompts)}):")
            for prompt in server.prompts[:3]:
                print(f"     - {prompt.name}")
            if len(server.prompts) > 3:
                print(f"     ... and {len(server.prompts) - 3} more")

        if server.error_message:
            print(f"   ❌ Error: {server.error_message}")

    # Summary by type
    print("\n\n📊 Summary by Type:")
    print("-" * 70)
    stdio_servers = [s for s in servers if s.server_type.value == "stdio"]
    sse_servers = [s for s in servers if s.server_type.value == "sse"]

    print(f"  STDIO servers: {len(stdio_servers)}")
    for s in stdio_servers:
        print(f"    - {s.name} ({s.status.value})")

    print(f"\n  SSE servers: {len(sse_servers)}")
    for s in sse_servers:
        print(f"    - {s.name} ({s.status.value})")

    # Summary by status
    print("\n📈 Summary by Status:")
    print("-" * 70)
    connected = [s for s in servers if s.status.value == "connected"]
    errored = [s for s in servers if s.status.value == "error"]

    print(f"  ✅ Connected: {len(connected)}")
    print(f"  ❌ Errored: {len(errored)}")
    print(f"  ○ Other: {len(servers) - len(connected) - len(errored)}")

    # Cleanup
    service.cleanup()


if __name__ == "__main__":
    asyncio.run(test_discovery())
