"""Tests for block parser and renderer."""

from __future__ import annotations

import pytest

from prompteer.blocks import (
    BlockSyntaxError,
    ForBlock,
    IfBlock,
    TextBlock,
    parse_blocks,
    render_blocks,
    resolve_value,
)
from prompteer.template import render_template, render_template_with_defaults


class TestParseBlocks:
    """Tests for parse_blocks function."""

    def test_text_only(self) -> None:
        """Test parsing plain text without blocks."""
        blocks = parse_blocks("Hello World")
        assert len(blocks) == 1
        assert isinstance(blocks[0], TextBlock)
        assert blocks[0].content == "Hello World"

    def test_simple_if_block(self) -> None:
        """Test parsing simple if block."""
        blocks = parse_blocks("{#if show}Hello{/if}")
        assert len(blocks) == 1
        assert isinstance(blocks[0], IfBlock)
        assert blocks[0].condition == "show"
        assert blocks[0].negated is False
        assert len(blocks[0].then_blocks) == 1

    def test_if_not_block(self) -> None:
        """Test parsing if not block."""
        blocks = parse_blocks("{#if not hide}Visible{/if}")
        assert len(blocks) == 1
        assert isinstance(blocks[0], IfBlock)
        assert blocks[0].condition == "hide"
        assert blocks[0].negated is True

    def test_if_else_block(self) -> None:
        """Test parsing if-else block."""
        blocks = parse_blocks("{#if show}Yes{#else}No{/if}")
        assert len(blocks) == 1
        assert isinstance(blocks[0], IfBlock)
        assert len(blocks[0].then_blocks) == 1
        assert len(blocks[0].else_blocks) == 1

    def test_if_comparison_equal(self) -> None:
        """Test parsing if block with == operator."""
        blocks = parse_blocks('{#if type == "admin"}Admin{/if}')
        assert len(blocks) == 1
        assert isinstance(blocks[0], IfBlock)
        assert blocks[0].condition == "type"
        assert blocks[0].operator == "=="
        assert blocks[0].compare_value == "admin"

    def test_if_comparison_not_equal(self) -> None:
        """Test parsing if block with != operator."""
        blocks = parse_blocks('{#if status != "active"}Inactive{/if}')
        assert len(blocks) == 1
        assert isinstance(blocks[0], IfBlock)
        assert blocks[0].operator == "!="
        assert blocks[0].compare_value == "active"

    def test_simple_for_block(self) -> None:
        """Test parsing simple for block."""
        blocks = parse_blocks("{#for item in items}{item}{/for}")
        assert len(blocks) == 1
        assert isinstance(blocks[0], ForBlock)
        assert blocks[0].item_name == "item"
        assert blocks[0].collection_name == "items"
        assert blocks[0].index_name is None

    def test_for_with_index(self) -> None:
        """Test parsing for block with index."""
        blocks = parse_blocks("{#for item, idx in items}{idx}. {item}{/for}")
        assert len(blocks) == 1
        assert isinstance(blocks[0], ForBlock)
        assert blocks[0].item_name == "item"
        assert blocks[0].index_name == "idx"
        assert blocks[0].collection_name == "items"

    def test_nested_blocks(self) -> None:
        """Test parsing nested blocks."""
        template = "{#for item in items}{#if item.active}{item.name}{/if}{/for}"
        blocks = parse_blocks(template)
        assert len(blocks) == 1
        assert isinstance(blocks[0], ForBlock)
        assert len(blocks[0].body_blocks) == 1
        assert isinstance(blocks[0].body_blocks[0], IfBlock)

    def test_unclosed_if_raises_error(self) -> None:
        """Test that unclosed if block raises error."""
        with pytest.raises(BlockSyntaxError):
            parse_blocks("{#if show}Hello")

    def test_unclosed_for_raises_error(self) -> None:
        """Test that unclosed for block raises error."""
        with pytest.raises(BlockSyntaxError):
            parse_blocks("{#for x in items}Hello")

    def test_unexpected_closing_tag(self) -> None:
        """Test that unexpected closing tag raises error."""
        with pytest.raises(BlockSyntaxError):
            parse_blocks("{/if}")

    def test_mismatched_closing_tag(self) -> None:
        """Test that mismatched closing tag raises error."""
        with pytest.raises(BlockSyntaxError):
            parse_blocks("{#if show}Hello{/for}")

    def test_else_without_if(self) -> None:
        """Test that else without if raises error."""
        with pytest.raises(BlockSyntaxError):
            parse_blocks("{#else}Hello{/if}")

    def test_invalid_for_syntax(self) -> None:
        """Test that invalid for syntax raises error."""
        with pytest.raises(BlockSyntaxError):
            parse_blocks("{#for item}{/for}")


class TestRenderBlocks:
    """Tests for render_blocks function."""

    def test_render_text(self) -> None:
        """Test rendering plain text."""
        blocks = [TextBlock(content="Hello World")]
        result = render_blocks(blocks, {})
        assert result == "Hello World"

    def test_render_if_true(self) -> None:
        """Test rendering if block with true condition."""
        blocks = parse_blocks("{#if show}Hello{/if}")
        result = render_blocks(blocks, {"show": True})
        assert result == "Hello"

    def test_render_if_false(self) -> None:
        """Test rendering if block with false condition."""
        blocks = parse_blocks("{#if show}Hello{/if}")
        result = render_blocks(blocks, {"show": False})
        assert result == ""

    def test_render_if_else_true(self) -> None:
        """Test rendering if-else with true condition."""
        blocks = parse_blocks("{#if show}Yes{#else}No{/if}")
        result = render_blocks(blocks, {"show": True})
        assert result == "Yes"

    def test_render_if_else_false(self) -> None:
        """Test rendering if-else with false condition."""
        blocks = parse_blocks("{#if show}Yes{#else}No{/if}")
        result = render_blocks(blocks, {"show": False})
        assert result == "No"

    def test_render_if_not(self) -> None:
        """Test rendering if not block."""
        blocks = parse_blocks("{#if not hide}Visible{/if}")
        result = render_blocks(blocks, {"hide": False})
        assert result == "Visible"

        result = render_blocks(blocks, {"hide": True})
        assert result == ""

    def test_render_if_equal(self) -> None:
        """Test rendering if with == comparison."""
        blocks = parse_blocks('{#if role == "admin"}Admin{/if}')
        result = render_blocks(blocks, {"role": "admin"})
        assert result == "Admin"

        result = render_blocks(blocks, {"role": "user"})
        assert result == ""

    def test_render_if_not_equal(self) -> None:
        """Test rendering if with != comparison."""
        blocks = parse_blocks('{#if status != "active"}Inactive{/if}')
        result = render_blocks(blocks, {"status": "pending"})
        assert result == "Inactive"

        result = render_blocks(blocks, {"status": "active"})
        assert result == ""

    def test_render_for_list(self) -> None:
        """Test rendering for block with list."""
        blocks = parse_blocks("{#for x in items}{x}{/for}")
        result = render_blocks(blocks, {"items": ["a", "b", "c"]})
        assert result == "abc"

    def test_render_for_with_separator(self) -> None:
        """Test rendering for block with separator."""
        blocks = parse_blocks("{#for x in items}{x}, {/for}")
        result = render_blocks(blocks, {"items": [1, 2, 3]})
        assert result == "1, 2, 3, "

    def test_render_for_with_index(self) -> None:
        """Test rendering for block with index."""
        blocks = parse_blocks("{#for item, idx in items}{idx}:{item} {/for}")
        result = render_blocks(blocks, {"items": ["a", "b"]})
        assert result == "0:a 1:b "

    def test_render_for_empty_list(self) -> None:
        """Test rendering for block with empty list."""
        blocks = parse_blocks("{#for x in items}{x}{/for}")
        result = render_blocks(blocks, {"items": []})
        assert result == ""

    def test_render_nested_blocks(self) -> None:
        """Test rendering nested blocks."""
        template = "{#for item in items}{#if item.active}{item.name}{/if}{/for}"
        blocks = parse_blocks(template)
        items = [
            {"name": "Alice", "active": True},
            {"name": "Bob", "active": False},
            {"name": "Charlie", "active": True},
        ]
        result = render_blocks(blocks, {"items": items})
        assert result == "AliceCharlie"


class TestResolveValue:
    """Tests for resolve_value function."""

    def test_simple_variable(self) -> None:
        """Test resolving simple variable."""
        result = resolve_value("name", {"name": "Alice"}, None)
        assert result == "Alice"

    def test_dot_notation(self) -> None:
        """Test resolving dot notation."""
        result = resolve_value("user.name", {"user": {"name": "Bob"}}, None)
        assert result == "Bob"

    def test_nested_dot_notation(self) -> None:
        """Test resolving nested dot notation."""
        data = {"user": {"profile": {"name": "Charlie"}}}
        result = resolve_value("user.profile.name", data, None)
        assert result == "Charlie"

    def test_local_vars_override(self) -> None:
        """Test that local vars override global vars."""
        result = resolve_value("item", {"item": "global"}, {"item": "local"})
        assert result == "local"

    def test_missing_variable_raises_error(self) -> None:
        """Test that missing variable raises error."""
        from prompteer.exceptions import TemplateVariableError

        with pytest.raises(TemplateVariableError):
            resolve_value("missing", {}, None)


class TestTemplateWithBlocks:
    """Tests for render_template with block support."""

    def test_simple_template_still_works(self) -> None:
        """Test that simple templates still work."""
        result = render_template("Hello {name}!", {"name": "World"})
        assert result == "Hello World!"

    def test_template_with_if_block(self) -> None:
        """Test template with if block."""
        template = "Hello{#if formal}, Sir{/if}!"
        result = render_template(template, {"formal": True})
        assert result == "Hello, Sir!"

        result = render_template(template, {"formal": False})
        assert result == "Hello!"

    def test_template_with_for_block(self) -> None:
        """Test template with for block."""
        template = "Items: {#for x in items}{x} {/for}"
        result = render_template(template, {"items": ["a", "b", "c"]})
        assert result == "Items: a b c "

    def test_template_with_mixed_content(self) -> None:
        """Test template with blocks and variables."""
        template = "Hello {name}!{#if show_items} Items: {#for x in items}{x}{/for}{/if}"
        result = render_template(
            template, {"name": "User", "show_items": True, "items": [1, 2, 3]}
        )
        assert result == "Hello User! Items: 123"

    def test_template_with_dot_notation(self) -> None:
        """Test template with dot notation variables."""
        template = "{#for user in users}{user.name}: {user.role}\n{/for}"
        users = [
            {"name": "Alice", "role": "Admin"},
            {"name": "Bob", "role": "User"},
        ]
        result = render_template(template, {"users": users})
        assert result == "Alice: Admin\nBob: User\n"


class TestRenderTemplateWithDefaultsAndBlocks:
    """Tests for render_template_with_defaults with block support."""

    def test_with_defaults_and_if_block(self) -> None:
        """Test render_template_with_defaults with if block."""
        template = "{#if show}Hello {name}!{/if}"
        result = render_template_with_defaults(
            template, {"show": True}, {"name": "Guest"}
        )
        assert result == "Hello Guest!"

    def test_with_defaults_and_for_block(self) -> None:
        """Test render_template_with_defaults with for block."""
        template = "Items: {#for item in items}{item.name}{/for}"
        items = [{"name": "A"}, {"name": "B"}]
        result = render_template_with_defaults(template, {"items": items}, {})
        assert result == "Items: AB"


class TestComplexScenarios:
    """Tests for complex real-world scenarios."""

    def test_code_review_with_optional_sections(self) -> None:
        """Test code review prompt with optional sections."""
        template = """Please review this {language} code:

```{language}
{code}
```

{#if show_checklist}
## Checklist
{#for item in checklist}
- [ ] {item}
{/for}
{/if}

{#if focus_areas}
Focus on: {focus_areas}
{/if}"""

        result = render_template(
            template,
            {
                "language": "Python",
                "code": "def hello(): pass",
                "show_checklist": True,
                "checklist": ["Style", "Performance", "Security"],
                "focus_areas": "error handling",
            },
        )

        assert "Python" in result
        assert "def hello(): pass" in result
        assert "- [ ] Style" in result
        assert "- [ ] Performance" in result
        assert "- [ ] Security" in result
        assert "Focus on: error handling" in result

    def test_multilingual_system_prompt(self) -> None:
        """Test multilingual system prompt."""
        template = """You are a multilingual assistant.

{#if tone == "formal"}
Please maintain a professional and formal tone.
{#else}
Feel free to be casual and friendly.
{/if}

Supported languages:
{#for lang in languages}
- {lang.name} ({lang.code})
{/for}"""

        result = render_template(
            template,
            {
                "tone": "formal",
                "languages": [
                    {"name": "English", "code": "en"},
                    {"name": "Korean", "code": "ko"},
                ],
            },
        )

        assert "professional and formal" in result
        assert "- English (en)" in result
        assert "- Korean (ko)" in result

    def test_conditional_examples(self) -> None:
        """Test prompt with conditional examples."""
        template = """{#if include_examples}
## Examples
{#for example in examples}
Input: {example.input}
Output: {example.output}

{/for}
{/if}
Now process: {input}"""

        # With examples
        result = render_template(
            template,
            {
                "include_examples": True,
                "examples": [
                    {"input": "hello", "output": "HELLO"},
                    {"input": "world", "output": "WORLD"},
                ],
                "input": "test",
            },
        )

        assert "## Examples" in result
        assert "Input: hello" in result
        assert "Output: HELLO" in result
        assert "Now process: test" in result

        # Without examples
        result = render_template(
            template,
            {
                "include_examples": False,
                "examples": [],
                "input": "test",
            },
        )

        assert "## Examples" not in result
        assert "Now process: test" in result
