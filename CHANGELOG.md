# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/ibare/prompteer/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ibare/prompteer/releases/tag/v0.1.0
