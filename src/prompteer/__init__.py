"""
prompteer - A lightweight file-based prompt manager for LLM workflows.

Simple, scalable, and version-control friendly.
"""

from __future__ import annotations

from prompteer.core import Prompteer, create_prompts
from prompteer.exceptions import (
    InvalidPathError,
    PrompteerError,
    PromptNotFoundError,
    TemplateVariableError,
)

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "Prompteer",
    "create_prompts",
    "PrompteerError",
    "PromptNotFoundError",
    "TemplateVariableError",
    "InvalidPathError",
]
