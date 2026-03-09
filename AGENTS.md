# AGENTS.md - Developer Guide for Robotoff

This file contains guidelines and instructions for agentic coding agents working in this repository.

## Project Overview

Robotoff is a real-time and batch prediction service for Open Food Facts. It's a Python project (Python 3.11+) using Falcon for APIs, Peewee for database, and various ML libraries.

## Build, Lint, and Test Commands

### Running Tests

```bash
# Run all tests (unit + integration)
make tests

# Run only unit tests
make unit-tests

# Run only integration tests
make integration-tests

# Run ML tests (requires Triton server)
make ml-tests

# Run a specific test file or function (most common)
make pytest args='tests/unit/path/to/test_file.py::test_function_name'

# Run a specific test file
make pytest args='tests/unit/path/to/test_file.py'

# Run with pytest options (e.g., --pdb for debugging)
make pytest args='tests/unit/path/to/test_file.py::test_function_name --pdb'
```

### Linting and Code Quality

```bash
# Run all checks (toml, flake8, black, mypy, isort, docs)
make checks

# Run individual linters
make flake8        # flake8 linting
make black         # auto-format code
make black-check   # check black formatting
make mypy          # type checking
make isort         # sort imports
make isort-check   # check import sorting

# Format code (isort + black)
make lint
```

### Other Useful Commands

```bash
make dev              # Setup development environment
make up               # Start containers
make down             # Stop containers
make tests args='...' # Run specific pytest args
```

## Code Style Guidelines

### Formatting

- **Line length**: 88 characters (matches Black default)
- **Formatter**: Black (v25.1.0)
- **Import sorting**: isort (v6.0.1) with:
  - `multi_line_output = 3` (hanging indent)
  - `include_trailing_comma = true`
  - `use_parentheses = true`
  - `line_length = 88`

Run `make lint` to auto-format code.

### Linting

- **Linter**: flake8 (v7.2.0)
- **Max line length**: 88
- **Ignored rules**: E203 (whitespace before ':'), E501 (line too long), W503 (line break before binary operator)
- **Max doc length**: 88

### Type Checking

- **Type checker**: mypy (v1.10.1)
- Config: `ignore_missing_imports = true` in pyproject.toml
- This project uses Python type hints extensively, especially with Pydantic models

### Import Conventions

```python
# Standard library first
import dataclasses
import datetime
import enum
from collections import Counter
from typing import Any, Literal, Self

# Third-party libraries
from pydantic import BaseModel, ConfigDict, model_validator
import requests

# Local application imports
from robotoff import settings
from robotoff.types import JSONType
from robotoff.utils import some_function
```

### Naming Conventions

- **Classes**: PascalCase (e.g., `ObjectDetectionModel`, `InsightType`)
- **Functions/variables**: snake_case (e.g., `get_image_from_url`, `jsonl_iter`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`)
- **Enums**: Use `@enum.unique` decorator for enum classes
- **Types**: Use type hints for all function arguments and return values

### Pydantic Models

```python
from pydantic import BaseModel, ConfigDict, model_validator

class MyModel(BaseModel):
    model_config = ConfigDict(...)

    name: str
    value: int

    @model_validator(mode='before')
    @classmethod
    def validate_values(cls, data: Any) -> Any:
        # validation logic
        return data
```

### Error Handling

- Use custom exceptions with clear names
- Use `from robotoff.exceptions import ...` pattern for custom errors
- Use `orjson` for JSON operations (faster than standard json)
- Use `backoff` for retry logic with exponential backoff

### Database Models

- Uses Peewee ORM (`peewee~=3.17.6`)
- Models defined in `robotoff/models.py`
- Migrations managed via `peewee-migrate`

### Testing Conventions

- Tests in `tests/unit/`, `tests/integration/`, `tests/ml/`
- Use `pytest` with `pytest-mock` and `pytest-httpserver`
- Use `requests-mock` for HTTP mocking
- Test files: `test_*.py` or `*_test.py`

### Pre-commit Hooks

The project uses pre-commit with:
- Black (formatting)
- Flake8 (linting)
- isort (import sorting)

Install hooks with: `pre-commit install`

### API Framework

- Uses Falcon (`falcon~=3.1.3`) for REST APIs
- Follows Falcon resource/responder patterns

### Documentation

- API docs: Spectral OpenAPI linting in `docs/references/api.yml`
- Docs built with MkDocs Material

## Important Files

- `pyproject.toml`: Project configuration and dependencies
- `Makefile`: Development commands
- `.flake8`: Flake8 configuration
- `.pre-commit-config.yaml`: Pre-commit hooks
- `robotoff/settings.py`: Application settings

## Development Notes

- This project requires Python 3.11+
- Uses `uv` for dependency management in Docker
- Docker-based development environment (see docker-compose.yml)
- Integrates with PostgreSQL, Elasticsearch, Redis, and Triton (ML inference)
