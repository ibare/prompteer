# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**prompteer** is a lightweight file-based prompt manager for LLM workflows. It enables developers to manage LLM prompts as markdown files with YAML frontmatter, accessible via an intuitive dot-notation Python API.

**Key Concepts:**
- Prompts stored as `.md` files with YAML frontmatter for metadata
- Directory structure maps to Python dot notation (e.g., `prompts/chat/system.md` → `prompts.chat.system()`)
- Naming convention: `kebab-case` files/directories → `camelCase` Python API
- Dynamic routing with `[param]` directories (Next.js-style) for runtime prompt selection
- Type stub generation for IDE autocomplete support

## Development Commands

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_core.py

# Run specific test
pytest tests/test_core.py::test_basic_prompt_loading

# Run tests with verbose output
pytest -v

# Generate HTML coverage report (outputs to htmlcov/)
pytest --cov=prompteer --cov-report=html
```

### Code Quality
```bash
# Format code with black
black src/ tests/ examples/

# Check imports with isort
isort src/ tests/ examples/

# Type checking with mypy
mypy src/

# Lint with flake8
flake8 src/ tests/
```

### Building and Distribution

Publishing is automated — see "CI/CD" and "Release Process" below. Do **not**
run `twine upload` manually; the project uses Trusted Publishing and no API
token exists. Local builds are for inspecting artifacts before tagging.

```bash
# Build distribution packages (inspection only)
python -m build

# Check distribution
twine check dist/*

# Install locally in editable mode for development
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Install with watch mode support
pip install -e ".[watch]"
```

### CLI Commands
```bash
# Initialize new prompt directory with examples
prompteer init
prompteer init custom-prompts --force

# Generate type stubs (default command)
prompteer ./prompts -o prompts.pyi

# Generate with watch mode
prompteer generate-types ./prompts --watch

# Get help
prompteer --help
```

### Running Examples
```bash
# Basic usage example
python examples/basic_usage.py

# LLM integration example
python examples/llm_integration.py

# Advanced usage patterns
python examples/advanced_usage.py

# Dynamic routing example
python examples/dynamic_routing.py
```

## Architecture

### Core Components

**`src/prompteer/core.py`** - Main entry point
- `Prompteer` class: Primary interface for prompt management
- `create_prompts()`: Factory function that returns Prompteer instance
- Validates base path exists and is a directory
- Delegates attribute access to internal `PromptProxy`

**`src/prompteer/proxy.py`** - Dynamic attribute resolution
- `PromptProxy` class: Enables dot-notation traversal of prompt directories
- `__getattr__()`: Maps camelCase attributes to kebab-case filesystem paths
- Directories → returns new `PromptProxy` for chaining
- Files (`.md`) → returns callable that renders the prompt
- Dynamic routing: Detects `[param]` directories and creates special callables
- `_create_dynamic_callable()`: Handles runtime parameter-based prompt selection
- `_render_prompt()`: Renders prompt files with variable substitution

**`src/prompteer/template.py`** - Variable substitution engine
- `extract_variables()`: Finds all `{variable}` placeholders in templates
- `render_template()`: Substitutes variables, raises error if required vars missing
- `render_template_with_defaults()`: Uses type-based defaults for missing vars
- `validate_template()`: Checks for malformed `{variable}` syntax

**`src/prompteer/metadata.py`** - YAML frontmatter parsing
- `parse_metadata()`: Extracts YAML frontmatter from markdown files
- `parse_variable_key()`: Parses variable declarations like `name(type): description`
- `VariableInfo`: Stores variable name, type, description, and default value
- `get_type_default()`: Returns default values for types (str="", int=0, etc.)

**`src/prompteer/path_utils.py`** - Naming conversions
- `kebab_to_camel()`: `code-review` → `codeReview`
- `camel_to_kebab()`: `codeReview` → `code-review`
- `is_dynamic_dir()`: Checks if directory name matches `[param]` pattern
- `extract_param_name()`: Extracts parameter name from `[type]` → `type`

**`src/prompteer/type_generator.py`** - Type stub generation
- Scans prompt directory structure
- Generates `.pyi` stub files with full type hints
- Supports `Literal` types for dynamic routing parameters
- Watch mode using `watchdog` library

**`src/prompteer/cli.py`** - Command-line interface
- `cmd_init()`: Scaffolds new prompt directories with examples
- `cmd_generate_types()`: Generates type stubs
- Default command is `generate-types` (can omit subcommand)

### Data Flow

1. **Initialization**: `create_prompts("./prompts")` → `Prompteer()` → validates path → creates root `PromptProxy`
2. **Attribute Access**: `prompts.chat.system` → `PromptProxy.__getattr__("chat")` → checks filesystem → returns new `PromptProxy` or callable
3. **Rendering**: `prompts.chat.system(role="...")` → reads `chat/system.md` → parses frontmatter → extracts variables → substitutes values → returns rendered string
4. **Dynamic Routing**: `prompts.question.user(type="basic")` → detects `[type]` directory → routes to `basic/user.md` or `default.md`

### Path Resolution Pattern

The library supports both relative and absolute paths:
- **Relative paths** (`"./prompts"`) are resolved from current working directory (CWD)
- **For packages/libraries**, always use `Path(__file__).parent / "prompts"` to ensure prompts are found regardless of where the code runs from
- This pattern is critical for library usage and should be documented in examples

### Dynamic Routing System

Dynamic directories use `[param]` syntax (e.g., `[type]/`, `[language]/`):
- Parameter name extracted from brackets: `[type]` → `type` parameter
- Subdirectories represent possible values: `basic/`, `advanced/`
- `default.md` serves as fallback when value doesn't match any directory
- Type stubs use `Literal` types to provide autocomplete for available values
- Example structure:
  ```
  prompts/question/[type]/
  ├── basic/user.md         # type="basic"
  ├── advanced/user.md      # type="advanced"
  └── default.md            # fallback
  ```

### Variable Type System

Supported types in YAML frontmatter:
- `str` (default): Empty string `""`
- `int`: `0`
- `float`: `0.0`
- `bool`: `False`
- `number`: `0` (accepts int or float)
- `any`: `None`

Declaration syntax in frontmatter:
```yaml
---
description: Prompt description
name: User name (defaults to str)
age(int): User age
score(float): Numerical score
active(bool): Is active
---
```

## Testing Strategy

- **Unit tests**: Each module has corresponding test file (e.g., `test_core.py`, `test_template.py`)
- **Integration tests**: `test_dynamic_routing.py` validates end-to-end workflows
- **Coverage target**: Currently ~78%, with focus on core functionality
- Test files use `tmp_path` fixture for filesystem operations
- Mock prompts created in test directories for isolation

## Code Conventions

- **Python version**: 3.7+ (maintain compatibility with older Python versions)
- **Type hints**: Use `from __future__ import annotations` for forward compatibility
- **Docstrings**: Include examples in docstrings using `>>> ` format
- **Error handling**: Use custom exceptions from `exceptions.py` for clear error messages
- **Naming**: `kebab-case` for files/directories, `snake_case` for Python, `camelCase` for API
- **Formatting**: Black with 88 character line length
- **Imports**: isort with black profile

## CI/CD

Two workflows in `.github/workflows/`. Added in v0.4.0.

### `test.yml`

Runs on push to `main`/`develop`, on every PR, and via `workflow_call` from
`release.yml`. Matrix: Python 3.9, 3.10, 3.11, 3.12, 3.13.

Each job runs the test suite, doctests for `template.py` and `blocks.py`, and
executes the example scripts to catch import/runtime breakage.

**Python floor is 3.9.** 3.7 has no verification path (neither uv nor GitHub
runners provide it) and 3.8 reached EOL in 2024-10. Every module uses
`from __future__ import annotations`, so annotations are never evaluated at
runtime — the floor is driven by tooling availability, not syntax.

### `release.yml`

Triggered **only** by pushing a `v*` tag. Nothing else publishes to PyPI.

Pipeline: matrix tests (reuses `test.yml`) → version check → build →
`twine check` → PyPI upload → GitHub release with artifacts attached.

The version check fails the build unless the tag matches **both**
`pyproject.toml` and `src/prompteer/__init__.py`. A mismatched release cannot
go out.

### Trusted Publishing

Uploads use PyPI Trusted Publishing (OIDC). **There is no API token anywhere** —
not in the repo, not in GitHub secrets, not on a developer machine. The
`publish` job requests a short-lived OIDC token via `permissions: id-token:
write` and PyPI verifies it against the registered publisher.

PyPI configuration (project → Manage → Publishing):

| Field | Value |
|-------|-------|
| Owner | `ibare` |
| Repository name | `prompteer` |
| Workflow name | `release.yml` |
| Environment | `pypi` |

All four must match exactly, and `Environment` must equal the `environment:`
value in `release.yml`.

This replaced manual local uploads. The prior process depended on a token whose
location was later unrecoverable, and the release method itself could not be
reconstructed from the repository — there was no CI history and no PyPI
provenance. Do not reintroduce manual uploads.

### Verifying a release

```bash
# Metadata landed (the /pypi/<pkg>/json endpoint is CDN-cached; the
# version-specific endpoint updates first)
curl -s https://pypi.org/pypi/prompteer/0.4.0/json | python -m json.tool

# Trusted Publishing attestation exists — 200 means OIDC-backed,
# 404 means it was uploaded some other way
curl -s -o /dev/null -w "%{http_code}\n" \
  https://pypi.org/integrity/prompteer/0.4.0/prompteer-0.4.0-py3-none-any.whl/provenance
```

Releases before v0.4.0 return 404 — they predate Trusted Publishing.

### When a release fails

The tag is already pushed, so fix and retag:

```bash
git tag -d v0.x.x && git push origin :refs/tags/v0.x.x   # remove tag
# commit the fix, then recreate the tag
```

A failure before the `publish` job leaves PyPI untouched. If `publish` itself
fails (usually a Trusted Publisher mismatch), correct the PyPI settings and
retag — nothing was uploaded. Once a version *is* on PyPI it cannot be replaced;
yank it and ship a patch version instead.

## Branch Strategy

`develop` → PR → `main` → tag. Work lands on `develop`, PRs target `main`, and
releases are tagged on `main` after merge. Keep `develop` fast-forwarded to
`main` after each merge so the next branch starts from the release commit.

## Release Process

Releases are automated. Pushing a `v*` tag is the only action that publishes to
PyPI — see `.github/workflows/release.yml`.

1. Update version in `src/prompteer/__init__.py` and `pyproject.toml` (both must
   match the tag; the workflow fails the build if they disagree)
2. Update `CHANGELOG.md` with new version and changes
3. Run tests locally: `pytest`
4. Merge to `main` (CI runs the full matrix on the PR)
5. Tag on `main` after the merge: `git tag -a v0.x.x -m "Release v0.x.x"`
6. Push the tag: `git push origin v0.x.x`

That last push is what publishes. See "CI/CD" above for the pipeline, the
Trusted Publisher settings, how to verify the result, and what to do when a
release fails.

## Common Development Tasks

### Adding a New Feature

1. Write tests first in appropriate `tests/test_*.py` file
2. Implement feature in corresponding `src/prompteer/*.py` module
3. Update type stubs if API changes
4. Add example usage to `examples/` if user-facing
5. Update README.md and CHANGELOG.md
6. Run full test suite and ensure coverage doesn't drop

### Debugging Prompt Resolution

When troubleshooting why a prompt isn't found:
1. Check the filesystem path: prompts use `kebab-case` files/directories
2. Verify API call uses `camelCase`: `prompts.codeReview.reviewRequest()`
3. Check for `[param]` directories - they change resolution behavior
4. Use `print(prompts._proxy._current_path)` to see current directory
5. Look at `PromptProxy.__getattr__()` logic in `proxy.py:47-85`

### Extending Variable Types

To add a new variable type:
1. Add type to `get_type_default()` in `metadata.py` with appropriate default value
2. Update type mapping in `VariableInfo.__post_init__()` if needed
3. Add to `TypeStubGenerator._get_type_hint()` in `type_generator.py`
4. Add tests in `test_metadata.py` and `test_type_generator.py`
5. Document in README.md under "Variable Types" section
