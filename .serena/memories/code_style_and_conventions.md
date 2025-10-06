# Code Style and Conventions

## Type Hints
- **Strict typing**: All functions and methods use type hints
- **mypy strict mode**: Enabled in pyproject.toml
- **py.typed marker**: Present for PEP 561 compliance
- **Type imports**: Use `from typing import` for type annotations

## Docstrings
- **Module docstrings**: Every module starts with a docstring describing its purpose
- **Class docstrings**: All classes have docstrings explaining their purpose
- **Method docstrings**: Public methods have docstrings
- **Format**: Google-style docstrings

## Naming Conventions
- **Classes**: PascalCase (e.g., `MCPServer`, `ServerType`)
- **Functions/Methods**: snake_case (e.g., `discover_all_servers`, `_init_server`)
- **Constants**: UPPER_CASE (e.g., `STDIO`, `SSE`)
- **Private methods**: Prefix with underscore (e.g., `_init_server`)
- **Type aliases**: PascalCase

## Imports
- **Order**: Standard library, third-party, local imports (enforced by ruff)
- **Relative imports**: Use relative imports within package (e.g., `from ..models import MCPServer`)
- **Absolute imports**: Use for external packages

## Code Organization
- **Line length**: Maximum 100 characters (ruff configuration)
- **Enums**: Use `str, Enum` for string enumerations
- **Pydantic models**: Use `BaseModel` for domain entities
- **Default values**: Use `Field(default_factory=list/dict)` for mutable defaults
- **Optional fields**: Use `Optional[type]` and provide None as default

## Error Handling
- **Async exceptions**: Use `asyncio.gather(..., return_exceptions=True)` for parallel operations
- **Validation**: Pydantic models handle validation automatically
- **Error propagation**: Servers marked with error status rather than raising exceptions

## Async Code
- **Async functions**: Use `async def` for I/O operations
- **Parallel execution**: Use `asyncio.gather()` for concurrent tasks
- **Type hints**: Return types like `List[MCPServer]` for async functions
