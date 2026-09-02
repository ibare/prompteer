"""
Custom exceptions for prompteer.
"""

from __future__ import annotations

from typing import Sequence


class PrompteerError(Exception):
    """Base exception for all prompteer errors."""

    pass


class PromptNotFoundError(PrompteerError, AttributeError):
    """Raised when a prompt file or directory is not found.

    Also inherits from :class:`AttributeError` so that ``hasattr()`` and other
    introspection helpers behave normally on prompt proxies.
    """

    def __init__(
        self,
        path: str,
        message: str | None = None,
        tried: Sequence[str] | None = None,
    ) -> None:
        self.path = path
        self.tried = list(tried or [])
        if message is None:
            message = f"Prompt not found: {path}"
        if self.tried:
            listing = "\n".join(f"  tried: {entry}" for entry in self.tried)
            message = f"{message}\n{listing}"
        super().__init__(message)


class TemplateVariableError(PrompteerError):
    """Raised when a template variable is missing or invalid."""

    def __init__(self, variable: str, message: str | None = None) -> None:
        self.variable = variable
        if message is None:
            message = f"Missing or invalid template variable: {variable}"
        super().__init__(message)


class InvalidPathError(PrompteerError):
    """Raised when a path format is invalid."""

    def __init__(self, path: str, message: str | None = None) -> None:
        self.path = path
        if message is None:
            message = f"Invalid path: {path}"
        super().__init__(message)


class DynamicParameterError(PrompteerError, ValueError):
    """Raised when a dynamic routing parameter value is unusable.

    Covers empty or blank values, unsupported types, and values that contain
    path separators or relative path references. A *missing* parameter raises
    :class:`TypeError` instead, following the usual Python convention for a
    missing argument.
    """

    def __init__(self, parameter: str, message: str | None = None) -> None:
        self.parameter = parameter
        if message is None:
            message = f"Invalid value for dynamic parameter: {parameter}"
        super().__init__(message)


class AmbiguousPromptError(PrompteerError):
    """Raised when a name cannot be resolved to a single filesystem entry.

    Happens when several entries in one directory differ only by case or by
    unicode normal form, or when a directory holds more than one ``[param]``
    subdirectory. Both make resolution depend on the filesystem rather than on
    the prompt tree, so prompteer refuses to guess.
    """

    def __init__(
        self,
        path: str,
        candidates: Sequence[str] | None = None,
        message: str | None = None,
    ) -> None:
        self.path = path
        self.candidates = list(candidates or [])
        if message is None:
            listed = ", ".join(repr(name) for name in self.candidates)
            message = f"Ambiguous prompt path {path}: {listed}"
        super().__init__(message)
