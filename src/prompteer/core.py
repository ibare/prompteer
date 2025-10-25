"""
Core Prompteer class for managing prompts.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

from prompteer.exceptions import InvalidPathError
from prompteer.proxy import PromptProxy

if TYPE_CHECKING:
    T = TypeVar("T")


class Prompteer:
    """Main class for managing file-based prompts.

    Provides dot-notation access to prompts stored as markdown files
    in a directory structure.

    Example:
        >>> from pathlib import Path
        >>> # Relative to CWD
        >>> prompts = Prompteer("./prompts")
        >>> # Relative to current file (recommended for packages)
        >>> prompts = Prompteer(Path(__file__).parent / "prompts")
        >>> # Usage
        >>> text = prompts.greeting.casual()
        >>> text = prompts.myPrompt.question.user(name="Alice", age=30)
    """

    def __init__(self, base_path: str | Path, encoding: str = "utf-8") -> None:
        """Initialize Prompteer with a base directory.

        Args:
            base_path: Root directory containing prompt files.
                       Relative paths are resolved from current working directory.
                       For packages, use: Path(__file__).parent / "prompts"
            encoding: File encoding for reading prompts (default: utf-8)

        Raises:
            InvalidPathError: If base_path doesn't exist or isn't a directory
        """
        self._base_path = Path(base_path).resolve()
        self._encoding = encoding

        # Validate base path
        if not self._base_path.exists():
            raise InvalidPathError(
                path=str(base_path),
                message=f"Base path does not exist: {base_path}",
            )

        if not self._base_path.is_dir():
            raise InvalidPathError(
                path=str(base_path),
                message=f"Base path is not a directory: {base_path}",
            )

        # Create internal proxy
        self._proxy = PromptProxy(self._base_path, self._base_path, self._encoding)

    def __getattr__(self, name: str) -> PromptProxy | Callable[..., str]:
        """Get prompt by attribute name.

        Args:
            name: Attribute name in camelCase

        Returns:
            PromptProxy for directories, or callable for files

        Raises:
            PromptNotFoundError: If the prompt doesn't exist
        """
        return getattr(self._proxy, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute.

        Internal attributes (starting with _) can be set,
        but prompt attributes cannot.

        Args:
            name: Attribute name
            value: Attribute value

        Raises:
            AttributeError: If trying to set a non-internal attribute
        """
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(
                f"Cannot set attribute '{name}'. "
                "Prompts are read-only and loaded from the filesystem."
            )

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String representation
        """
        return f"Prompteer(base_path={self._base_path})"

    @property
    def base_path(self) -> Path:
        """Get the base path.

        Returns:
            Base directory path
        """
        return self._base_path

    @property
    def encoding(self) -> str:
        """Get the file encoding.

        Returns:
            File encoding string
        """
        return self._encoding


def create_prompts(base_path: str | Path, encoding: str = "utf-8") -> Any:
    """Create a Prompteer instance with automatic type inference.

    This is a convenience factory function that creates a Prompteer instance
    and returns it with proper type hints when used with generated type stubs.

    Path Resolution:
        Relative paths are resolved relative to the current working directory (CWD).
        For library usage, use absolute paths or resolve relative to your file:

        >>> from pathlib import Path
        >>> from prompteer import create_prompts
        >>>
        >>> # Relative to CWD (works if you run from project root)
        >>> prompts = create_prompts("./prompts")
        >>>
        >>> # Absolute path (always works)
        >>> prompts = create_prompts("/absolute/path/to/prompts")
        >>>
        >>> # Relative to this file's location (recommended for libraries)
        >>> PROMPTS_DIR = Path(__file__).parent / "prompts"
        >>> prompts = create_prompts(PROMPTS_DIR)

    Usage with type stubs:
        >>> # After running: prompteer generate-types ./prompts -o prompts.pyi
        >>> from prompts import create_prompts
        >>> prompts = create_prompts("./prompts")
        >>> prompts.chat.system(role="...", personality="...")  # Full autocomplete!

    Usage without type stubs:
        >>> from prompteer import create_prompts
        >>> prompts = create_prompts("./prompts")
        >>> # Works the same, just without IDE autocomplete

    Args:
        base_path: Root directory containing prompt files.
                   Can be absolute or relative (resolved from CWD).
        encoding: File encoding for reading prompts (default: utf-8)

    Returns:
        Prompteer instance (typed as generated stub class if available)

    Raises:
        InvalidPathError: If base_path doesn't exist or isn't a directory
    """
    return Prompteer(base_path, encoding=encoding)
