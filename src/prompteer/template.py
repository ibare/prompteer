"""
Template engine for prompteer.

Handles variable substitution in prompt templates using {variable} syntax.
Also supports block syntax: {#if}, {#for}, {#else}, {/if}, {/for}.

핵심 불변식:
    템플릿 텍스트는 정확히 한 번만 스캔된다. 치환으로 만들어진 출력은
    어떤 단계에서도 다시 변수로 해석되지 않는다.

    이 불변식 덕분에 주입값 안에 들어 있는 중괄호(예: "React {children} 사용법")
    는 미해결 변수로 오인되지 않는다. 미해결 변수 판정에 필요한 정보는
    치환이 일어나는 지점에서만 정확하므로, 렌더 결과를 다시 훑는 대신
    substitute_variables 가 수집한 집합으로 판정한다.
"""

from __future__ import annotations

import re
from typing import Any

from prompteer.blocks import (
    BLOCK_KEYWORDS,
    VARIABLE_PATTERN,
    BlockSyntaxError,
    parse_blocks,
    render_blocks,
    resolve_value,
    substitute_variables,
)
from prompteer.exceptions import TemplateVariableError

__all__ = [
    "extract_variables",
    "extract_all_variables",
    "render_template",
    "render_template_safe",
    "render_template_with_defaults",
    "validate_template",
]


def extract_variables(template: str) -> set[str]:
    """Extract all simple variable names from a template.

    점 표기 변수({user.name})와 이스케이프된 리터럴({{name}}), 블록 문법은
    제외한다.

    Args:
        template: Template string with {variable} placeholders

    Returns:
        Set of variable names found in the template

    Examples:
        >>> extract_variables("Hello {name}!")
        {'name'}
        >>> sorted(extract_variables("Hello {name}, you are {age} years old"))
        ['age', 'name']
        >>> extract_variables("No variables here")
        set()
        >>> extract_variables("{#if show}Hello{/if}")
        set()
        >>> extract_variables("{{name}}")
        set()
    """
    return {
        name
        for name in _iter_variable_names(template)
        if "." not in name and name not in BLOCK_KEYWORDS
    }


def extract_all_variables(template: str) -> set[str]:
    """Extract all variable names including dot notation from a template.

    This includes both simple variables {name} and dot notation {user.name}.
    이스케이프된 리터럴({{name}})과 블록 문법은 제외한다.

    Args:
        template: Template string with {variable} placeholders

    Returns:
        Set of root variable names found in the template

    Examples:
        >>> extract_all_variables("Hello {user.name}!")
        {'user'}
        >>> extract_all_variables("{item.title} by {item.author}")
        {'item'}
        >>> extract_all_variables("{{user.name}}")
        set()
    """
    return {
        name.split(".")[0]
        for name in _iter_variable_names(template)
        if name.split(".")[0] not in BLOCK_KEYWORDS
    }


def _iter_variable_names(template: str) -> list[str]:
    """통합 패턴으로 템플릿을 훑어 변수 이름만 뽑는다.

    이스케이프 토큰({{, }})은 group(1) 이 None 이므로 자연히 걸러진다.
    """
    return [m.group(1) for m in VARIABLE_PATTERN.finditer(template) if m.group(1)]


def _has_blocks(template: str) -> bool:
    """Check if template contains block syntax."""
    return "{#if" in template or "{#for" in template


def _render(
    template: str,
    variables: dict[str, Any],
    missing_default: str | None = None,
) -> tuple[str, set[str]]:
    """템플릿을 단일 패스로 렌더하고 (결과, 미해결 변수) 를 돌려준다.

    블록이 있는 템플릿은 parse_blocks 가 블록 밖 텍스트까지 TextBlock 으로
    포함하므로, render_blocks 한 번으로 모든 치환이 끝난다. 결과 문자열에
    대한 추가 치환 패스는 존재하지 않는다.
    """
    missing: set[str] = set()

    if _has_blocks(template):
        result = render_blocks(
            parse_blocks(template),
            variables,
            missing=missing,
            missing_default=missing_default,
        )
    else:
        result = substitute_variables(
            template,
            variables,
            missing=missing,
            missing_default=missing_default,
        )

    return result, missing


def _raise_missing(missing: set[str], suffix: str = "") -> None:
    """미해결 변수가 있으면 TemplateVariableError 를 던진다."""
    if not missing:
        return
    missing_list = ", ".join(sorted(missing))
    raise TemplateVariableError(
        variable=missing_list,
        message=f"Missing required variables{suffix}: {missing_list}",
    )


def render_template(template: str, variables: dict[str, Any]) -> str:
    """Render a template by substituting variables and processing blocks.

    Supports:
    - Simple variables: {name}
    - Dot notation: {user.name}
    - Conditional blocks: {#if condition}...{/if}
    - Loop blocks: {#for item in items}...{/for}
    - Escaped literals: {{name}} renders as {name}

    주입값 안의 중괄호는 변수로 해석되지 않는다.

    Args:
        template: Template string with {variable} placeholders and blocks
        variables: Dictionary of variable names to values

    Returns:
        Rendered template string

    Raises:
        TemplateVariableError: If a required variable is missing
        BlockSyntaxError: If block syntax is invalid

    Examples:
        >>> render_template("Hello {name}!", {"name": "Alice"})
        'Hello Alice!'
        >>> render_template("Age: {age}", {"age": 30})
        'Age: 30'
        >>> render_template("{#if show}Hello{/if}", {"show": True})
        'Hello'
        >>> render_template("{#for x in items}{x}{/for}", {"items": [1, 2, 3]})
        '123'
        >>> render_template("A: {a}", {"a": "x {foo} y"})
        'A: x {foo} y'
    """
    result, missing = _render(template, variables)
    _raise_missing(missing)
    return result


def render_template_safe(
    template: str, variables: dict[str, Any], default: str = ""
) -> str:
    """Render a template with safe fallback for missing variables.

    render_template 과 동일한 단일 패스 파이프라인을 쓰므로 점 표기 변수도
    치환되고, 치환 순서에 따라 결과가 달라지지 않는다.

    Args:
        template: Template string with {variable} placeholders
        variables: Dictionary of variable names to values
        default: Default value for missing variables

    Returns:
        Rendered template string with defaults for missing variables

    Examples:
        >>> render_template_safe("Hello {name}!", {})
        'Hello !'
        >>> render_template_safe("Hello {name}!", {}, default="Guest")
        'Hello Guest!'
        >>> render_template_safe("{user.name}", {"user": {"name": "Bob"}})
        'Bob'
    """
    result, _ = _render(template, variables, missing_default=default)
    return result


def render_template_with_defaults(
    template: str,
    variables: dict[str, Any],
    defaults: dict[str, Any] | None = None,
) -> str:
    """Render a template with per-variable defaults.

    Supports:
    - Simple variables: {name}
    - Dot notation: {user.name}
    - Conditional blocks: {#if condition}...{/if}
    - Loop blocks: {#for item in items}...{/for}
    - Escaped literals: {{name}} renders as {name}

    Args:
        template: Template string with {variable} placeholders
        variables: Dictionary of variable names to values
        defaults: Dictionary of default values for variables

    Returns:
        Rendered template string

    Raises:
        TemplateVariableError: If a required variable has no default and is missing
        BlockSyntaxError: If block syntax is invalid

    Examples:
        >>> render_template_with_defaults(
        ...     "Hello {name}, age {age}",
        ...     {"name": "Alice"},
        ...     {"age": 0}
        ... )
        'Hello Alice, age 0'
        >>> render_template_with_defaults("A: {a}", {"a": "x {foo} y"}, {})
        'A: x {foo} y'
    """
    # defaults 는 치환 이전에 병합되므로, 여기서 해결되지 않은 이름은
    # 기본값으로도 채울 수 없는 진짜 누락이다.
    merged_vars = {**(defaults or {}), **variables}

    result, missing = _render(template, merged_vars)
    _raise_missing(missing, suffix=" (no defaults)")
    return result


def validate_template(template: str) -> tuple[bool, str | None]:
    """Validate a template string including block syntax.

    Args:
        template: Template string to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_template("Hello {name}!")
        (True, None)
        >>> validate_template("Hello {name!")
        (False, 'Unmatched braces: 1 open, 0 close')
        >>> validate_template("{#if show}Hello{/if}")
        (True, None)
        >>> validate_template("{{name}}")
        (True, None)
    """
    # 이스케이프된 중괄호는 리터럴이므로 검사 대상에서 제외한다.
    scannable = template.replace("{{", "").replace("}}", "")

    # Check for unmatched braces
    open_count = scannable.count("{")
    close_count = scannable.count("}")

    if open_count != close_count:
        return False, f"Unmatched braces: {open_count} open, {close_count} close"

    # Validate block syntax if present
    if _has_blocks(template):
        try:
            parse_blocks(template)
        except BlockSyntaxError as e:
            return False, str(e)

    # Check for valid variable/block syntax
    # Valid patterns: {word}, {word.word...}, {#if ...}, {#for ...}, {#else}, {/if}, {/for}
    valid_pattern = re.compile(
        r"^\{(\w+(?:\.\w+)*|#(?:if|for|else)\s*.*?|/(?:if|for))\}$"
    )

    matches = re.finditer(r"\{[^}]*\}", scannable)

    for match in matches:
        content = match.group(0)
        if not valid_pattern.match(content):
            return False, f"Invalid variable syntax: {content}"

    return True, None


# resolve_value 는 blocks 모듈 소유지만, 과거 template 모듈에서 재export 되어
# 왔으므로 import 경로를 유지한다.
_ = resolve_value
