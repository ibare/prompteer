"""Tests for template module."""

from __future__ import annotations

import pytest

from prompteer.exceptions import TemplateVariableError
from prompteer.template import (
    extract_variables,
    render_template,
    render_template_safe,
    render_template_with_defaults,
    validate_template,
)


class TestExtractVariables:
    """Tests for extract_variables function."""

    def test_single_variable(self) -> None:
        """Test extracting single variable."""
        result = extract_variables("Hello {name}!")
        assert result == {"name"}

    def test_multiple_variables(self) -> None:
        """Test extracting multiple variables."""
        result = extract_variables("Hello {name}, you are {age} years old")
        assert result == {"name", "age"}

    def test_no_variables(self) -> None:
        """Test template without variables."""
        result = extract_variables("No variables here")
        assert result == set()

    def test_duplicate_variables(self) -> None:
        """Test template with duplicate variables."""
        result = extract_variables("{name} and {name} again")
        assert result == {"name"}


class TestRenderTemplate:
    """Tests for render_template function."""

    def test_simple_substitution(self) -> None:
        """Test simple variable substitution."""
        result = render_template("Hello {name}!", {"name": "Alice"})
        assert result == "Hello Alice!"

    def test_multiple_variables(self) -> None:
        """Test multiple variable substitution."""
        result = render_template(
            "Hello {name}, you are {age} years old", {"name": "Bob", "age": 30}
        )
        assert result == "Hello Bob, you are 30 years old"

    def test_missing_variable_raises_error(self) -> None:
        """Test that missing variable raises error."""
        with pytest.raises(TemplateVariableError):
            render_template("Hello {name}!", {})

    def test_extra_variables_ignored(self) -> None:
        """Test that extra variables are ignored."""
        result = render_template("Hello {name}!", {"name": "Alice", "extra": "ignored"})
        assert result == "Hello Alice!"


class TestRenderTemplateSafe:
    """Tests for render_template_safe function."""

    def test_with_default_empty_string(self) -> None:
        """Test safe rendering with default empty string."""
        result = render_template_safe("Hello {name}!", {})
        assert result == "Hello !"

    def test_with_custom_default(self) -> None:
        """Test safe rendering with custom default."""
        result = render_template_safe("Hello {name}!", {}, default="Guest")
        assert result == "Hello Guest!"

    def test_provided_variables_override_default(self) -> None:
        """Test that provided variables override defaults."""
        result = render_template_safe(
            "Hello {name}!", {"name": "Alice"}, default="Guest"
        )
        assert result == "Hello Alice!"


class TestRenderTemplateWithDefaults:
    """Tests for render_template_with_defaults function."""

    def test_with_defaults(self) -> None:
        """Test rendering with per-variable defaults."""
        result = render_template_with_defaults(
            "Hello {name}, age {age}", {"name": "Alice"}, {"age": 0}
        )
        assert result == "Hello Alice, age 0"

    def test_all_variables_provided(self) -> None:
        """Test when all variables are provided."""
        result = render_template_with_defaults(
            "Hello {name}, age {age}", {"name": "Bob", "age": 30}, {"age": 0}
        )
        assert result == "Hello Bob, age 30"

    def test_missing_without_default_raises_error(self) -> None:
        """Test that missing variable without default raises error."""
        with pytest.raises(TemplateVariableError):
            render_template_with_defaults("Hello {name}!", {}, {})


class TestValidateTemplate:
    """Tests for validate_template function."""

    def test_valid_template(self) -> None:
        """Test valid template."""
        is_valid, error = validate_template("Hello {name}!")
        assert is_valid is True
        assert error is None

    def test_unmatched_braces(self) -> None:
        """Test template with unmatched braces."""
        is_valid, error = validate_template("Hello {name!")
        assert is_valid is False
        assert "Unmatched braces" in error

    def test_invalid_variable_syntax(self) -> None:
        """Test template with invalid variable syntax."""
        is_valid, error = validate_template("Hello {na me}!")
        assert is_valid is False
        assert "Invalid variable syntax" in error
