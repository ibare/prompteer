# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-06

### Fixed
- **Braces inside injected values were misread as unresolved variables** -
  Rendering is now a single pass, so `{...}` contained in a value is no longer
  interpreted as a variable. Common inputs such as
  `render_template("A: {a}", {"a": "React {children} usage"})` used to fail with
  `TemplateVariableError`. Detection of genuinely missing variables is unchanged.
  - Applies to every rendering path: plain templates, `{#if}`, `{#for}`, and dot notation.
- **Non-deterministic output from `render_template_safe()`** - It applied
  `str.replace` once per variable, so the result depended on substitution order
  (hash seed). Now uses the shared pipeline, removing the order dependency.
- **`render_template_safe()` did not substitute dot notation** - `{user.name}`
  was left as-is even when a value was supplied.
- Missing `Prompteer` import in `examples/advanced_usage.py`.

### Added
- **Brace escaping** - `{{` and `}}` produce literal braces. To write
  `{children}` verbatim in a prompt, escape it as `{{children}}`.
- `blocks.substitute_variables()` - the single substitution implementation (public API)
- `blocks.VARIABLE_PATTERN`, `blocks.BLOCK_KEYWORDS`
- 27 regression tests for braces in injected values (`tests/test_brace_injection.py`)

### Changed
- Rendering was restructured into a single pass. A template is scanned exactly
  once, and output produced by substitution is never reinterpreted as a variable.
- `render_template()`, `render_template_safe()`, and
  `render_template_with_defaults()` now share one rendering core.
- `extract_variables()`, `extract_all_variables()`, and `validate_template()`
  recognize escaped braces.

### Breaking
- **`{{foo}}` changes meaning.** It used to render as `{` + the value of `foo` +
  `}`; it now renders as the literal `{foo}`. Code that used escaping as a
  workaround should drop it at value-injection sites (escaping intended for
  literal braces in the template itself keeps working as written).
- **Partial dot-notation failures now raise.** If `user` exists but has no `name`
  attribute, `{user.name}` raises `TemplateVariableError` instead of silently
  leaving the placeholder.
- **`render_template_safe()` substitutes dot notation.** Where `{user.name}` was
  previously left verbatim, the value is now inserted.
- Internal helpers `template._substitute_variables()` and
  `blocks._substitute_text_variables()` were merged into
  `blocks.substitute_variables()` and removed.
- **Minimum Python is now 3.9** (previously declared as 3.7). 3.7 has no
  verification path (neither uv nor GitHub runners provide it) and 3.8 reached
  EOL in 2024-10. 3.9 through 3.13 are verified by the CI matrix.

### Infrastructure
- GitHub Actions CI (`.github/workflows/test.yml`) - runs tests, doctests, and
  the example scripts across Python 3.9-3.13 on every push and pull request.
- Automated PyPI releases (`.github/workflows/release.yml`) - publishing is
  triggered only by pushing a `v*` tag and uses Trusted Publishing (OIDC), so no
  API token is stored anywhere. The build fails if the tag and the package
  version disagree.

### Known limitations
- Block tags cannot be escaped; `{{#if x}}` is still parsed as a block.
- `validate_template()` still reports syntax the renderer ignores (`{"key": 1}`,
  `{na me}`) as invalid. This function is not called on the rendering path.

## [0.3.0] - 2025-11-25

### Added
- **Conditional blocks** - `{#if condition}...{/if}` syntax for conditional content
- **Loop blocks** - `{#for item in items}...{/for}` syntax for iterating over collections
- **Else clause** - `{#if condition}...{#else}...{/if}` for alternative content
- **Comparison operators** - `{#if var == "value"}` and `{#if var != "value"}` support
- **Negation** - `{#if not condition}` for inverted conditions
- **Dot notation in conditions** - `{#if item.active}` for nested property checks
- **Loop index** - `{#for item, index in items}` to access iteration index
- **Dot notation variables** - `{user.name}` syntax for accessing nested object properties
- **New types** - `list` and `object` types in YAML frontmatter metadata
- **Type aliases** - `array` (alias for list), `dict` (alias for object)
- **Nested blocks** - Full support for blocks inside blocks (e.g., `{#if}` inside `{#for}`)
- `blocks.py` module with `parse_blocks()` and `render_blocks()` functions
- `BlockSyntaxError` exception for invalid block syntax
- 43 new test cases for block functionality

### Changed
- `render_template()` now processes blocks before variable substitution
- `render_template_with_defaults()` supports block syntax
- `validate_template()` validates block syntax
- `extract_variables()` excludes block keywords from variable detection
- Type stub generator supports `list[Any]` and `dict[str, Any]` types
- Test coverage increased to 74% with 134 total tests

### Technical Details
- New `blocks.py` module implements recursive descent parser for block syntax
- Block types: `TextBlock`, `IfBlock`, `ForBlock` as dataclasses
- `resolve_value()` function for dot notation property access
- `_substitute_text_variables()` for variable substitution within blocks

### Example
```markdown
---
description: Dynamic prompt with conditions and loops
show_examples(bool): Include examples
items(list): List of items to process
---

{#if show_examples}
## Examples
{#for item in items}
- {item.name}: {item.description}
{/for}
{/if}

{#if tone == "formal"}
Please maintain a professional tone.
{#else}
Feel free to be casual.
{/if}
```

```python
prompts.myPrompt(
    show_examples=True,
    items=[
        {"name": "Example 1", "description": "First example"},
        {"name": "Example 2", "description": "Second example"},
    ],
    tone="formal"
)
```

## [0.2.1] - 2025-11-17

### Fixed
- **Priority order for mixed static and dynamic files** - Static directories and files are now checked before dynamic directories
- Dynamic directories no longer override static files in the same parent directory

### Changed
- `PromptProxy.__getattr__()` now prioritizes static content over dynamic routing
- Improved resolution logic to support mixed file structures

### Added
- Support for combining dynamic `[param]` directories with static files in the same directory
- Three new test cases for mixed dynamic/static structure scenarios
- Documentation for mixed static and dynamic file usage in README

### Technical Details
- Modified `proxy.py:47-85` to reorder attribute resolution priority
- Test coverage improved from 58% to 70%
- All 91 tests passing with no regressions

### Example
You can now use this structure:
```
my-query/
  ├── [type]/
  │   ├── good/system.md
  │   └── bad/system.md
  ├── common.md         # Now accessible via myQuery.common()
  └── helper.md         # Now accessible via myQuery.helper()
```

## [0.2.0] - 2025-10-24

### Added
- **Dynamic routing support** (Next.js-style) with `[param]` directory syntax
- Automatic fallback to `default.md` when dynamic parameter value doesn't match
- Type hints with `Literal` types for dynamic parameters in generated stubs
- `is_dynamic_dir()` and `extract_param_name()` functions in path_utils
- Comprehensive test suite for dynamic routing (14 new tests)
- Dynamic routing documentation and examples
- `examples/dynamic_routing.py` demonstration script
- `examples/prompts-dynamic/` example prompt structure
- `init` CLI command to scaffold new projects with sample prompts
- PATTERN_ANALYSIS.md documentation for prompt management patterns

### Changed
- Enhanced type stub generation to support dynamic routing with Literal types
- Updated `PromptProxy` to detect and handle `[param]` directories
- Improved error messages for dynamic routing failures
- Test coverage increased from 75% to 78%
- Made `generate-types` the default CLI command (no need to type subcommand)
- **Improved path resolution documentation** with `Path(__file__).parent` pattern
- Updated all example files to use robust path resolution
- Enhanced docstrings in `create_prompts()` and `Prompteer.__init__()` with path resolution guidance

### Documentation
- Added "Path Resolution" section to README Quick Start
- Added path handling examples to AI agents section
- Reorganized README to improve sequential reading flow
- Added detailed explanations for Few-Shot, Chaining, Composition patterns

### Technical Details
- `proxy.py`: Added `_create_dynamic_callable()` and `_render_prompt()` methods
- `type_generator.py`: Added `_scan_dynamic_dir()` method and Literal import support
- `path_utils.py`: Added dynamic directory pattern recognition utilities
- `cli.py`: Added `cmd_init()` function and default command handling
- `core.py`: Enhanced docstrings with path resolution examples

## [0.1.0] - 2025-10-24

### Added
- Initial release of prompteer
- File-based prompt management with markdown files
- Intuitive dot notation API for accessing prompts
- YAML frontmatter support for prompt metadata
- Template variable substitution with type safety
- CLI tool for generating type stubs
- Watch mode for automatic type stub regeneration
- Support for multiple variable types (str, int, float, bool, number, any)
- IDE autocomplete support via generated .pyi files
- Zero-configuration setup
- Comprehensive test suite (74 tests)
- Documentation and examples

### Features
- `create_prompts()` factory function
- `Prompteer` class for prompt management
- Custom exceptions for better error handling
- Path utilities for kebab-case ↔ camelCase conversion
- Type stub generator with full type hints
- Template rendering with defaults

[0.3.0]: https://github.com/ibare/prompteer/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/ibare/prompteer/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ibare/prompteer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ibare/prompteer/releases/tag/v0.1.0
