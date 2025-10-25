"""
Tests for dynamic routing functionality.

Tests Next.js-style dynamic routing with [param] directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from prompteer import create_prompts
from prompteer.exceptions import PromptNotFoundError


@pytest.fixture
def dynamic_prompts_dir(tmp_path: Path) -> Path:
    """Create a directory structure with dynamic routing."""
    prompts_dir = tmp_path / "prompts"

    # Create question/[type]/basic/user.md
    basic_dir = prompts_dir / "question" / "[type]" / "basic"
    basic_dir.mkdir(parents=True)
    (basic_dir / "user.md").write_text(
        """---
description: Basic user query
name: User name
---
Hello {name}, this is a basic question."""
    )

    # Create question/[type]/advanced/user.md
    advanced_dir = prompts_dir / "question" / "[type]" / "advanced"
    advanced_dir.mkdir(parents=True)
    (advanced_dir / "user.md").write_text(
        """---
description: Advanced user query
name: User name
context: Additional context
---
Hello {name}, this is an advanced question. Context: {context}"""
    )

    # Create question/[type]/default.md
    (prompts_dir / "question" / "[type]" / "default.md").write_text(
        """---
description: Default fallback
---
This is the default prompt."""
    )

    return prompts_dir


@pytest.fixture
def dynamic_prompts_no_default(tmp_path: Path) -> Path:
    """Create a directory structure with dynamic routing but no default.md."""
    prompts_dir = tmp_path / "prompts"

    # Create question/[type]/basic/user.md
    basic_dir = prompts_dir / "question" / "[type]" / "basic"
    basic_dir.mkdir(parents=True)
    (basic_dir / "user.md").write_text(
        """---
description: Basic user query
name: User name
---
Hello {name}, this is a basic question."""
    )

    return prompts_dir


class TestDynamicRouting:
    """Test dynamic routing functionality."""

    def test_basic_dynamic_routing(self, dynamic_prompts_dir: Path) -> None:
        """Test basic dynamic parameter routing."""
        prompts = create_prompts(str(dynamic_prompts_dir))
        result = prompts.question.user(type="basic", name="Alice")

        assert "Hello Alice" in result
        assert "basic" in result.lower()

    def test_advanced_dynamic_routing(self, dynamic_prompts_dir: Path) -> None:
        """Test advanced type selection."""
        prompts = create_prompts(str(dynamic_prompts_dir))
        result = prompts.question.user(
            type="advanced", name="Bob", context="Python beginner"
        )

        assert "Hello Bob" in result
        assert "advanced" in result.lower()
        assert "Python beginner" in result

    def test_fallback_to_default(self, dynamic_prompts_dir: Path) -> None:
        """Test fallback to default.md when value not found."""
        prompts = create_prompts(str(dynamic_prompts_dir))
        result = prompts.question.user(type="expert")  # No expert/ dir

        assert "default" in result.lower()

    def test_missing_parameter_error(self, dynamic_prompts_dir: Path) -> None:
        """Test error when required parameter not provided."""
        prompts = create_prompts(str(dynamic_prompts_dir))

        with pytest.raises(TypeError, match="Missing required parameter: type"):
            prompts.question.user(name="Charlie")  # No type provided

    def test_no_default_error(self, dynamic_prompts_no_default: Path) -> None:
        """Test error when no match and no default.md."""
        prompts = create_prompts(str(dynamic_prompts_no_default))

        with pytest.raises(PromptNotFoundError):
            prompts.question.user(type="expert")

    def test_dynamic_with_template_defaults(
        self, dynamic_prompts_dir: Path
    ) -> None:
        """Test dynamic routing with default template values."""
        prompts = create_prompts(str(dynamic_prompts_dir))

        # Only provide type, use defaults for name
        result = prompts.question.user(type="basic")

        # Should use default empty string for name
        assert "Hello " in result
        assert "basic" in result.lower()

    def test_multiple_prompts_in_dynamic_dir(self, tmp_path: Path) -> None:
        """Test multiple different prompt files in dynamic directory."""
        prompts_dir = tmp_path / "prompts"

        # Create basic/user.md and basic/system.md
        basic_dir = prompts_dir / "chat" / "[type]" / "basic"
        basic_dir.mkdir(parents=True)
        (basic_dir / "user.md").write_text("User: {message}")
        (basic_dir / "system.md").write_text("System: You are a basic assistant.")

        # Create expert/user.md and expert/system.md
        expert_dir = prompts_dir / "chat" / "[type]" / "expert"
        expert_dir.mkdir(parents=True)
        (expert_dir / "user.md").write_text("Expert user: {message}")
        (expert_dir / "system.md").write_text("Expert system: You are an expert.")

        prompts = create_prompts(str(prompts_dir))

        # Test user prompt
        user_result = prompts.chat.user(type="basic", message="Hello")
        assert "User: Hello" in user_result

        # Test system prompt
        system_result = prompts.chat.system(type="basic")
        assert "System: You are a basic assistant" in system_result

        # Test expert
        expert_result = prompts.chat.user(type="expert", message="Hi")
        assert "Expert user: Hi" in expert_result

    def test_nested_directories_with_dynamic(self, tmp_path: Path) -> None:
        """Test dynamic routing within nested directory structure."""
        prompts_dir = tmp_path / "prompts"

        # Create api/v1/[type]/basic/request.md
        basic_dir = prompts_dir / "api" / "v1" / "[type]" / "basic"
        basic_dir.mkdir(parents=True)
        (basic_dir / "request.md").write_text("Basic API request: {endpoint}")

        prompts = create_prompts(str(prompts_dir))
        result = prompts.api.v1.request(type="basic", endpoint="/users")

        assert "Basic API request: /users" in result

    def test_dynamic_parameter_as_string(self, dynamic_prompts_dir: Path) -> None:
        """Test that dynamic parameter values are converted to strings."""
        prompts = create_prompts(str(dynamic_prompts_dir))

        # Even though we pass an integer, it should be converted to string
        result = prompts.question.user(type="basic", name="Alice")
        assert "basic" in result.lower()


class TestDynamicRoutingEdgeCases:
    """Test edge cases for dynamic routing."""

    def test_empty_dynamic_directory(self, tmp_path: Path) -> None:
        """Test dynamic directory with no value directories."""
        prompts_dir = tmp_path / "prompts"

        # Create [type]/ but with only default.md
        type_dir = prompts_dir / "question" / "[type]"
        type_dir.mkdir(parents=True)
        (type_dir / "default.md").write_text("Default only")

        prompts = create_prompts(str(prompts_dir))

        # Should use default for any value
        result = prompts.question.default(type="anything")
        assert "Default only" in result

    def test_dynamic_directory_with_subdirectories(
        self, tmp_path: Path
    ) -> None:
        """Test that only .md files are treated as prompts."""
        prompts_dir = tmp_path / "prompts"

        # Create structure with subdirectories
        basic_dir = prompts_dir / "question" / "[type]" / "basic"
        basic_dir.mkdir(parents=True)
        (basic_dir / "user.md").write_text("Basic user")

        # Create a subdirectory that should be ignored
        (basic_dir / "subdir").mkdir()
        (basic_dir / "subdir" / "file.md").write_text("Should not be found")

        prompts = create_prompts(str(prompts_dir))
        result = prompts.question.user(type="basic")

        assert "Basic user" in result

    def test_special_characters_in_values(self, tmp_path: Path) -> None:
        """Test value directories with hyphens and underscores."""
        prompts_dir = tmp_path / "prompts"

        # Create directories with special chars
        type_dir = prompts_dir / "question" / "[type]"
        (type_dir / "basic-level").mkdir(parents=True)
        (type_dir / "basic-level" / "user.md").write_text("Basic level")

        (type_dir / "advanced_level").mkdir(parents=True)
        (type_dir / "advanced_level" / "user.md").write_text("Advanced level")

        prompts = create_prompts(str(prompts_dir))

        result1 = prompts.question.user(type="basic-level")
        assert "Basic level" in result1

        result2 = prompts.question.user(type="advanced_level")
        assert "Advanced level" in result2


class TestDynamicRoutingTypeGeneration:
    """Test type stub generation for dynamic routes."""

    def test_type_stub_generation_with_dynamic(
        self, dynamic_prompts_dir: Path, tmp_path: Path
    ) -> None:
        """Test that type stubs include Literal types for dynamic parameters."""
        from prompteer.type_generator import TypeStubGenerator

        generator = TypeStubGenerator(dynamic_prompts_dir)
        output = tmp_path / "prompts.pyi"
        generator.generate_type_stub(output)

        content = output.read_text()

        # Check that Literal is imported
        assert "from typing import Literal" in content

        # Check that the method has the Literal type
        assert 'type: Literal["advanced", "basic"]' in content

        # Check that the method has the template variables
        assert "name: str" in content
        assert "context: str" in content

    def test_type_stub_includes_available_values(
        self, dynamic_prompts_dir: Path, tmp_path: Path
    ) -> None:
        """Test that type stubs document available values in docstring."""
        from prompteer.type_generator import TypeStubGenerator

        generator = TypeStubGenerator(dynamic_prompts_dir)
        output = tmp_path / "prompts.pyi"
        generator.generate_type_stub(output)

        content = output.read_text()

        # Check that docstring includes available values
        assert "Available values: advanced, basic" in content
