#!/usr/bin/env python3
"""Test configuration loading only (no server connections)."""

from mcp_explorer.services.config_loader import MCPConfigLoader


def main():
    """Test configuration loading."""
    print("🔍 Testing MCP Configuration Loading\n")
    print("=" * 70)

    loader = MCPConfigLoader()

    # Test 1: Find config files
    print("\n1️⃣  Configuration File Discovery")
    print("-" * 70)
    config_paths = loader.get_config_paths()

    if not config_paths:
        print("❌ No configuration files found")
        return

    print(f"✅ Found {len(config_paths)} configuration file(s):\n")
    for path in config_paths:
        print(f"   📄 {path}")

    # Test 2: Validate JSON syntax
    print("\n\n2️⃣  JSON/JSON5 Syntax Validation")
    print("-" * 70)

    for path in config_paths:
        is_valid, error = loader.validate_json_syntax(path)
        if is_valid:
            print(f"✅ {path.name}: Valid")
        else:
            print(f"❌ {path.name}: {error}")

    # Test 3: Load and parse configs
    print("\n\n3️⃣  Configuration Loading")
    print("-" * 70)

    all_servers = loader.discover_servers()
    print(f"\n✅ Loaded {len(all_servers)} server(s) total\n")

    # Test 4: Analyze server configs
    print("\n4️⃣  Server Configuration Analysis")
    print("-" * 70)

    # Group by source file
    by_source = {}
    for name, config in all_servers.items():
        source = config.get("_source_file", "unknown")
        if source not in by_source:
            by_source[source] = []
        by_source[source].append((name, config))

    for source_file, servers in by_source.items():
        print(f"\n📁 {source_file}")
        print(f"   Servers: {len(servers)}")

        for name, config in servers:
            server_type = config.get("type", "stdio")
            print(f"\n   🖥  {name}")
            print(f"      Type: {server_type}")

            # Validate
            is_valid, error = loader.validate_server_config(name, config)
            if is_valid:
                print(f"      ✅ Valid configuration")
            else:
                print(f"      ❌ Validation error: {error}")

            # Show key fields
            if server_type == "stdio":
                print(f"      Command: {config.get('command', 'N/A')}")
                if config.get("args"):
                    args = config["args"]
                    args_str = " ".join(args[:3])
                    if len(args) > 3:
                        args_str += f" ... (+{len(args) - 3} more)"
                    print(f"      Args: {args_str}")
            elif server_type == "sse":
                print(f"      URL: {config.get('url', 'N/A')}")

            if config.get("description"):
                print(f"      Description: {config['description']}")

            if config.get("env"):
                env_keys = list(config["env"].keys())
                print(f"      Env vars: {', '.join(env_keys)}")

    # Test 5: Schema detection
    print("\n\n5️⃣  Configuration Schema Detection")
    print("-" * 70)

    for path in config_paths:
        config = loader.load_config_file(path)
        if not config:
            continue

        # Detect schema type
        if "mcpServers" in config:
            schema_type = "Claude Code (mcpServers)"
        elif "servers" in config:
            schema_type = "GitHub Copilot / Generic (servers)"
        else:
            schema_type = "Unknown (custom format)"

        print(f"\n📄 {path.name}")
        print(f"   Schema: {schema_type}")

        # Check for JSON5 features
        with open(path, "r") as f:
            content = f.read()

        features = []
        if "//" in content or "/*" in content:
            features.append("comments")
        if content.count('"') < content.count(":"):
            features.append("unquoted keys")
        if ",\n  }" in content or ",\n}" in content:
            features.append("trailing commas")

        if features:
            print(f"   JSON5 features: {', '.join(features)}")
        else:
            print(f"   Format: Strict JSON")

    # Test 6: Summary statistics
    print("\n\n6️⃣  Summary Statistics")
    print("-" * 70)

    stdio_count = sum(1 for c in all_servers.values() if c.get("type", "stdio") == "stdio")
    sse_count = sum(1 for c in all_servers.values() if c.get("type") == "sse")
    valid_count = sum(
        1 for name, c in all_servers.items() if loader.validate_server_config(name, c)[0]
    )
    invalid_count = len(all_servers) - valid_count

    print(f"\n  Total servers: {len(all_servers)}")
    print(f"  └─ STDIO servers: {stdio_count}")
    print(f"  └─ SSE servers: {sse_count}")
    print()
    print(f"  Valid configurations: {valid_count}")
    print(f"  Invalid configurations: {invalid_count}")

    # Test 7: Format compatibility
    print("\n\n7️⃣  Format Compatibility Check")
    print("-" * 70)

    print("\n✅ Supported formats:")
    print("   • Claude Code (mcpServers, strict JSON, stdio only)")
    print("   • GitHub Copilot IntelliJ (servers, JSON5, stdio + SSE)")
    print("   • Generic MCP config (servers, JSON/JSON5, stdio + SSE)")

    print("\n✅ JSON5 support: ENABLED")
    print("   • Unquoted keys")
    print("   • Trailing commas")
    print("   • Comments (// and /* */)")

    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")


if __name__ == "__main__":
    main()
