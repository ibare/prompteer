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


class TestNormalizedMatching:
    """Case- and unicode-insensitive entry lookup."""

    def test_normalize_name_folds_case(self) -> None:
        """Case folding makes differently cased spellings compare equal."""
        from prompteer.path_utils import normalize_name

        assert normalize_name("Chat") == normalize_name("chat")
        assert normalize_name("CODE-REVIEW") == normalize_name("code-review")

    def test_normalize_name_composes_unicode(self) -> None:
        """NFD and NFC spellings of the same text compare equal."""
        import unicodedata

        from prompteer.path_utils import normalize_name

        assert normalize_name(unicodedata.normalize("NFD", "번역")) == normalize_name(
            unicodedata.normalize("NFC", "번역")
        )

    def test_find_entry_prefers_exact_match(self, tmp_path, monkeypatch) -> None:
        """An exact spelling wins even when a case twin exists.

        The listing is stubbed so the case behaves the same on a
        case-insensitive filesystem, where the collision cannot be created.
        """
        from prompteer import path_utils

        (tmp_path / "chat").mkdir()
        monkeypatch.setattr(
            path_utils, "get_dir_index", lambda directory: {"chat": ["Chat", "chat"]}
        )
        monkeypatch.setattr(path_utils, "_matches_kind", lambda path, kind: True)

        assert path_utils.find_entry(tmp_path, "chat", "dir").name == "chat"
        assert path_utils.find_entry(tmp_path, "Chat", "dir").name == "Chat"

    def test_find_entry_reports_ambiguity(self, tmp_path, monkeypatch) -> None:
        """With no exact spelling, prompteer refuses to guess."""
        import pytest

        from prompteer import path_utils
        from prompteer.exceptions import AmbiguousPromptError

        monkeypatch.setattr(
            path_utils, "get_dir_index", lambda directory: {"chat": ["Chat", "cHaT"]}
        )
        monkeypatch.setattr(path_utils, "_matches_kind", lambda path, kind: True)

        with pytest.raises(AmbiguousPromptError, match="differ only by"):
            path_utils.find_entry(tmp_path, "chat", "dir")

    def test_find_entry_returns_none_when_absent(self, tmp_path) -> None:
        """A name that matches nothing yields None rather than an error."""
        from prompteer.path_utils import find_entry

        (tmp_path / "chat").mkdir()

        assert find_entry(tmp_path, "translation", "dir") is None


class TestToAttributeName:
    """Filesystem name to stub attribute name conversion."""

    def test_kebab_becomes_camel(self) -> None:
        """The documented convention is preserved."""
        from prompteer.path_utils import to_attribute_name

        assert to_attribute_name("code-review") == "codeReview"

    def test_leading_capital_is_lowered(self) -> None:
        """Stub attributes always start lowercase, whatever the disk says."""
        from prompteer.path_utils import to_attribute_name

        assert to_attribute_name("Chat") == "chat"
        assert to_attribute_name("My-Prompt") == "myPrompt"


class TestValidateParamValue:
    """Routing parameter value validation."""

    def test_accepts_plain_values(self) -> None:
        """Strings, integers and booleans map onto directory names."""
        from prompteer.path_utils import validate_param_value

        assert validate_param_value("basic", "type") == "basic"
        assert validate_param_value(1, "version") == "1"
        assert validate_param_value(True, "flag") == "true"

    def test_rejects_empty_and_traversal(self) -> None:
        """Empty values and path references are refused."""
        import pytest

        from prompteer.exceptions import DynamicParameterError
        from prompteer.path_utils import validate_param_value

        for bad in ["", "   ", "..", "a/b", "a\\b"]:
            with pytest.raises(DynamicParameterError):
                validate_param_value(bad, "type")
