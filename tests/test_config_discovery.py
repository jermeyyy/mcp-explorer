#!/usr/bin/env python3
"""Debug script to test config discovery."""

from mcp_explorer.services.config_loader import MCPConfigLoader

def main():
    loader = MCPConfigLoader()

    # Get all config paths
    paths = loader.get_config_paths()
    print(f"\n{'='*70}")
    print(f"STEP 1: Config paths found: {len(paths)}")
    print(f"{'='*70}")
    for i, path in enumerate(paths, 1):
        print(f"  {i}. {path}")

    # Discover all servers
    print(f"\n{'='*70}")
    print(f"STEP 2: Processing each config file")
    print(f"{'='*70}")

    all_servers = loader.discover_servers()

    print(f"\n{'='*70}")
    print(f"STEP 3: Final results - Total servers: {len(all_servers)}")
    print(f"{'='*70}")

    # Group by source file
    from collections import defaultdict
    by_source = defaultdict(list)
    for name, config in all_servers.items():
        source = config.get('_source_file', 'Unknown')
        by_source[source].append(name)

    for source, server_names in sorted(by_source.items()):
        print(f"\n  📁 {source}")
        for name in server_names:
            print(f"      - {name}")

    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()

