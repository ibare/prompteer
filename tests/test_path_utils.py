"""Tests for path_utils module."""

from __future__ import annotations

from pathlib import Path

import pytest

from prompteer.path_utils import (
    camel_to_kebab,
    is_valid_attribute_name,
    kebab_to_camel,
    normalize_path_segment,
    resolve_prompt_path,
)


class TestKebabToCamel:
    """Tests for kebab_to_camel function."""

    def test_simple_conversion(self) -> None:
        """Test simple kebab to camel conversion."""
        assert kebab_to_camel("my-prompt") == "myPrompt"

    def test_multiple_words(self) -> None:
        """Test multiple words."""
        assert kebab_to_camel("user-profile-settings") == "userProfileSettings"

    def test_no_hyphens(self) -> None:
        """Test string without hyphens."""
        assert kebab_to_camel("simple") == "simple"

    def test_single_letter_words(self) -> None:
        """Test single letter words."""
        assert kebab_to_camel("a-b-c") == "aBC"


class TestCamelToKebab:
    """Tests for camel_to_kebab function."""

    def test_simple_conversion(self) -> None:
        """Test simple camel to kebab conversion."""
        assert camel_to_kebab("myPrompt") == "my-prompt"

    def test_multiple_words(self) -> None:
        """Test multiple words."""
        assert camel_to_kebab("userProfileSettings") == "user-profile-settings"

    def test_no_uppercase(self) -> None:
        """Test string without uppercase."""
        assert camel_to_kebab("simple") == "simple"

    def test_single_letter_words(self) -> None:
        """Test single letter words."""
        assert camel_to_kebab("aBC") == "a-b-c"


class TestNormalizePathSegment:
    """Tests for normalize_path_segment function."""

    def test_to_camel(self) -> None:
        """Test conversion to camelCase."""
        assert normalize_path_segment("my-prompt", to_camel=True) == "myPrompt"

    def test_to_kebab(self) -> None:
        """Test conversion to kebab-case."""
        assert normalize_path_segment("myPrompt", to_camel=False) == "my-prompt"


class TestResolvePromptPath:
    """Tests for resolve_prompt_path function."""

    def test_single_directory(self) -> None:
        """Test single directory resolution."""
        base = Path("/prompts")
        result = resolve_prompt_path(base, ["myPrompt"], is_file=False)
        assert result == Path("/prompts/my-prompt")

    def test_nested_directories(self) -> None:
        """Test nested directory resolution."""
        base = Path("/prompts")
        result = resolve_prompt_path(base, ["myPrompt", "question"], is_file=False)
        assert result == Path("/prompts/my-prompt/question")

    def test_file_path(self) -> None:
        """Test file path with .md extension."""
        base = Path("/prompts")
        result = resolve_prompt_path(
            base, ["myPrompt", "question", "user"], is_file=True
        )
        assert result == Path("/prompts/my-prompt/question/user.md")


class TestIsValidAttributeName:
    """Tests for is_valid_attribute_name function."""

    def test_valid_names(self) -> None:
        """Test valid attribute names."""
        assert is_valid_attribute_name("myPrompt") is True
        assert is_valid_attribute_name("_private") is True
        assert is_valid_attribute_name("name123") is True

    def test_invalid_names(self) -> None:
        """Test invalid attribute names."""
        assert is_valid_attribute_name("my-prompt") is False
        assert is_valid_attribute_name("123invalid") is False
        assert is_valid_attribute_name("my.prompt") is False
