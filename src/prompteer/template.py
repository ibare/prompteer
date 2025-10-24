"""
Template engine for prompteer.

Handles variable substitution in prompt templates using {variable} syntax.
"""

from __future__ import annotations

import re
from typing import Any

from prompteer.exceptions import TemplateVariableError


def extract_variables(template: str) -> set[str]:
    """Extract all variable names from a template.

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
    """
    # Find all {variable} patterns
    pattern = r"\{(\w+)\}"
    matches = re.findall(pattern, template)
    return set(matches)


def render_template(template: str, variables: dict[str, Any]) -> str:
    """Render a template by substituting variables.

    Args:
        template: Template string with {variable} placeholders
        variables: Dictionary of variable names to values

    Returns:
        Rendered template string

    Raises:
        TemplateVariableError: If a required variable is missing

    Examples:
        >>> render_template("Hello {name}!", {"name": "Alice"})
        'Hello Alice!'
        >>> render_template("Age: {age}", {"age": 30})
        'Age: 30'
    """
    # Find all variables in template
    required_vars = extract_variables(template)

    # Check for missing variables
    missing_vars = required_vars - set(variables.keys())
    if missing_vars:
        missing_list = ", ".join(sorted(missing_vars))
        raise TemplateVariableError(
            variable=missing_list,
            message=f"Missing required variables: {missing_list}",
        )

    # Convert all values to strings and substitute
    result = template
    for var_name, value in variables.items():
        if var_name in required_vars:
            placeholder = "{" + var_name + "}"
            result = result.replace(placeholder, str(value))

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
    # Find all variables in template
    required_vars = extract_variables(template)

    # Build complete variables dict with defaults
    complete_vars = {var: default for var in required_vars}
    complete_vars.update(variables)

    # Substitute
    result = template
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

    Args:
        template: Template string with {variable} placeholders
        variables: Dictionary of variable names to values
        defaults: Dictionary of default values for variables

    Returns:
        Rendered template string

    Raises:
        TemplateVariableError: If a required variable has no default and is missing

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

    # Find all variables in template
    required_vars = extract_variables(template)

    # Build complete variables dict
    complete_vars = {}
    missing_vars = []

    for var_name in required_vars:
        if var_name in variables:
            complete_vars[var_name] = variables[var_name]
        elif var_name in defaults:
            complete_vars[var_name] = defaults[var_name]
        else:
            missing_vars.append(var_name)

    # Check for missing variables without defaults
    if missing_vars:
        missing_list = ", ".join(sorted(missing_vars))
        raise TemplateVariableError(
            variable=missing_list,
            message=f"Missing required variables (no defaults): {missing_list}",
        )

    # Substitute
    result = template
    for var_name, value in complete_vars.items():
        placeholder = "{" + var_name + "}"
        result = result.replace(placeholder, str(value))

    return result


def validate_template(template: str) -> tuple[bool, str | None]:
    """Validate a template string.

    Args:
        template: Template string to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_template("Hello {name}!")
        (True, None)
        >>> validate_template("Hello {name!")
        (False, 'Unclosed brace at position ...')
    """
    # Check for unmatched braces
    open_count = template.count("{")
    close_count = template.count("}")

    if open_count != close_count:
        return False, f"Unmatched braces: {open_count} open, {close_count} close"

    # Check for valid variable names
    pattern = r"\{(\w+)\}"
    matches = re.finditer(r"\{[^}]*\}", template)

    for match in matches:
        content = match.group(0)
        if not re.match(r"^\{\w+\}$", content):
            return False, f"Invalid variable syntax: {content}"

    return True, None
