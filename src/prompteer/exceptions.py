"""
Custom exceptions for prompteer.
"""

from __future__ import annotations


class PrompteerError(Exception):
    """Base exception for all prompteer errors."""

    pass


class PromptNotFoundError(PrompteerError):
    """Raised when a prompt file or directory is not found."""

    def __init__(self, path: str, message: str | None = None) -> None:
        self.path = path
        if message is None:
            message = f"Prompt not found: {path}"
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
