#!/usr/bin/env python3
"""Test that all config files are being discovered and processed."""

import sys
from pathlib import Path
from mcp_explorer.services.config_loader import MCPConfigLoader


def main():
    loader = MCPConfigLoader()

    # Step 1: Get all config paths
    paths = loader.get_config_paths()
    print(f"\n{'=' * 70}", file=sys.stderr)
    print(f"Config paths discovered: {len(paths)}", file=sys.stderr)
    print(f"{'=' * 70}", file=sys.stderr)
    for i, path in enumerate(paths, 1):
        print(f"{i}. {path}", file=sys.stderr)
        # Check if file is readable
        try:
            with open(path, "r") as f:
                content = f.read(100)
                print(f"   ✓ File is readable ({len(content)} chars preview)", file=sys.stderr)
        except Exception as e:
            print(f"   ✗ Error reading: {e}", file=sys.stderr)

    # Step 2: Discover servers (this will show detailed logging)
    print(f"\n{'=' * 70}", file=sys.stderr)
    print(f"Starting server discovery...", file=sys.stderr)
    print(f"{'=' * 70}\n", file=sys.stderr)

    all_servers = loader.discover_servers()

    # Step 3: Show results grouped by source
    print(f"\n{'=' * 70}", file=sys.stderr)
    print(f"FINAL RESULTS", file=sys.stderr)
    print(f"{'=' * 70}", file=sys.stderr)

    from collections import defaultdict

    by_source = defaultdict(list)
    for name, config in all_servers.items():
        source = config.get("_source_file", "Unknown")
        by_source[source].append(name)

    print(f"\nServers grouped by config file:", file=sys.stderr)
    for source in sorted(by_source.keys()):
        server_names = by_source[source]
        print(f"\n📁 {source}", file=sys.stderr)
        print(
            f"   ({len(server_names)} server{'s' if len(server_names) != 1 else ''})",
            file=sys.stderr,
        )
        for name in sorted(server_names):
            server_type = all_servers[name].get("type", "stdio")
            print(f"   - {name} ({server_type})", file=sys.stderr)

    print(f"\n{'=' * 70}", file=sys.stderr)
    print(f"Total unique servers: {len(all_servers)}", file=sys.stderr)
    print(f"Total config files: {len(by_source)}", file=sys.stderr)
    print(f"{'=' * 70}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
