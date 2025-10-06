# Claude Instructions for MCP Explorer

## Using Serena MCP for This Project

This project is configured with the Serena MCP server, which provides intelligent code navigation and editing tools. **Always use Serena's symbolic tools instead of reading entire files.**

### 1. Start with Memories

Before working on any task, check the available memories:

```
mcp__serena__list_memories
```

Read relevant memories to understand the project context:
- `project_overview` - Architecture, tech stack, directory structure
- `code_style_and_conventions` - Coding standards and patterns
- `configuration_and_features` - Configuration details
- `suggested_commands` - Common development commands
- `task_completion_checklist` - Quality assurance steps

### 2. Navigate Code Symbolically

**DO NOT read entire files unless absolutely necessary.** Use symbolic tools instead:

#### Get File Overview
```
mcp__serena__jet_brains_get_symbols_overview
relative_path: "mcp_explorer/services/discovery.py"
```

#### Find Specific Symbols
```
mcp__serena__jet_brains_find_symbol
name_path: "DiscoveryService/discover_all_servers"
relative_path: "mcp_explorer/services/discovery.py"
include_body: true
depth: 0
```

#### Find References
```
mcp__serena__jet_brains_find_referencing_symbols
name_path: "MCPServer"
relative_path: "mcp_explorer/models/server.py"
```

### 3. Search for Patterns

Use pattern search for flexible code discovery:

```
mcp__serena__search_for_pattern
substring_pattern: "async def.*discover"
relative_path: "mcp_explorer/services"
restrict_search_to_code_files: true
```

### 4. Edit Code Symbolically

#### Replace Symbol Bodies
```
mcp__serena__replace_symbol_body
name_path: "DiscoveryService/discover_all_servers"
relative_path: "mcp_explorer/services/discovery.py"
body: "<new implementation>"
```

#### Insert New Code
```
mcp__serena__insert_after_symbol
name_path: "DiscoveryService"
relative_path: "mcp_explorer/services/discovery.py"
body: "\n    async def new_method(self) -> None:\n        pass\n"
```

#### Add Imports
```
mcp__serena__insert_before_symbol
name_path: "<first_top_level_symbol>"
relative_path: "mcp_explorer/services/discovery.py"
body: "from typing import Optional\n"
```

### 5. Explore Project Structure

Use `list_dir` and `find_file` for navigation:

```
mcp__serena__list_dir
relative_path: "."
recursive: false
```

```
mcp__serena__find_file
file_mask: "*config*.py"
relative_path: "mcp_explorer"
```

### 6. Best Practices

1. **Read minimally**: Only read symbol bodies you need to modify
2. **Use depth parameter**: Get child symbols (methods of a class) with `depth=1`
3. **Leverage memories**: Don't re-explore architecture already documented
4. **Think before editing**: Use `mcp__serena__think_about_collected_information` and `mcp__serena__think_about_task_adherence`
5. **Check references**: Before changing a symbol, find its references to ensure backward compatibility

### 7. Workflow Example

When asked to add a new feature:

1. Read relevant memories to understand context
2. Use `get_symbols_overview` on affected files
3. Use `find_symbol` with `include_body=false` to understand structure
4. Use `find_symbol` with `include_body=true` only for symbols you'll modify
5. Use `find_referencing_symbols` to understand dependencies
6. Use symbolic editing tools to make changes
7. Think about whether you're done with `mcp__serena__think_about_whether_you_are_done`

### 8. Common Pitfalls to Avoid

- L Reading entire files with Read tool
- L Using grep/find bash commands instead of serena tools
- L Re-reading code already seen with symbolic tools
- L Ignoring project memories
-  Using symbolic overview ’ targeted symbol reads ’ edit workflow
-  Leveraging memories for architectural context
-  Using pattern search for unknown symbol locations

## Project-Specific Notes

- **Async code**: Most service methods are async, use `async def`
- **Type hints**: Always include comprehensive type hints
- **Pydantic models**: Domain entities use Pydantic BaseModel
- **Error handling**: Use `return_exceptions=True` with `asyncio.gather`
- **Testing**: Run `uv run pytest` before marking tasks complete
- **Formatting**: Run `uv run ruff format` on modified files