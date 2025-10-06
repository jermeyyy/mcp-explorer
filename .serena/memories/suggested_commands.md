# Suggested Commands

## Installation
```bash
# Install with uv (recommended)
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"

# Or with standard pip
pip install -e .
pip install -e ".[dev]"
```

## Running the Application
```bash
# Run directly (after installation)
mcp-explorer

# Run with uv (without installation)
uv run mcp-explorer
```

## Testing
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_config.py

# Quick tests (standalone test scripts)
uv run python test_config_only.py       # Test config loading only
uv run python test_app_startup.py       # Test app imports and startup
uv run python test_discovery.py         # Test server discovery
uv run python test_async_discovery.py   # Test async discovery
```

## Code Quality
```bash
# Type checking
mypy mcp_explorer

# Linting (check for issues)
ruff check mcp_explorer

# Auto-fix linting issues
ruff check --fix mcp_explorer

# Format check (ruff can also format)
ruff format --check mcp_explorer

# Auto-format
ruff format mcp_explorer
```

## Development Workflow
```bash
# 1. Make changes to code
# 2. Run type checker
mypy mcp_explorer

# 3. Run linter
ruff check mcp_explorer

# 4. Run tests
pytest

# 5. Test the app
uv run mcp-explorer
```

## System Commands (Darwin/macOS)
```bash
# List files
ls -la

# Find files
find . -name "*.py"

# Search in files
grep -r "pattern" mcp_explorer/

# Change directory
cd mcp_explorer/

# Git operations
git status
git add .
git commit -m "message"
git push
```
