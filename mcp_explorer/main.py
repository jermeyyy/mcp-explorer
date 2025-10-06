"""Main entry point for MCP Explorer."""

import sys

from .ui import MCPExplorerApp


def main() -> int:
    """Run the MCP Explorer application."""
    app = MCPExplorerApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
