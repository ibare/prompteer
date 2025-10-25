"""
Proxy object for dynamic attribute access in prompteer.

Enables dot-notation access to prompts: prompts.myPrompt.question.user()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from prompteer.exceptions import PromptNotFoundError
from prompteer.path_utils import (
    camel_to_kebab,
    extract_param_name,
    is_dynamic_dir,
    kebab_to_camel,
)
from prompteer.template import render_template


class PromptProxy:
    """Proxy object that enables dynamic attribute access to prompts.

    Attributes are resolved to either:
    - Subdirectories: Return another PromptProxy
    - Files (*.md): Return a callable that renders the prompt
    """

    def __init__(
        self,
        base_path: Path,
        current_path: Path,
        encoding: str = "utf-8",
    ) -> None:
        """Initialize a PromptProxy.

        Args:
            base_path: Root directory of all prompts
            current_path: Current directory path
            encoding: File encoding for reading prompts
        """
        object.__setattr__(self, "_base_path", base_path)
        object.__setattr__(self, "_current_path", current_path)
        object.__setattr__(self, "_encoding", encoding)

    def __getattr__(self, name: str) -> PromptProxy | Callable[..., str]:
        """Get attribute by name, resolving to directory or file.

        Args:
            name: Attribute name in camelCase

        Returns:
            PromptProxy for directories, or callable for files

        Raises:
            PromptNotFoundError: If the path doesn't exist
        """
        # Convert camelCase attribute to kebab-case path
        path_name = camel_to_kebab(name)

        # Check for dynamic directories first
        for item in self._current_path.iterdir():
            if item.is_dir() and is_dynamic_dir(item.name):
                # Found a dynamic directory - return dynamic callable
                return self._create_dynamic_callable(item, name)

        # Try as directory first
        dir_path = self._current_path / path_name
        if dir_path.is_dir():
            return PromptProxy(self._base_path, dir_path, self._encoding)

        # Try as file with .md extension
        file_path = self._current_path / f"{path_name}.md"
        if file_path.is_file():
            # Return a callable that renders the prompt
            return self._create_prompt_callable(file_path)

        # Not found
        relative_path = self._current_path.relative_to(self._base_path)
        full_attr_path = f"{relative_path}/{path_name}" if str(relative_path) != "." else path_name
        raise PromptNotFoundError(
            path=str(full_attr_path),
            message=f"Prompt not found: {full_attr_path} (looking for directory or {path_name}.md)",
        )

    def _create_prompt_callable(self, file_path: Path) -> Callable[..., str]:
        """Create a callable that reads and renders a prompt file.

        Args:
            file_path: Path to the prompt file

        Returns:
            Callable that accepts keyword arguments and returns rendered prompt
        """

        def prompt_renderer(**kwargs: Any) -> str:
            """Read and render the prompt with provided variables.

            Args:
                **kwargs: Variables to substitute in the template

            Returns:
                Rendered prompt string

            Raises:
                TemplateVariableError: If required variables are missing
            """
            # Read the file
            content = file_path.read_text(encoding=self._encoding)

            # Parse metadata and body
            from prompteer.metadata import get_type_default, parse_metadata
            from prompteer.template import render_template_with_defaults

            metadata, body = parse_metadata(content)

            # Build defaults from metadata
            defaults = {}
            for var_name, var_info in metadata.variables.items():
                defaults[var_name] = get_type_default(var_info.type)

            # If no variables provided and no variables in template, return body as-is
            if not kwargs and not metadata.variables:
                from prompteer.template import extract_variables

                template_vars = extract_variables(body)
                if not template_vars:
                    return body

            # Render with variables and defaults
            try:
                return render_template_with_defaults(body, kwargs, defaults)
            except Exception:
                # Fallback: if there's an error and no kwargs, return body
                if not kwargs:
                    return body
                raise

        return prompt_renderer

    def _create_dynamic_callable(self, dynamic_dir: Path, target_name: str) -> Callable[..., str]:
        """Create a callable that handles dynamic parameter routing.

        Args:
            dynamic_dir: Path to the dynamic directory (e.g., [type])
            target_name: Target prompt name (e.g., "user")

        Returns:
            Callable that accepts dynamic parameter and returns rendered prompt
        """
        param_name = extract_param_name(dynamic_dir.name)

        def dynamic_callable(**kwargs: Any) -> str:
            """Route to appropriate prompt based on dynamic parameter.

            Args:
                **kwargs: Must include the dynamic parameter and any template variables

            Returns:
                Rendered prompt string

            Raises:
                TypeError: If required dynamic parameter is missing
                PromptNotFoundError: If no matching prompt found and no default
            """
            # Extract the dynamic parameter value
            param_value = kwargs.pop(param_name, None)
            if param_value is None:
                raise TypeError(f"Missing required parameter: {param_name}")

            # Convert target_name to kebab-case for file lookup
            file_name = camel_to_kebab(target_name)

            # Try to find matching value directory
            value_dir = dynamic_dir / str(param_value)
            if value_dir.exists() and value_dir.is_dir():
                # Look for target file in value directory
                target_file = value_dir / f"{file_name}.md"
                if target_file.exists():
                    return self._render_prompt(target_file, kwargs)

            # Fallback to default.md
            default_file = dynamic_dir / "default.md"
            if default_file.exists():
                return self._render_prompt(default_file, kwargs)

            # No match found
            relative_path = dynamic_dir.relative_to(self._base_path)
            raise PromptNotFoundError(
                path=str(relative_path / file_name),
                message=(
                    f"No prompt found for {param_name}={param_value!r} "
                    f"and no default.md in {relative_path}"
                ),
            )

        return dynamic_callable

    def _render_prompt(self, file_path: Path, kwargs: dict[str, Any]) -> str:
        """Render a prompt file with variables.

        Args:
            file_path: Path to the prompt file
            kwargs: Variables to substitute in the template

        Returns:
            Rendered prompt string
        """
        # Read the file
        content = file_path.read_text(encoding=self._encoding)

        # Parse metadata and body
        from prompteer.metadata import get_type_default, parse_metadata
        from prompteer.template import render_template_with_defaults

        metadata, body = parse_metadata(content)

        # Build defaults from metadata
        defaults = {}
        for var_name, var_info in metadata.variables.items():
            defaults[var_name] = get_type_default(var_info.type)

        # If no variables provided and no variables in template, return body as-is
        if not kwargs and not metadata.variables:
            from prompteer.template import extract_variables

            template_vars = extract_variables(body)
            if not template_vars:
                return body

        # Render with variables and defaults
        try:
            return render_template_with_defaults(body, kwargs, defaults)
        except Exception:
            # Fallback: if there's an error and no kwargs, return body
            if not kwargs:
                return body
            raise

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent setting attributes on proxy objects.

        Args:
            name: Attribute name
            value: Attribute value

        Raises:
            AttributeError: Always, as proxy objects are read-only
        """
        raise AttributeError(
            "Cannot set attributes on PromptProxy. "
            "Prompts are read-only and loaded from the filesystem."
        )

    def __repr__(self) -> str:
        """Return string representation of the proxy.

        Returns:
            String representation
        """
        relative_path = self._current_path.relative_to(self._base_path)
        return f"PromptProxy({relative_path})"
