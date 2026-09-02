"""
Tests for recursive dynamic routing.

Covers nested [param] directories, static directories sitting between them,
and the default/ fallback subtree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prompteer import create_prompts
from prompteer.exceptions import AmbiguousPromptError, PromptNotFoundError


def write(root: Path, relative: str, content: str) -> None:
    """Create a prompt file, making parent directories as needed."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def nested_dir(tmp_path: Path) -> Path:
    """Prompt tree with two dynamic levels and intermediate static directories."""
    prompts = tmp_path / "prompts"

    write(prompts, "q/[type]/basic/[lang]/ko/user.md", "basic ko user")
    write(prompts, "q/[type]/basic/[lang]/en/user.md", "basic en user")
    write(prompts, "q/[type]/basic/extra/user.md", "basic extra user")
    write(prompts, "q/[type]/basic/extra/system.md", "basic extra system")
    write(prompts, "q/[type]/advanced/user.md", "advanced user")
    write(prompts, "q/[type]/advanced/extra/user.md", "advanced extra user")

    return prompts


class TestNestedDynamicRouting:
    """Recursive [param] resolution."""

    def test_two_dynamic_levels(self, nested_dir: Path) -> None:
        """Two nested [param] directories both consume their parameter."""
        prompts = create_prompts(str(nested_dir))

        assert prompts.q.user(type="basic", lang="ko") == "basic ko user"
        assert prompts.q.user(type="basic", lang="en") == "basic en user"

    def test_intermediate_static_directory(self, nested_dir: Path) -> None:
        """A static directory may sit between the parameter and the prompt."""
        prompts = create_prompts(str(nested_dir))

        assert prompts.q.extra.user(type="basic") == "basic extra user"
        assert prompts.q.extra.system(type="basic") == "basic extra system"
        assert prompts.q.extra.user(type="advanced") == "advanced extra user"

    def test_missing_inner_parameter(self, nested_dir: Path) -> None:
        """The inner parameter is required once the route reaches its level."""
        prompts = create_prompts(str(nested_dir))

        with pytest.raises(TypeError, match="Missing required parameter: lang"):
            prompts.q.user(type="basic")

    def test_inner_value_not_found_does_not_propagate(self, tmp_path: Path) -> None:
        """An inner failure is final and does not fall back to an outer default."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/[lang]/ko/user.md", "basic ko user")
        write(prompts_dir, "q/[type]/default.md", "outer default")

        prompts = create_prompts(str(prompts_dir))

        with pytest.raises(PromptNotFoundError) as error:
            prompts.q.user(type="basic", lang="fr")

        assert "lang='fr'" in str(error.value)
        assert "outer default" not in str(error.value)

    def test_static_wins_when_parameter_absent(self, tmp_path: Path) -> None:
        """A static prompt is preferred when no routing parameter is supplied."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "dynamic user")
        write(prompts_dir, "q/common.md", "static common")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.common() == "static common"

    def test_supplied_parameter_prefers_dynamic_route(self, tmp_path: Path) -> None:
        """Passing a parameter selects the dynamic route over a static twin."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "generic basic user")
        write(prompts_dir, "q/[type]/basic/[lang]/ko/user.md", "korean basic user")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="basic") == "generic basic user"
        assert prompts.q.user(type="basic", lang="ko") == "korean basic user"

    def test_multiple_dynamic_dirs_rejected(self, tmp_path: Path) -> None:
        """Two [param] directories at one level would depend on traversal order."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "by type")
        write(prompts_dir, "q/[lang]/ko/user.md", "by lang")

        prompts = create_prompts(str(prompts_dir))

        with pytest.raises(AmbiguousPromptError, match="Multiple dynamic directories"):
            prompts.q.user(type="basic")

    def test_unused_parameter_reports_the_route_failure(self, tmp_path: Path) -> None:
        """A routing parameter that no route consumed is an error, not a no-op.

        The static prompt matched, but the caller asked for a route that does
        not lead to it, so the routing failure is the useful message.
        """
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/common.md", "static common")
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.common() == "static common"

        with pytest.raises(PromptNotFoundError) as error:
            prompts.q.common(type="basic")

        assert "type='basic'" in str(error.value)

    def test_unknown_keyword_is_left_to_the_template(self, tmp_path: Path) -> None:
        """A keyword that names no [param] anywhere is an ordinary variable."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "Hello {name}")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="basic", name="Alice") == "Hello Alice"


class TestDefaultDirectoryFallback:
    """The default/ fallback subtree."""

    @pytest.fixture
    def with_default_dir(self, tmp_path: Path) -> Path:
        """Tree whose dynamic level has both a default/ subtree and default.md."""
        prompts = tmp_path / "prompts"
        write(prompts, "q/[type]/basic/user.md", "basic user")
        write(prompts, "q/[type]/basic/extra/system.md", "basic extra system")
        write(prompts, "q/[type]/default/user.md", "default user")
        write(prompts, "q/[type]/default/extra/system.md", "default extra system")
        return prompts

    def test_default_dir_covers_single_segment(self, with_default_dir: Path) -> None:
        """An unmatched value falls back into default/."""
        prompts = create_prompts(str(with_default_dir))

        assert prompts.q.user(type="expert") == "default user"

    def test_default_dir_covers_nested_path(self, with_default_dir: Path) -> None:
        """default/ can stand in for a whole subtree, unlike default.md."""
        prompts = create_prompts(str(with_default_dir))

        assert prompts.q.extra.system(type="expert") == "default extra system"

    def test_default_dir_wins_over_default_file(self, tmp_path: Path) -> None:
        """A named match in default/ beats the catch-all default.md."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")
        write(prompts_dir, "q/[type]/default/user.md", "default subtree user")
        write(prompts_dir, "q/[type]/default.md", "default file")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="expert") == "default subtree user"

    def test_default_file_still_works_for_single_segment(self, tmp_path: Path) -> None:
        """Trees written before default/ existed keep their behaviour."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")
        write(prompts_dir, "q/[type]/default.md", "default file")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="expert") == "default file"

    def test_default_file_skipped_for_nested_path(self, tmp_path: Path) -> None:
        """A single file cannot stand in for extra/user versus extra/system."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/extra/user.md", "basic extra user")
        write(prompts_dir, "q/[type]/basic/extra/system.md", "basic extra system")
        write(prompts_dir, "q/[type]/default.md", "default file")

        prompts = create_prompts(str(prompts_dir))

        with pytest.raises(PromptNotFoundError) as error:
            prompts.q.extra.user(type="expert")

        assert "skipped: path has 2 segments" in str(error.value)

    def test_error_lists_attempted_paths(self, tmp_path: Path) -> None:
        """Failures name every candidate that was tried."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/extra/user.md", "basic extra user")

        prompts = create_prompts(str(prompts_dir))

        with pytest.raises(PromptNotFoundError) as error:
            prompts.q.extra.user(type="expert")

        message = str(error.value)
        assert "q/[type]/expert/extra/user.md" in message
        assert "q/[type]/default/extra/user.md" in message

    def test_default_dir_may_nest_further(self, tmp_path: Path) -> None:
        """default/ is an ordinary subtree and may hold its own [param]."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")
        write(prompts_dir, "q/[type]/default/[lang]/ko/user.md", "default ko user")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="expert", lang="ko") == "default ko user"


class TestDeferredProxyBehaviour:
    """Attribute-access semantics of the deferred proxy."""

    def test_typo_fails_fast(self, nested_dir: Path) -> None:
        """A name that exists nowhere reachable raises at attribute access."""
        prompts = create_prompts(str(nested_dir))

        with pytest.raises(PromptNotFoundError):
            prompts.q.nosuchname

    def test_hasattr_returns_false(self, nested_dir: Path) -> None:
        """PromptNotFoundError is an AttributeError, so hasattr works."""
        prompts = create_prompts(str(nested_dir))

        assert hasattr(prompts.q, "extra") is True
        assert hasattr(prompts.q, "nosuchname") is False

    def test_private_names_are_not_routed(self, nested_dir: Path) -> None:
        """Introspection helpers must not be captured by dynamic routing."""
        prompts = create_prompts(str(nested_dir))

        with pytest.raises(AttributeError):
            prompts.q._repr_html_

    def test_deferred_proxy_is_read_only(self, nested_dir: Path) -> None:
        """Deferred proxies reject attribute assignment like PromptProxy."""
        prompts = create_prompts(str(nested_dir))
        deferred = prompts.q.extra

        with pytest.raises(AttributeError, match="read-only"):
            deferred.something = "x"


class TestRoutingValuesInTemplates:
    """Routing parameters are also available as template variables."""

    def test_value_is_substituted(self, tmp_path: Path) -> None:
        """A prompt can mention the route it was selected by."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "등급: {type}")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="basic") == "등급: basic"

    def test_every_nested_level_is_available(self, tmp_path: Path) -> None:
        """Each level contributes its own value."""
        prompts_dir = tmp_path / "prompts"
        write(
            prompts_dir,
            "support/[tier]/pro/[lang]/ko/reply.md",
            "{customer} ({tier}/{lang})",
        )

        prompts = create_prompts(str(prompts_dir))
        result = prompts.support.reply(tier="pro", lang="ko", customer="Alice")

        assert result == "Alice (pro/ko)"

    def test_caller_value_is_used_verbatim(self, tmp_path: Path) -> None:
        """The value is what the caller passed, not the directory it matched.

        Matching ignores case, so the two can differ; substituting the caller's
        own value keeps the result predictable.
        """
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "등급: {type}")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="BASIC") == "등급: BASIC"

    def test_declared_variable_receives_the_value(self, tmp_path: Path) -> None:
        """A frontmatter declaration of the same name is filled by the route.

        It used to be filled with the type default, an empty string.
        """
        prompts_dir = tmp_path / "prompts"
        write(
            prompts_dir,
            "q/[type]/basic/user.md",
            "---\ndescription: x\ntype: Routing tier\n---\n등급: {type}",
        )

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="basic") == "등급: basic"

    def test_value_available_in_default_file(self, tmp_path: Path) -> None:
        """The fallback file can name the value that failed to match."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")
        write(prompts_dir, "q/[type]/default.md", "{type} 등급은 지원하지 않습니다")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="expert") == "expert 등급은 지원하지 않습니다"

    def test_value_available_in_default_subtree(self, tmp_path: Path) -> None:
        """The default/ subtree gets the value too."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "basic user")
        write(prompts_dir, "q/[type]/default/user.md", "unknown tier: {type}")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="expert") == "unknown tier: expert"

    def test_separately_named_variable_still_works(self, tmp_path: Path) -> None:
        """The pre-0.5.0 workaround of passing a differently named copy."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "{type_label} / {type}")

        prompts = create_prompts(str(prompts_dir))
        result = prompts.q.user(type="basic", type_label="Basic tier")

        assert result == "Basic tier / basic"

    def test_body_is_returned_when_called_without_arguments(
        self, tmp_path: Path
    ) -> None:
        """Injecting routing values must not change the no-argument fallback."""
        prompts_dir = tmp_path / "prompts"
        write(prompts_dir, "q/[type]/basic/user.md", "Hello {name}")

        prompts = create_prompts(str(prompts_dir))

        assert prompts.q.user(type="basic") == "Hello {name}"
