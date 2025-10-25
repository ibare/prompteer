"""
Path conversion utilities for prompteer.

Handles conversion between file system paths (kebab-case) and
Python attributes (camelCase).
"""

from __future__ import annotations

import re
from pathlib import Path


def kebab_to_camel(name: str) -> str:
    """Convert kebab-case to camelCase.

    Args:
        name: Kebab-case string (e.g., "my-prompt-name")

    Returns:
        CamelCase string (e.g., "myPromptName")

    Examples:
        >>> kebab_to_camel("my-prompt")
        'myPrompt'
        >>> kebab_to_camel("user-profile-settings")
        'userProfileSettings'
        >>> kebab_to_camel("simple")
        'simple'
    """
    if "-" not in name:
        return name

    parts = name.split("-")
    # First part stays lowercase, rest are capitalized
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def camel_to_kebab(name: str) -> str:
    """Convert camelCase to kebab-case.

    Args:
        name: CamelCase string (e.g., "myPromptName")

    Returns:
        Kebab-case string (e.g., "my-prompt-name")

    Examples:
        >>> camel_to_kebab("myPrompt")
        'my-prompt'
        >>> camel_to_kebab("userProfileSettings")
        'user-profile-settings'
        >>> camel_to_kebab("simple")
        'simple'
    """
    # Insert hyphen before uppercase letters and convert to lowercase
    return re.sub(r"([A-Z])", r"-\1", name).lower().lstrip("-")


def normalize_path_segment(segment: str, to_camel: bool = True) -> str:
    """Normalize a path segment between filesystem and attribute format.

    Args:
        segment: Path segment to normalize
        to_camel: If True, convert to camelCase; if False, convert to kebab-case

    Returns:
        Normalized path segment

    Examples:
        >>> normalize_path_segment("my-prompt", to_camel=True)
        'myPrompt'
        >>> normalize_path_segment("myPrompt", to_camel=False)
        'my-prompt'
    """
    if to_camel:
        return kebab_to_camel(segment)
    else:
        return camel_to_kebab(segment)


def resolve_prompt_path(
    base_path: Path, attribute_path: list[str], is_file: bool = False
) -> Path:
    """Resolve attribute access path to filesystem path.

    Args:
        base_path: Base directory containing prompts
        attribute_path: List of attribute names (camelCase)
        is_file: If True, add .md extension

    Returns:
        Resolved filesystem path

    Examples:
        >>> base = Path("/prompts")
        >>> resolve_prompt_path(base, ["myPrompt", "question"], is_file=False)
        PosixPath('/prompts/my-prompt/question')
        >>> resolve_prompt_path(base, ["myPrompt", "question", "user"], is_file=True)
        PosixPath('/prompts/my-prompt/question/user.md')
    """
    # Convert each attribute segment to kebab-case
    path_segments = [camel_to_kebab(attr) for attr in attribute_path]

    # Build path
    result = base_path
    for segment in path_segments:
        result = result / segment

    # Add .md extension if it's a file
    if is_file and not result.suffix:
        result = result.with_suffix(".md")

    return result


def is_valid_attribute_name(name: str) -> bool:
    """Check if a name is a valid Python attribute name.

    Args:
        name: Name to check

    Returns:
        True if valid, False otherwise

    Examples:
        >>> is_valid_attribute_name("myPrompt")
        True
        >>> is_valid_attribute_name("my-prompt")
        False
        >>> is_valid_attribute_name("123invalid")
        False
    """
    # Must start with letter or underscore, followed by letters, digits, or underscores
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name))


def is_dynamic_dir(name: str) -> bool:
    """Check if a directory name represents a dynamic parameter.

    Dynamic directories are enclosed in square brackets, e.g., [type], [category].

    Args:
        name: Directory name to check

    Returns:
        True if name matches [param] pattern, False otherwise

    Examples:
        >>> is_dynamic_dir("[type]")
        True
        >>> is_dynamic_dir("[category]")
        True
        >>> is_dynamic_dir("normal")
        False
        >>> is_dynamic_dir("[invalid name]")
        False
        >>> is_dynamic_dir("[]")
        False
    """
    # Pattern: [valid_identifier]
    pattern = r"^\[([a-zA-Z_][a-zA-Z0-9_]*)\]$"
    return bool(re.match(pattern, name))


def extract_param_name(name: str) -> str:
    """Extract parameter name from dynamic directory name.

    Args:
        name: Dynamic directory name (e.g., "[type]")

    Returns:
        Parameter name without brackets (e.g., "type")

    Raises:
        ValueError: If name is not a valid dynamic directory

    Examples:
        >>> extract_param_name("[type]")
        'type'
        >>> extract_param_name("[category]")
        'category'
        >>> extract_param_name("normal")
        Traceback (most recent call last):
            ...
        ValueError: Not a dynamic directory: normal
    """
    pattern = r"^\[([a-zA-Z_][a-zA-Z0-9_]*)\]$"
    match = re.match(pattern, name)
    if not match:
        raise ValueError(f"Not a dynamic directory: {name}")
    return match.group(1)
