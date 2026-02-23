#!/usr/bin/env python3
"""Test that the app can start without errors."""

import sys


def test_imports():
    """Test all imports work."""
    print("Testing imports...")

    try:
        from mcp_explorer.ui import MCPExplorerApp

        print("✅ MCPExplorerApp imported")

        from mcp_explorer.services import MCPDiscoveryService

        print("✅ MCPDiscoveryService imported")

        from mcp_explorer.models import MCPServer, ServerType

        print("✅ Models imported")

        from mcp_explorer.ui.screens import ServerListScreen

        print("✅ Screens imported")

        from mcp_explorer.ui.widgets import ServerListItem

        print("✅ Widgets imported")

        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_app_creation():
    """Test that app can be created."""
    print("\nTesting app creation...")

    try:
        from mcp_explorer.ui import MCPExplorerApp

        app = MCPExplorerApp()
        print("✅ App created successfully")
        print(f"   Title: {app.TITLE}")
        return True
    except Exception as e:
        print(f"❌ App creation error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_screen_creation():
    """Test that screens can be created."""
    print("\nTesting screen creation...")

    try:
        from mcp_explorer.ui.screens import ServerListScreen
        from mcp_explorer.models import MCPServer, ServerType

        # Create a test server
        server = MCPServer(
            name="test-server",
            server_type=ServerType.STDIO,
            command="echo",
            args=["hello"],
        )

        # Create screen with test data
        screen = ServerListScreen([server])
        print("✅ ServerListScreen created with 1 server")

        # Create empty screen
        empty_screen = ServerListScreen([])
        print("✅ Empty ServerListScreen created")

        return True
    except Exception as e:
        print(f"❌ Screen creation error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Testing MCP Explorer startup...\n")
    print("=" * 70)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("App Creation", test_app_creation()))
    results.append(("Screen Creation", test_screen_creation()))

    print("\n" + "=" * 70)
    print("\n📊 Test Results:\n")

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✅ All tests passed! App should start correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check errors above.")
        sys.exit(1)
