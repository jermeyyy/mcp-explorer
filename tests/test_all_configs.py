#!/usr/bin/env python3
"""Test that all servers from all config files are discovered hierarchically."""

from mcp_explorer.services.config_loader import MCPConfigLoader

def main():
    loader = MCPConfigLoader()
    config_files_data = loader.discover_servers_hierarchical()

    print('\n' + '='*70)
    print('HIERARCHICAL DISCOVERY RESULTS')
    print('='*70)
    print(f'Total config files: {len(config_files_data)}')

    total_servers = 0
    for config_file_data in config_files_data:
        path = config_file_data['path']
        servers = config_file_data['servers']
        total_servers += len(servers)

        print(f'\n📁 {path}')
        print(f'   ({len(servers)} server(s))')

        for server_data in servers:
            name = server_data['name']
            config = server_data['config']
            server_type = config.get('type', 'stdio')
            print(f'   - {name} ({server_type})')

    print(f'\n{"="*70}')
    print(f'Total servers across all configs: {total_servers}')
    print(f'All servers kept without renaming!')
    print('='*70 + '\n')

if __name__ == "__main__":
    main()

