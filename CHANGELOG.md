# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-06

### Fixed
- **주입값 안의 중괄호를 미해결 변수로 오인하던 문제** - 렌더링이 단일 패스로
  바뀌면서, 값에 포함된 `{...}` 는 더 이상 변수로 해석되지 않는다.
  `render_template("A: {a}", {"a": "React {children} 사용법"})` 처럼 흔한 입력이
  `TemplateVariableError` 로 실패하던 회귀가 해소됐다. 누락 변수 검출력은 그대로다.
  - 평문, `{#if}`, `{#for}`, 점 표기 등 모든 렌더 경로에 동일하게 적용된다.
- **`render_template_safe()` 의 비결정적 출력** - 변수마다 `str.replace` 를 순차
  적용하던 구현이 치환 순서(해시 시드)에 따라 결과가 달라졌다. 공통 파이프라인으로
  통합해 순서 의존성을 제거했다.
- **`render_template_safe()` 가 점 표기 변수를 치환하지 못하던 문제** - `{user.name}`
  이 값을 제공해도 원문 그대로 남던 동작을 수정했다.

### Added
- **중괄호 이스케이프** - `{{` 와 `}}` 로 리터럴 중괄호를 표현한다.
  템플릿 본문에 `{children}` 같은 문자열을 그대로 쓰려면 `{{children}}` 으로 적는다.
- `blocks.substitute_variables()` - 단일 치환 구현 (공개 API)
- `blocks.VARIABLE_PATTERN`, `blocks.BLOCK_KEYWORDS`
- 주입값 중괄호 회귀 방지 테스트 27건 (`tests/test_brace_injection.py`)

### Changed
- 렌더링 파이프라인을 단일 패스로 재구성했다. 템플릿은 정확히 한 번만 스캔되며,
  치환으로 만들어진 출력은 어떤 단계에서도 다시 변수로 해석되지 않는다.
- `render_template()`, `render_template_safe()`, `render_template_with_defaults()`
  가 모두 같은 렌더 코어를 공유한다.
- `extract_variables()`, `extract_all_variables()`, `validate_template()` 이
  이스케이프된 중괄호를 인식한다.

### Breaking
- **`{{foo}}` 의 의미가 바뀐다.** 기존에는 `{` + `foo` 치환값 + `}` 로 해석됐으나,
  이제 리터럴 `{foo}` 가 된다. 이스케이프를 우회 수단으로 써 온 코드는 값 주입
  지점에서 이스케이프를 걷어내야 한다 (템플릿 본문의 리터럴 목적이라면 그대로 두면 된다).
- **점 표기 부분 실패가 오류가 된다.** `{user.name}` 에서 `user` 는 있으나 `name`
  속성이 없으면 조용히 자리표시자를 남기는 대신 `TemplateVariableError` 를 던진다.
- **`render_template_safe()` 가 점 표기를 치환한다.** 기존에 `{user.name}` 원문이
  나오던 자리에 값이 들어간다.
- 내부 함수 `template._substitute_variables()`, `blocks._substitute_text_variables()`
  가 `blocks.substitute_variables()` 로 통합·제거됐다.

### Known limitations
- 블록 태그는 이스케이프할 수 없다. `{{#if x}}` 는 여전히 블록으로 파싱된다.
- `validate_template()` 은 렌더러가 무시하는 구문(`{"key": 1}`, `{na me}`)을 여전히
  invalid 로 판정한다. 이 함수는 렌더 경로에서 호출되지 않는다.

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
