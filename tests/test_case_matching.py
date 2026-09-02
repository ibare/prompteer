"""
Tests for case- and unicode-insensitive name matching.

Matching is performed by prompteer rather than delegated to the filesystem, so
the same prompt tree resolves identically on macOS, Linux and Windows.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from prompteer import create_prompts
from prompteer.exceptions import AmbiguousPromptError, PromptNotFoundError
from prompteer.path_utils import clear_path_cache


def write(root: Path, relative: str, content: str) -> None:
    """Create a prompt file, making parent directories as needed."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def filesystem_is_case_sensitive(tmp_path: Path) -> bool:
    """Detect whether the filesystem under tmp_path distinguishes case."""
    probe = tmp_path / "_CaseProbe"
    probe.mkdir()
    return not (tmp_path / "_caseprobe").exists()


class TestCaseInsensitiveMatching:
    """Names resolve regardless of the case used on disk or in code."""

    def test_uppercase_directory_and_file(self, tmp_path: Path) -> None:
        """A capitalised tree is reachable through the camelCase API."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "Chat/System.md", "chat system")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.chat.system() == "chat system"

    def test_uppercase_kebab_names(self, tmp_path: Path) -> None:
        """Kebab-case conversion happens before the case-insensitive match."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "CODE-REVIEW/Review-Request.md", "review request")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.codeReview.reviewRequest() == "review request"

    def test_camel_case_directory_on_disk(self, tmp_path: Path) -> None:
        """A directory written in camelCase is reachable too."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "myPrompt/user.md", "my prompt user")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.myPrompt.user() == "my prompt user"

    def test_attribute_case_does_not_matter(self, tmp_path: Path) -> None:
        """The API accepts a different case than the one on disk."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "chat/system.md", "chat system")

        prompts = create_prompts(str(prompts_dir))

        assert getattr(prompts, "Chat").system() == "chat system"

    def test_dynamic_value_case_does_not_matter(self, tmp_path: Path) -> None:
        """Routing values match value directories case-insensitively."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="basic") == "basic user"
        assert prompts.q.user(type="BASIC") == "basic user"
        assert prompts.q.user(type="Basic") == "basic user"

    def test_default_file_case_does_not_matter(self, tmp_path: Path) -> None:
        """The fallback file is found even when written as Default.md."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")
        write(prompts_dir, "q/[type]/Default.md", "default file")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="expert") == "default file"


class TestUnicodeNormalization:
    """NFD (macOS) and NFC (Linux) spellings of the same name must match."""

    def test_decomposed_directory_matches_composed_attribute(
        self, tmp_path: Path
    ) -> None:
        """A directory stored as NFD is reachable through its NFC name."""
        prompts_dir = tmp_path / "prompts"
        decomposed = unicodedata.normalize("NFD", "번역")
        write(prompts_dir, f"{decomposed}/user.md", "번역 프롬프트")

        prompts = create_prompts(str(prompts_dir))
        composed = unicodedata.normalize("NFC", "번역")

        assert getattr(prompts, composed).user() == "번역 프롬프트"

    def test_composed_file_matches_decomposed_attribute(self, tmp_path: Path) -> None:
        """The reverse direction resolves as well."""
        prompts_dir = tmp_path / "prompts"
        composed = unicodedata.normalize("NFC", "요약")
        write(prompts_dir, f"chat/{composed}.md", "요약 프롬프트")

        prompts = create_prompts(str(prompts_dir))
        decomposed = unicodedata.normalize("NFD", "요약")

        assert getattr(prompts.chat, decomposed)() == "요약 프롬프트"


class TestAmbiguousNames:
    """Names that differ only by case are refused rather than guessed."""

    def test_case_only_collision_is_reported(self, tmp_path: Path) -> None:
        """Two directories differing only by case cannot resolve portably."""
        if not filesystem_is_case_sensitive(tmp_path):
            pytest.skip("filesystem is case-insensitive; cannot create the collision")

        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "Chat/system.md", "upper")
        write(prompts_dir, "chat/system.md", "lower")
        clear_path_cache()

        prompts = create_prompts(str(prompts_dir))

        with pytest.raises(AmbiguousPromptError, match="differ only by"):
            getattr(prompts, "CHAT")

    def test_exact_match_wins_over_collision(self, tmp_path: Path) -> None:
        """An exact spelling resolves even when a case twin exists."""
        if not filesystem_is_case_sensitive(tmp_path):
            pytest.skip("filesystem is case-insensitive; cannot create the collision")

        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "Chat/system.md", "upper")
        write(prompts_dir, "chat/system.md", "lower")
        clear_path_cache()

        prompts = create_prompts(str(prompts_dir))

        assert prompts.chat.system() == "lower"
        assert getattr(prompts, "Chat").system() == "upper"


class TestUnmatchedNames:
    """Names that match nothing still fail clearly."""

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        """An unrelated name is not silently matched by normalization."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "chat/system.md", "chat system")

        prompts = create_prompts(str(prompts_dir))

        with pytest.raises(PromptNotFoundError):
            prompts.chats
