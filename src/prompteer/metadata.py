"""
Metadata parser for YAML frontmatter in prompt files.

Parses frontmatter in the format:
---
description: Prompt description
name: Variable description
age(int): Variable with type
---
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class VariableInfo:
    """Information about a template variable."""

    name: str
    type: str
    description: str
    default: Any = None

    def __post_init__(self) -> None:
        """Validate and normalize type."""
        # Normalize type names
        type_mapping = {
            "string": "str",
            "boolean": "bool",
            "number": "number",  # Keep as number for Union[int, float]
        }
        self.type = type_mapping.get(self.type, self.type)


@dataclass
class PromptMetadata:
    """Metadata extracted from prompt file."""

    description: str | None
    variables: dict[str, VariableInfo]
    raw_frontmatter: dict[str, Any]


def parse_variable_key(key: str) -> tuple[str, str]:
    """Parse variable key to extract name and type.

    Args:
        key: Variable key in format "name" or "name(type)"

    Returns:
        Tuple of (variable_name, variable_type)

    Examples:
        >>> parse_variable_key("name")
        ('name', 'str')
        >>> parse_variable_key("age(int)")
        ('age', 'int')
        >>> parse_variable_key("height(float)")
        ('height', 'float')
    """
    # Pattern: variable_name(type) or just variable_name
    pattern = r"^(\w+)(?:\((\w+)\))?$"
    match = re.match(pattern, key.strip())

    if not match:
        # Invalid format, treat as plain string variable
        return key, "str"

    var_name = match.group(1)
    var_type = match.group(2) or "str"  # Default to str

    return var_name, var_type


def extract_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Extract YAML frontmatter from content.

    Args:
        content: File content that may contain frontmatter

    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter)
        If no frontmatter, returns (None, original_content)

    Examples:
        >>> content = "---\\nkey: value\\n---\\nContent"
        >>> fm, body = extract_frontmatter(content)
        >>> fm
        {'key': 'value'}
        >>> body
        'Content'
    """
    if yaml is None:
        # PyYAML not installed, return content as-is
        return None, content

    # Check if content starts with ---
    if not content.strip().startswith("---"):
        return None, content

    # Find the closing ---
    lines = content.split("\n")
    if len(lines) < 3:  # Need at least ---, content, ---
        return None, content

    # Find second --- (closing delimiter)
    closing_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        # No closing delimiter found
        return None, content

    # Extract frontmatter
    frontmatter_lines = lines[1:closing_idx]
    content_lines = lines[closing_idx + 1 :]

    # Parse YAML
    try:
        frontmatter_text = "\n".join(frontmatter_lines)
        frontmatter_dict = yaml.safe_load(frontmatter_text)

        # If parsing resulted in None or not a dict, treat as no frontmatter
        if not isinstance(frontmatter_dict, dict):
            return None, content

        # Join remaining content
        remaining_content = "\n".join(content_lines)

        return frontmatter_dict, remaining_content

    except yaml.YAMLError:
        # Invalid YAML, treat as no frontmatter
        return None, content


def parse_metadata(content: str) -> tuple[PromptMetadata, str]:
    """Parse metadata from prompt file content.

    Args:
        content: Prompt file content with optional YAML frontmatter

    Returns:
        Tuple of (PromptMetadata, content_without_frontmatter)

    Examples:
        >>> content = '''---
        ... description: User greeting
        ... name: User name
        ... age(int): User age
        ... ---
        ... Hello {name}!'''
        >>> metadata, body = parse_metadata(content)
        >>> metadata.description
        'User greeting'
        >>> len(metadata.variables)
        2
    """
    # Extract frontmatter
    frontmatter, body = extract_frontmatter(content)

    # If no frontmatter, return empty metadata
    if frontmatter is None:
        return PromptMetadata(
            description=None,
            variables={},
            raw_frontmatter={},
        ), body

    # Extract description (reserved key)
    description = frontmatter.get("description")
    if description is not None:
        description = str(description)

    # Parse variables (all keys except description)
    variables = {}
    for key, value in frontmatter.items():
        if key == "description":
            continue

        # Parse variable key for name and type
        var_name, var_type = parse_variable_key(key)

        # Description is the value
        var_description = str(value) if value is not None else ""

        # Create VariableInfo
        var_info = VariableInfo(
            name=var_name,
            type=var_type,
            description=var_description,
        )

        variables[var_name] = var_info

    return PromptMetadata(
        description=description,
        variables=variables,
        raw_frontmatter=frontmatter,
    ), body


def get_type_default(var_type: str) -> Any:
    """Get default value for a variable type.

    Args:
        var_type: Variable type string

    Returns:
        Default value for the type

    Examples:
        >>> get_type_default("str")
        ''
        >>> get_type_default("int")
        0
        >>> get_type_default("float")
        0.0
        >>> get_type_default("bool")
        False
    """
    defaults = {
        "str": "",
        "int": 0,
        "float": 0.0,
        "bool": False,
        "number": 0,
        "any": None,
    }
    return defaults.get(var_type, None)
