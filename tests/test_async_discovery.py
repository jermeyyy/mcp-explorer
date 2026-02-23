#!/usr/bin/env python3
"""Test async discovery with detailed error reporting."""

import asyncio
import sys

import pytest


@pytest.mark.asyncio
async def test_discovery():
    """Test server discovery with error handling."""
    print("🧪 Testing async server discovery...\n")
    print("=" * 70)

    try:
        from mcp_explorer.services.discovery import MCPDiscoveryService

        service = MCPDiscoveryService()

        print("\n📋 Step 1: Loading config files...")
        configs = service.config_loader.discover_servers()
        print(f"✅ Found {len(configs)} server configs")

        print("\n📋 Step 2: Discovering servers in parallel...")
        print("Note: This may take a few seconds per server\n")

        servers = await service.discover_all_servers()

        print(f"\n✅ Discovery completed: {len(servers)} servers")

        print("\n📊 Server Status:")
        print("-" * 70)
        for server in servers:
            status_icon = "✅" if server.status.value == "connected" else "❌"
            print(f"{status_icon} {server.name}: {server.status.value}")
            if server.error_message:
                print(f"   Error: {server.error_message}")
            else:
                print(f"   Capabilities: {server.get_capabilities_summary()}")

        # Cleanup
        service.cleanup()

        print("\n" + "=" * 70)
        print("✅ Test completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(test_discovery())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
