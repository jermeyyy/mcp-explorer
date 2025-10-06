# Task Completion Checklist

When completing a coding task in this project, follow these steps:

## 1. Code Quality Checks

### Type Checking
```bash
mypy mcp_explorer
```
- Must pass with no errors (strict mode enabled)
- Fix any type errors before proceeding

### Linting
```bash
ruff check mcp_explorer
```
- Must pass with no errors
- Use `ruff check --fix mcp_explorer` for auto-fixable issues
- Line length: max 100 characters
- Import order must be correct (standard, third-party, local)

### Formatting
```bash
ruff format mcp_explorer
```
- Auto-format code to ensure consistency

## 2. Testing

### Run Tests
```bash
pytest
```
- All tests must pass
- Add new tests for new functionality

### Manual Testing
```bash
uv run mcp-explorer
```
- Test the application manually if UI changes were made
- Verify changes work as expected

## 3. Documentation

### Docstrings
- Add/update docstrings for new/modified classes and methods
- Use Google-style docstrings

### Type Hints
- Ensure all functions have proper type hints
- Use `Optional[type]` for optional parameters

## 4. Git Workflow

### Before Committing
1. Run all quality checks (mypy, ruff, pytest)
2. Ensure all tests pass
3. Review changes with `git diff`

### Commit
```bash
git add .
git commit -m "descriptive message"
```

## Quick Validation Script
Run these commands in sequence:
```bash
mypy mcp_explorer && \
ruff check mcp_explorer && \
pytest && \
echo "✅ All checks passed!"
```

## Common Issues

### Type Errors
- Check Optional vs required fields
- Verify return types match function signatures
- Use `from typing import` for complex types

### Linting Errors
- Line too long: break into multiple lines
- Import order: ruff can auto-fix with `--fix`
- Unused imports: remove them

### Test Failures
- Check async/await usage
- Verify mocks are set up correctly
- Ensure test data is valid
