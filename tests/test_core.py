"""Tests for core module."""

from __future__ import annotations

from pathlib import Path

import pytest

from prompteer import Prompteer
from prompteer.exceptions import InvalidPathError, PromptNotFoundError


class TestPrompterInit:
    """Tests for Prompteer initialization."""

    def test_valid_directory(self, tmp_path: Path) -> None:
        """Test initialization with valid directory."""
        prompts = Prompteer(str(tmp_path))
        assert prompts.base_path == tmp_path.resolve()
        assert prompts.encoding == "utf-8"

    def test_custom_encoding(self, tmp_path: Path) -> None:
        """Test custom encoding."""
        prompts = Prompteer(str(tmp_path), encoding="latin-1")
        assert prompts.encoding == "latin-1"

    def test_nonexistent_directory(self) -> None:
        """Test initialization with non-existent directory."""
        with pytest.raises(InvalidPathError):
            Prompteer("/nonexistent/path")

    def test_file_not_directory(self, tmp_path: Path) -> None:
        """Test initialization with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(InvalidPathError):
            Prompteer(str(file_path))


class TestPromptAccess:
    """Tests for prompt access."""

    def test_simple_prompt(self) -> None:
        """Test accessing simple prompt."""
        prompts = Prompteer("tests/fixtures/prompts")
        result = prompts.simple()
        assert result == "Hello, World!\n"

    def test_prompt_with_variables(self) -> None:
        """Test prompt with variables."""
        prompts = Prompteer("tests/fixtures/prompts")
        result = prompts.withVariables(name="Alice", age=30)
        assert result == "Hello Alice! You are 30 years old.\n"

    def test_prompt_with_metadata(self) -> None:
        """Test prompt with metadata and defaults."""
        prompts = Prompteer("tests/fixtures/prompts")

        # Test with all variables
        result = prompts.withMetadata(name="Bob", age=25, height=180.5)
        assert "Name: Bob" in result
        assert "Age: 25" in result
        assert "Height: 180.5" in result

        # Test with defaults
        result = prompts.withMetadata()
        assert "Name: " in result
        assert "Age: 0" in result
        assert "Height: 0.0" in result

    def test_nested_prompt(self) -> None:
        """Test accessing nested prompt."""
        prompts = Prompteer("tests/fixtures/prompts")
        result = prompts.nested.deep.prompt()
        assert result == "Nested prompt\n"

    def test_nonexistent_prompt(self) -> None:
        """Test accessing non-existent prompt."""
        prompts = Prompteer("tests/fixtures/prompts")
        with pytest.raises(PromptNotFoundError):
            prompts.nonexistent()


class TestPrompteerReadOnly:
    """Tests for read-only behavior."""

    def test_cannot_set_prompt_attributes(self, tmp_path: Path) -> None:
        """Test that prompt attributes cannot be set."""
        prompts = Prompteer(str(tmp_path))
        with pytest.raises(AttributeError):
            prompts.newprompt = "value"  # type: ignore

    def test_can_access_internal_attributes(self, tmp_path: Path) -> None:
        """Test that internal attributes are accessible."""
        prompts = Prompteer(str(tmp_path))
        assert prompts.base_path == tmp_path.resolve()
        assert prompts.encoding == "utf-8"


class TestPrompteerRepr:
    """Tests for Prompteer string representation."""

    def test_repr(self, tmp_path: Path) -> None:
        """Test string representation."""
        prompts = Prompteer(str(tmp_path))
        assert "Prompteer" in repr(prompts)
        assert str(tmp_path.resolve()) in repr(prompts)
