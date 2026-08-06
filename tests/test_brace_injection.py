"""주입값 안의 중괄호가 변수로 오인되지 않는지 검증한다.

리포트 수용 기준 + 블록/점표기/이스케이프 확장 케이스.
"""

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


class TestAcceptanceCriteria:
    """리포트가 명시한 수용 기준."""

    def test_braces_in_value_are_literal(self) -> None:
        result = render_template_with_defaults("A: {a}", {"a": "x {foo} y"}, {})
        assert result == "A: x {foo} y"

    def test_value_containing_only_a_placeholder(self) -> None:
        result = render_template_with_defaults("A: {a}", {"a": "{b}"}, {})
        assert result == "A: {b}"

    def test_genuinely_missing_variable_still_raises(self) -> None:
        """회귀 방지선: 검출력은 그대로여야 한다."""
        with pytest.raises(TemplateVariableError) as exc:
            render_template_with_defaults("A: {a} B: {b}", {"a": "x"}, {})
        assert "b" in str(exc.value)

    def test_report_original_example(self) -> None:
        result = render_template_with_defaults(
            "A: {a}", {"a": "width {width} 지정"}, {}
        )
        assert result == "A: width {width} 지정"


class TestRealWorldInputs:
    """리포트가 예시로 든 실제 입력들."""

    def test_react_children(self) -> None:
        result = render_template("설명: {body}", {"body": "React {children} 사용법"})
        assert result == "설명: React {children} 사용법"

    def test_latex_fraction(self) -> None:
        result = render_template("수식: {expr}", {"expr": r"$\frac{a}{b}$"})
        assert result == r"수식: $\frac{a}{b}$"

    def test_json_example_in_value(self) -> None:
        result = render_template("스키마: {s}", {"s": '{"key": "value"}'})
        assert result == '스키마: {"key": "value"}'


class TestRenderTemplatePlain:
    """render_template 도 같은 보장을 갖는다."""

    def test_braces_in_value(self) -> None:
        assert render_template("A: {a}", {"a": "x {foo} y"}) == "A: x {foo} y"

    def test_missing_still_raises(self) -> None:
        with pytest.raises(TemplateVariableError):
            render_template("A: {a} B: {b}", {"a": "x"})


class TestBlockPaths:
    """블록 경로에서도 주입값이 재해석되지 않는다."""

    def test_for_loop_item_value(self) -> None:
        result = render_template(
            "{#for x in items}[{x}]{/for}", {"items": ["a {foo} b", "c"]}
        )
        assert result == "[a {foo} b][c]"

    def test_if_block_value(self) -> None:
        result = render_template("{#if show}{a}{/if}", {"show": True, "a": "v {foo} w"})
        assert result == "v {foo} w"

    def test_variable_outside_block_still_substituted(self) -> None:
        """블록 밖 변수도 같은 패스에서 치환된다."""
        result = render_template(
            "HEAD {a} {#if s}IN {b}{/if} TAIL {c}",
            {"a": "A", "b": "B", "c": "C", "s": True},
        )
        assert result == "HEAD A IN B TAIL C"

    def test_missing_inside_block_still_raises(self) -> None:
        with pytest.raises(TemplateVariableError):
            render_template("{#if s}{nope}{/if}", {"s": True})

    def test_missing_outside_block_still_raises(self) -> None:
        with pytest.raises(TemplateVariableError):
            render_template("{nope} {#if s}x{/if}", {"s": True})

    def test_optional_condition_variable_is_tolerated(self) -> None:
        """조건 변수 누락은 기존대로 falsy 취급 (에러 아님)."""
        assert render_template("{#if never}X{/if}", {}) == ""


class TestDotNotation:
    def test_dot_value_with_braces(self) -> None:
        result = render_template("{u.name}", {"u": {"name": "n {foo}"}})
        assert result == "n {foo}"

    def test_dot_notation_in_safe(self) -> None:
        """render_template_safe 도 점 표기를 치환한다."""
        assert render_template_safe("{u.name}", {"u": {"name": "Bob"}}) == "Bob"


class TestRenderTemplateSafeDeterminism:
    def test_injected_value_not_rescanned(self) -> None:
        """먼저 주입된 값 안의 {다른변수} 가 치환되지 않는다."""
        result = render_template_safe("{a} {b}", {"a": "AAA {b}", "b": "BBB"})
        assert result == "AAA {b} BBB"

    def test_missing_uses_default(self) -> None:
        assert (
            render_template_safe("Hello {name}!", {}, default="Guest") == "Hello Guest!"
        )


class TestEscape:
    def test_escaped_literal(self) -> None:
        assert render_template("{{foo}}", {}) == "{foo}"

    def test_escaped_literal_alongside_variable(self) -> None:
        result = render_template("{{children}} 와 {a}", {"a": "값"})
        assert result == "{children} 와 값"

    def test_escaped_is_not_extracted_as_variable(self) -> None:
        assert extract_variables("{{foo}}") == set()

    def test_escaped_does_not_count_as_missing(self) -> None:
        assert render_template_with_defaults("{{foo}}", {}, {}) == "{foo}"

    def test_unescaped_output_is_not_reinterpreted(self) -> None:
        """{{a}} 가 {a} 로 풀린 뒤 다시 변수로 해석되면 안 된다."""
        assert render_template("{{a}}", {"a": "VALUE"}) == "{a}"

    def test_validate_accepts_escape(self) -> None:
        assert validate_template("{{foo}}") == (True, None)


class TestNoRescanInvariant:
    def test_nested_injection_depth_two(self) -> None:
        """값 안의 값 안의 중괄호까지 안전하다."""
        result = render_template("{outer}", {"outer": "L1 {mid} L1", "mid": "unused"})
        assert result == "L1 {mid} L1"

    def test_value_with_unbalanced_brace(self) -> None:
        assert render_template("{a}", {"a": "unbalanced {"}) == "unbalanced {"
