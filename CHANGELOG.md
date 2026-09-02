# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-09-02

### Fixed
- **Dynamic routing stopped after one `[param]` level** - A nested
  `[param]` directory was never scanned, so
  `prompts.q.user(type="basic", lang="ko")` silently returned the outer
  `default.md` and dropped `lang`. Routing is now recursive, and a parameter a
  route needs is required rather than ignored.
- **Name matching was delegated to the filesystem** - `Path.is_dir()` and
  `Path.exists()` follow the rules of whatever filesystem is underneath, so a
  tree that resolved on macOS (case-insensitive, names often stored as NFD)
  could fail on a case-sensitive Linux server. Matching now happens inside
  prompteer, ignoring case and unicode normal form, and produces the same
  result on every platform. The same rule applies to routing values, so
  `type="BASIC"` no longer resolves on one OS and falls back to `default.md`
  on another.
- **An empty routing value resolved ambiguously** - `type=""` joined to the
  `[param]` directory itself, so it read a stray file inside it or fell through
  to `default.md`. Empty, blank and `None` values now raise
  `DynamicParameterError`.
- **Routing values could escape the prompt directory** - `type="../../etc"`
  was joined into the path unchecked. Path separators and relative references
  are now rejected.
- **A routing value that matched nothing could be silently ignored** - Passing
  a parameter that no route consumes now raises instead of quietly rendering a
  generic prompt.

### Added
- **Nested `[param]` routing** - `[param]` directories may nest to any depth;
  each level consumes its own argument.
- **Static directories inside dynamic routes** - `q/[type]/basic/extra/user.md`
  is reachable as `prompts.q.extra.user(type="basic")`. Such paths resolve at
  call time, because the routing arguments are only known then.
- **Routing values are available as template variables** - A prompt selected
  through `[tier]/pro/[lang]/ko/` can write `{tier}` and `{lang}` in its body,
  including in `default.md` and the `default/` subtree. The value substituted
  is the one the caller passed, not the directory it matched, so `tier="PRO"`
  selects `pro/` and renders `PRO`. Previously the value was consumed by
  routing and unreachable: `{type}` rendered as literal `{type}`, as an empty
  string when declared in frontmatter, or raised `TemplateVariableError` when
  other arguments were present. These names cannot collide with caller
  variables, since routing pops the name before rendering and Python forbids
  passing the same keyword twice.
- **`default/` fallback subtree** - A `default/` directory beside the value
  directories stands in for a whole subtree. `default.md` still works but is
  used only when a single name remains to resolve, since one file cannot
  distinguish `extra/user` from `extra/system`.
- `DynamicParameterError` - unusable routing value (empty, blank, `None`,
  unsupported type, or containing path separators).
- `AmbiguousPromptError` - two entries in one directory differing only by case
  or unicode normal form, or two `[param]` directories at one level.
- `Enum` values are accepted for routing and route by their `.value`.
- Resolution failures list every path that was tried.
- `path_utils.clear_path_cache()` - drops the cached directory listings.
- `@overload` generation in type stubs when branches of the tree require
  different routing parameters, instead of unioning them into one signature
  that claims every parameter is always required.
- Type stub warnings for unportable trees: entries differing only by case, and
  a directory and prompt file sharing a name.
- `examples/prompts-dynamic/support/` and two new sections in
  `examples/dynamic_routing.py` covering nested routes, static directories
  inside a route, and the `default/` subtree. `prompteer init` scaffolds the
  same structure.
- 31 tests in `tests/test_nested_dynamic_routing.py` and
  `tests/test_case_matching.py`, plus routing value validation, name matching
  and stub generation tests. The suite grew from 161 to 218 tests.

### Changed
- **Static and dynamic precedence is decided by the call, not the filesystem.**
  If you pass a level's routing parameter, the dynamic route is tried first and
  the static match is used only as a fallback; if you do not pass it, the
  static match wins. Previously the static match always won, so passing a
  routing argument could quietly return the generic prompt.
- Attribute access inside a directory that holds a `[param]` now returns a
  deferred proxy and resolves on call. Trees without dynamic routing are
  unchanged and still resolve eagerly.
- `PromptNotFoundError` also inherits from `AttributeError`, so `hasattr()` and
  other introspection helpers behave normally on prompt proxies.
- Attribute names starting with `_` are never routed, so `hasattr`, `copy` and
  IDE introspection no longer receive a routing callable.
- Type stub attribute names are normalized to camelCase (`Chat/` → `chat`).
  Previously a capitalized directory produced an attribute the runtime could
  not resolve.
- Resolution is bounded to 64 levels to stop symlink loops.

### Breaking
- `type=""`, `type=None`, values with path separators, and unsupported value
  types now raise `DynamicParameterError` instead of resolving to something
  arbitrary. A *missing* argument still raises `TypeError`.
- Passing a routing parameter that no route consumes now raises.
- Two entries in one directory that differ only by case or unicode normal form
  now raise `AmbiguousPromptError` instead of resolving to whichever one the
  filesystem returned first. This is only reachable on a case-sensitive
  filesystem.
- `PromptProxy.__getattr__` may return a `DeferredPromptProxy` rather than a
  `PromptProxy` or a plain callable. It is still callable and still supports
  attribute chaining; code that inspected the returned type may need updating.

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
