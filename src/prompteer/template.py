"""
Template engine for prompteer.

Handles variable substitution in prompt templates using {variable} syntax.
Also supports block syntax: {#if}, {#for}, {#else}, {/if}, {/for}.
"""

from __future__ import annotations

import re
from typing import Any

from prompteer.blocks import (
    BlockSyntaxError,
    parse_blocks,
    render_blocks,
    resolve_value,
)
from prompteer.exceptions import TemplateVariableError


def extract_variables(template: str) -> set[str]:
    """Extract all variable names from a template.

    Excludes block syntax ({#if}, {#for}, {/if}, {/for}, {#else}).

    Args:
        template: Template string with {variable} placeholders

    Returns:
        Set of variable names found in the template

    Examples:
        >>> extract_variables("Hello {name}!")
        {'name'}
        >>> extract_variables("Hello {name}, you are {age} years old")
        {'name', 'age'}
        >>> extract_variables("No variables here")
        set()
        >>> extract_variables("{#if show}Hello{/if}")
        set()
    """
    # Find all {variable} patterns, excluding block syntax
    # Match {word} but not {#word}, {/word}, or {word.property}
    pattern = r"\{(\w+)\}"
    matches = re.findall(pattern, template)

    # Filter out block keywords
    block_keywords = {"if", "for", "else"}
    return {m for m in matches if m not in block_keywords}


def extract_all_variables(template: str) -> set[str]:
    """Extract all variable names including dot notation from a template.

    This includes both simple variables {name} and dot notation {user.name}.
    Excludes block syntax ({#if}, {#for}, etc.).

    Args:
        template: Template string with {variable} placeholders

    Returns:
        Set of root variable names found in the template

    Examples:
        >>> extract_all_variables("Hello {user.name}!")
        {'user'}
        >>> extract_all_variables("{item.title} by {item.author}")
        {'item'}
    """
    # Match both {word} and {word.word.word...} patterns
    pattern = r"\{(\w+(?:\.\w+)*)\}"
    matches = re.findall(pattern, template)

    # Extract root variable names (before first dot)
    root_vars = set()
    block_keywords = {"if", "for", "else"}

    for match in matches:
        root = match.split(".")[0]
        if root not in block_keywords:
            root_vars.add(root)

    return root_vars


def _has_blocks(template: str) -> bool:
    """Check if template contains block syntax."""
    return "{#if" in template or "{#for" in template


def _substitute_variables(
    text: str,
    variables: dict[str, Any],
    local_vars: dict[str, Any] | None = None,
) -> str:
    """Substitute variables in text, supporting dot notation.

    Args:
        text: Text with {variable} placeholders
        variables: Global variables
        local_vars: Local variables (from for loops)

    Returns:
        Text with variables substituted
    """
    if local_vars is None:
        local_vars = {}

    # Match both {word} and {word.word...} patterns, but not block syntax
    pattern = r"\{(\w+(?:\.\w+)*)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        # Skip block keywords
        if var_name in ("if", "for", "else"):
            return match.group(0)
        try:
            value = resolve_value(var_name, variables, local_vars)
            return str(value)
        except TemplateVariableError:
            # If variable not found, leave placeholder as-is for later error
            return match.group(0)

    return re.sub(pattern, replacer, text)


def render_template(template: str, variables: dict[str, Any]) -> str:
    """Render a template by substituting variables and processing blocks.

    Supports:
    - Simple variables: {name}
    - Dot notation: {user.name}
    - Conditional blocks: {#if condition}...{/if}
    - Loop blocks: {#for item in items}...{/for}

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
    """
    # Process blocks first if present
    if _has_blocks(template):
        blocks = parse_blocks(template)
        result = render_blocks(blocks, variables)
        # Substitute remaining variables
        result = _substitute_variables(result, variables)
    else:
        # Simple variable substitution
        result = _substitute_variables(template, variables)

    # Check for unsubstituted variables (excluding block keywords)
    remaining_vars = extract_variables(result)
    if remaining_vars:
        missing_list = ", ".join(sorted(remaining_vars))
        raise TemplateVariableError(
            variable=missing_list,
            message=f"Missing required variables: {missing_list}",
        )

    return result


def render_template_safe(
    template: str, variables: dict[str, Any], default: str = ""
) -> str:
    """Render a template with safe fallback for missing variables.

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
    """
    # Process blocks first if present
    if _has_blocks(template):
        blocks = parse_blocks(template)
        result = render_blocks(blocks, variables)
    else:
        result = template

    # Find all variables in result
    required_vars = extract_variables(result)

    # Build complete variables dict with defaults
    complete_vars = {var: default for var in required_vars}
    complete_vars.update(variables)

    # Substitute
    for var_name, value in complete_vars.items():
        placeholder = "{" + var_name + "}"
        result = result.replace(placeholder, str(value))

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
    """
    if defaults is None:
        defaults = {}

    # Merge variables with defaults (variables take precedence)
    merged_vars = {**defaults, **variables}

    # Process blocks first if present
    if _has_blocks(template):
        blocks = parse_blocks(template)
        result = render_blocks(blocks, merged_vars)
        # Substitute remaining simple variables
        result = _substitute_variables(result, merged_vars)
    else:
        # Simple variable substitution
        result = _substitute_variables(template, merged_vars)

    # Check for unsubstituted variables
    remaining_vars = extract_variables(result)
    if remaining_vars:
        # Check which ones are truly missing (not in defaults either)
        missing_vars = [v for v in remaining_vars if v not in merged_vars]
        if missing_vars:
            missing_list = ", ".join(sorted(missing_vars))
            raise TemplateVariableError(
                variable=missing_list,
                message=f"Missing required variables (no defaults): {missing_list}",
            )

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
        (False, 'Unclosed brace at position ...')
        >>> validate_template("{#if show}Hello{/if}")
        (True, None)
    """
    # Check for unmatched braces
    open_count = template.count("{")
    close_count = template.count("}")

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

    matches = re.finditer(r"\{[^}]*\}", template)

    for match in matches:
        content = match.group(0)
        if not valid_pattern.match(content):
            return False, f"Invalid variable syntax: {content}"

    return True, None
