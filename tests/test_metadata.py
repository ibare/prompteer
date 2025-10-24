"""Tests for metadata module."""

from __future__ import annotations

import pytest

from prompteer.metadata import (
    extract_frontmatter,
    get_type_default,
    parse_metadata,
    parse_variable_key,
)


class TestParseVariableKey:
    """Tests for parse_variable_key function."""

    def test_plain_variable(self) -> None:
        """Test parsing plain variable name."""
        name, var_type = parse_variable_key("name")
        assert name == "name"
        assert var_type == "str"

    def test_variable_with_type(self) -> None:
        """Test parsing variable with type."""
        name, var_type = parse_variable_key("age(int)")
        assert name == "age"
        assert var_type == "int"

    def test_different_types(self) -> None:
        """Test parsing different types."""
        assert parse_variable_key("height(float)") == ("height", "float")
        assert parse_variable_key("active(bool)") == ("active", "bool")


class TestExtractFrontmatter:
    """Tests for extract_frontmatter function."""

    def test_with_frontmatter(self) -> None:
        """Test extracting valid frontmatter."""
        content = """---
description: Test
name: User name
---
Body content"""
        frontmatter, body = extract_frontmatter(content)
        assert frontmatter == {"description": "Test", "name": "User name"}
        assert body == "Body content"

    def test_without_frontmatter(self) -> None:
        """Test content without frontmatter."""
        content = "Just plain content"
        frontmatter, body = extract_frontmatter(content)
        assert frontmatter is None
        assert body == "Just plain content"

    def test_invalid_yaml(self) -> None:
        """Test invalid YAML in frontmatter."""
        content = """---
invalid: [yaml
---
Body"""
        frontmatter, body = extract_frontmatter(content)
        assert frontmatter is None
        assert body == content


class TestParseMetadata:
    """Tests for parse_metadata function."""

    def test_with_metadata(self) -> None:
        """Test parsing metadata."""
        content = """---
description: User profile
name: User name
age(int): User age
---
Hello {name}"""
        metadata, body = parse_metadata(content)

        assert metadata.description == "User profile"
        assert len(metadata.variables) == 2
        assert "name" in metadata.variables
        assert "age" in metadata.variables
        assert metadata.variables["name"].type == "str"
        assert metadata.variables["age"].type == "int"
        assert body == "Hello {name}"

    def test_without_metadata(self) -> None:
        """Test parsing without metadata."""
        content = "Just a prompt"
        metadata, body = parse_metadata(content)

        assert metadata.description is None
        assert len(metadata.variables) == 0
        assert body == "Just a prompt"

    def test_description_only(self) -> None:
        """Test metadata with only description."""
        content = """---
description: Simple prompt
---
Content"""
        metadata, body = parse_metadata(content)

        assert metadata.description == "Simple prompt"
        assert len(metadata.variables) == 0


class TestGetTypeDefault:
    """Tests for get_type_default function."""

    def test_string_default(self) -> None:
        """Test string type default."""
        assert get_type_default("str") == ""

    def test_int_default(self) -> None:
        """Test int type default."""
        assert get_type_default("int") == 0

    def test_float_default(self) -> None:
        """Test float type default."""
        assert get_type_default("float") == 0.0

    def test_bool_default(self) -> None:
        """Test bool type default."""
        assert get_type_default("bool") is False

    def test_number_default(self) -> None:
        """Test number type default."""
        assert get_type_default("number") == 0

    def test_any_default(self) -> None:
        """Test any type default."""
        assert get_type_default("any") is None

    def test_unknown_type_default(self) -> None:
        """Test unknown type default."""
        assert get_type_default("unknown") is None
