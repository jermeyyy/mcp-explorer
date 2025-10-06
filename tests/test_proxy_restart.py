"""Test proxy server restart functionality."""

import asyncio
from mcp_explorer.models import ProxyConfig, MCPServer
from mcp_explorer.proxy import ProxyServer, ProxyLogger


async def test_restart():
    """Test that proxy can be stopped and restarted multiple times."""
    # Create minimal config
    config = ProxyConfig(enabled=True, port=3001)
    logger = ProxyLogger()

    # Create a simple test server
    server = MCPServer(name="test-server", command="echo", args=["test"])

    print("Test 1: Start proxy server...")
    proxy = ProxyServer(servers=[server], config=config, logger=logger)

    # Start in background
    start_task = asyncio.create_task(proxy.start())
    await asyncio.sleep(1)  # Give it time to start

    print(f"  Proxy running: {proxy.is_running()}")
    assert proxy.is_running(), "Proxy should be running"

    print("Test 2: Stop proxy server...")
    await proxy.stop()

    print(f"  Proxy running: {proxy.is_running()}")
    assert not proxy.is_running(), "Proxy should be stopped"

    # Cancel the start task
    if not start_task.done():
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    print("  Waiting for port to be released...")
    await asyncio.sleep(1.0)  # Give OS more time to release the port

    print("Test 3: Create and start new proxy on same port...")
    proxy2 = ProxyServer(servers=[server], config=config, logger=logger)
    start_task2 = asyncio.create_task(proxy2.start())
    await asyncio.sleep(1)  # Give it time to start

    print(f"  Proxy running: {proxy2.is_running()}")
    assert proxy2.is_running(), "Second proxy should be running"

    print("Test 4: Stop second proxy...")
    await proxy2.stop()
    await asyncio.sleep(0.5)

    print(f"  Proxy running: {proxy2.is_running()}")
    assert not proxy2.is_running(), "Second proxy should be stopped"

    # Cleanup
    if not start_task2.done():
        start_task2.cancel()
        try:
            await start_task2
        except asyncio.CancelledError:
            pass

    print("\n✅ All tests passed! Proxy can be restarted multiple times.")


if __name__ == "__main__":
    asyncio.run(test_restart())

