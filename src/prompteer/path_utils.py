"""
Path conversion utilities for prompteer.

Handles conversion between file system paths (kebab-case) and
Python attributes (camelCase).
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Literal


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


# ---------------------------------------------------------------------------
# 대소문자 / 유니코드 정규화 매칭
#
# 파일 존재 여부를 OS 에 맡기면(Path.is_dir(), Path.exists()) 매칭 규칙이
# 파일시스템마다 달라진다. macOS(APFS 기본)는 대소문자를 무시하고 파일명을
# NFD 로 저장하지만, Linux 의 ext4 는 대소문자를 구분하고 보통 NFC 를 쓴다.
# 그래서 로컬에서 통과한 코드가 배포 서버에서 깨진다.
#
# 매칭을 prompteer 안에서 직접 수행해 모든 OS 에서 같은 결과를 보장한다.
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Normalize a filesystem name for case/unicode-insensitive comparison.

    Args:
        name: Raw filesystem or attribute name

    Returns:
        Normalization key (NFC-normalized, case-folded)

    Examples:
        >>> normalize_name("Chat") == normalize_name("chat")
        True
        >>> normalize_name("CODE-REVIEW") == normalize_name("code-review")
        True
    """
    return unicodedata.normalize("NFC", name).casefold()


# 디렉터리 목록 캐시: path -> (mtime_ns, {정규화 키: [실제 이름, ...]})
_dir_index_cache: dict[str, tuple[int, dict[str, list[str]]]] = {}


def clear_path_cache() -> None:
    """Clear the cached directory listings.

    Useful in long-running processes or tests that mutate the prompt tree
    faster than the directory mtime resolution can detect.
    """
    _dir_index_cache.clear()


def _build_index(directory: Path) -> dict[str, list[str]]:
    """Build a normalized-name index for a directory.

    Args:
        directory: Directory to index

    Returns:
        Mapping of normalization key to the actual on-disk names
    """
    index: dict[str, list[str]] = {}
    try:
        entries = list(os.scandir(directory))
    except (NotADirectoryError, FileNotFoundError, PermissionError):
        return index

    for entry in entries:
        index.setdefault(normalize_name(entry.name), []).append(entry.name)

    # 실제 이름 목록은 정렬해 두어 결과가 파일시스템 순회 순서에 의존하지 않게 한다.
    for names in index.values():
        names.sort()
    return index


def get_dir_index(directory: Path) -> dict[str, list[str]]:
    """Get the normalized-name index for a directory, using an mtime cache.

    Args:
        directory: Directory to index

    Returns:
        Mapping of normalization key to the actual on-disk names
    """
    key = str(directory)
    try:
        mtime = directory.stat().st_mtime_ns
    except (NotADirectoryError, FileNotFoundError, PermissionError):
        _dir_index_cache.pop(key, None)
        return {}

    cached = _dir_index_cache.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    index = _build_index(directory)
    _dir_index_cache[key] = (mtime, index)
    return index


def find_entry(
    directory: Path,
    name: str,
    kind: Literal["dir", "file", "any"] = "any",
    exact_only: bool = False,
) -> Path | None:
    """Find a child entry by name, ignoring case and unicode normal form.

    Exact matches win over normalized matches, so a case-sensitive filesystem
    holding both ``Chat`` and ``chat`` still resolves ``chat`` deterministically.

    Args:
        directory: Parent directory to search
        name: Name to look for
        kind: Restrict the match to directories, files, or either
        exact_only: Only accept an entry spelled exactly like ``name``. Callers
            that try several spellings use this to run an exact pass across all
            of them before falling back to normalized matching, so a derived
            spelling cannot beat the name the caller actually wrote.

    Returns:
        Path to the matching entry, or None if there is no match

    Raises:
        AmbiguousPromptError: If several entries differ only by case or
            unicode normal form and none matches exactly
    """
    from prompteer.exceptions import AmbiguousPromptError

    index = get_dir_index(directory)
    candidates = index.get(normalize_name(name))
    if not candidates:
        return None

    matches = [directory / candidate for candidate in candidates]
    matches = [path for path in matches if _matches_kind(path, kind)]
    if not matches:
        return None

    for path in matches:
        if path.name == name:
            return path

    if exact_only:
        return None

    if len(matches) > 1:
        raise AmbiguousPromptError(
            path=str(directory),
            candidates=[path.name for path in matches],
            message=(
                f"Ambiguous name {name!r} in {directory}: "
                f"{', '.join(repr(path.name) for path in matches)} differ only by "
                "case or unicode normal form, which is not portable across "
                "operating systems. Rename them so they differ by more than case."
            ),
        )

    return matches[0]


def _matches_kind(path: Path, kind: Literal["dir", "file", "any"]) -> bool:
    """Check whether a path satisfies the requested entry kind.

    Args:
        path: Path to check
        kind: Requested kind

    Returns:
        True if the path matches the kind
    """
    if kind == "dir":
        return path.is_dir()
    if kind == "file":
        return path.is_file()
    return True


def iter_dynamic_dirs(directory: Path) -> list[Path]:
    """List the dynamic ``[param]`` subdirectories of a directory.

    Args:
        directory: Directory to scan

    Returns:
        Sorted list of dynamic directories

    Raises:
        AmbiguousPromptError: If the directory holds more than one dynamic
            directory, which would make routing depend on traversal order
    """
    from prompteer.exceptions import AmbiguousPromptError

    index = get_dir_index(directory)
    found: list[Path] = []
    for names in index.values():
        for name in names:
            if is_dynamic_dir(name) and (directory / name).is_dir():
                found.append(directory / name)

    if len(found) > 1:
        found.sort()
        raise AmbiguousPromptError(
            path=str(directory),
            candidates=[path.name for path in found],
            message=(
                f"Multiple dynamic directories in {directory}: "
                f"{', '.join(repr(path.name) for path in found)}. "
                "Routing would depend on filesystem traversal order; keep at "
                "most one [param] directory per level."
            ),
        )

    return found


def to_attribute_name(name: str) -> str:
    """Convert a filesystem name to the camelCase attribute used in stubs.

    Unlike :func:`kebab_to_camel` this always yields a lowercase first
    character, so ``Chat`` and ``chat`` produce the same attribute name.

    Args:
        name: Filesystem name (without extension)

    Returns:
        camelCase attribute name

    Examples:
        >>> to_attribute_name("code-review")
        'codeReview'
        >>> to_attribute_name("Chat")
        'chat'
        >>> to_attribute_name("My-Prompt")
        'myPrompt'
    """
    parts = [part for part in name.split("-") if part]
    if not parts:
        return name

    head = parts[0][:1].lower() + parts[0][1:]
    return head + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def validate_param_value(value: object, param_name: str) -> str:
    """Validate and coerce a dynamic routing parameter value.

    Args:
        value: Value passed by the caller
        param_name: Name of the dynamic parameter, used in error messages

    Returns:
        The value as a path-safe string

    Raises:
        DynamicParameterError: If the value is empty, of an unsupported type,
            or contains path separators
    """
    from enum import Enum

    from prompteer.exceptions import DynamicParameterError

    if isinstance(value, Enum):
        value = value.value

    if value is None:
        raise DynamicParameterError(
            parameter=param_name,
            message=(
                f"Dynamic parameter {param_name!r} cannot be None. "
                "Pass one of the available values, or omit the argument only "
                "if you meant to trigger a TypeError for a missing parameter."
            ),
        )

    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, str):
        text = value
    elif isinstance(value, int):
        text = str(value)
    else:
        raise DynamicParameterError(
            parameter=param_name,
            message=(
                f"Dynamic parameter {param_name!r} must be a str, int, bool or "
                f"Enum, got {type(value).__name__}."
            ),
        )

    if not text.strip():
        raise DynamicParameterError(
            parameter=param_name,
            message=(
                f"Dynamic parameter {param_name!r} cannot be empty or blank "
                f"(got {text!r})."
            ),
        )

    if text != text.strip():
        raise DynamicParameterError(
            parameter=param_name,
            message=(
                f"Dynamic parameter {param_name!r} cannot have leading or "
                f"trailing whitespace (got {text!r})."
            ),
        )

    if text in {os.curdir, os.pardir} or text in {".", ".."}:
        raise DynamicParameterError(
            parameter=param_name,
            message=(
                f"Dynamic parameter {param_name!r} cannot be {text!r}; "
                "relative path references are not allowed."
            ),
        )

    separators = {"/", "\\", os.sep}
    if os.altsep:
        separators.add(os.altsep)
    if any(sep in text for sep in separators):
        raise DynamicParameterError(
            parameter=param_name,
            message=(
                f"Dynamic parameter {param_name!r} cannot contain path "
                f"separators (got {text!r}); it selects a single directory."
            ),
        )

    if "\x00" in text:
        raise DynamicParameterError(
            parameter=param_name,
            message=f"Dynamic parameter {param_name!r} contains a null byte.",
        )

    return text


def format_candidates(names: Iterable[str], limit: int = 8) -> str:
    """Format a list of names for error messages.

    Args:
        names: Names to format
        limit: Maximum number of names to show

    Returns:
        Comma-separated, quoted names with an ellipsis when truncated
    """
    items = sorted(names)
    if not items:
        return "(none)"
    shown = items[:limit]
    text = ", ".join(repr(item) for item in shown)
    if len(items) > limit:
        text += f", … (+{len(items) - limit} more)"
    return text
