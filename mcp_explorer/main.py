"""Main entry point for MCP Explorer."""

import argparse
import sys

from .ui import MCPExplorerApp


def main() -> int:
    """Run the MCP Explorer application."""
    parser = argparse.ArgumentParser(
        description="MCP Explorer - Model Context Protocol Browser & Proxy"
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Start the application with proxy server running",
    )
    args = parser.parse_args()

    app = MCPExplorerApp(start_proxy=args.proxy)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
