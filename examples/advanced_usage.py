"""
Advanced usage examples for prompteer.

This example demonstrates:
1. Dynamic prompt selection
2. Prompt composition
3. Error handling
4. Custom prompt workflows
"""

from pathlib import Path

from prompteer import PromptNotFoundError, create_prompts

# Get prompts directory relative to this file (not CWD)
PROMPTS_DIR = Path(__file__).parent / "prompts"


def example_dynamic_prompt_selection() -> None:
    """Example of selecting prompts dynamically based on conditions."""
    print("\n" + "=" * 60)
    print("Dynamic Prompt Selection")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Simulate different user scenarios
    scenarios = [
        {"type": "chat", "user_level": "beginner"},
        {"type": "code_review", "language": "Python"},
        {"type": "translation", "languages": ("English", "Korean")},
    ]

    for scenario in scenarios:
        print(f"\nScenario: {scenario}")
        print("-" * 40)

        if scenario["type"] == "chat":
            prompt = prompts.chat.system(
                role="patient tutor",
                personality="encouraging and supportive"
            )
        elif scenario["type"] == "code_review":
            prompt = prompts.codeReview.reviewRequest(
                language=scenario["language"],
                code="# Sample code here",
                focus_areas="best practices"
            )
        elif scenario["type"] == "translation":
            src, tgt = scenario["languages"]
            prompt = prompts.translation.translate(
                source_lang=src,
                target_lang=tgt,
                text="Sample text",
                style="casual"
            )

        print(prompt[:100] + "..." if len(prompt) > 100 else prompt)


def example_prompt_composition() -> None:
    """Example of composing complex prompts from multiple parts."""
    print("\n" + "=" * 60)
    print("Prompt Composition")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Build a complex prompt by combining multiple prompts
    system_context = prompts.chat.system(
        role="expert code reviewer and teacher",
        personality="thorough and constructive"
    )

    review_task = prompts.codeReview.reviewRequest(
        language="Python",
        code="""
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
        """.strip(),
        focus_areas="pythonic patterns and efficiency"
    )

    # Combine them
    combined_prompt = f"{system_context}\n\n---\n\n{review_task}"

    print("\nCombined prompt:")
    print(combined_prompt)


def example_error_handling() -> None:
    """Example of proper error handling with prompteer."""
    print("\n" + "=" * 60)
    print("Error Handling")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Example 1: Handling non-existent prompts
    print("\n1. Handling non-existent prompts:")
    try:
        # This will raise PromptNotFoundError
        prompts.nonexistent.prompt()
    except PromptNotFoundError as e:
        print(f"✓ Caught error: {e}")
        print("  Fallback: Using default prompt instead")

    # Example 2: Validating required variables
    print("\n2. Handling missing variables:")
    try:
        # This should work with defaults
        result = prompts.chat.userQuery(
            question="What is Python?"
            # context is optional, will use default
        )
        print(f"✓ Successfully used defaults")
        print(f"  Result: {result[:50]}...")
    except Exception as e:
        print(f"✗ Error: {e}")


def example_custom_workflow() -> None:
    """Example of a custom prompt workflow."""
    print("\n" + "=" * 60)
    print("Custom Workflow: Code Generation & Review Cycle")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    class CodeGenerationWorkflow:
        """A workflow for generating and reviewing code."""

        def __init__(self, prompts: Prompteer):
            self.prompts = prompts

        def generate_code_prompt(self, task: str, language: str) -> str:
            """Generate a code generation prompt."""
            return self.prompts.chat.userQuery(
                question=f"Write {language} code for: {task}",
                context="Include comments and error handling."
            )

        def review_code_prompt(self, code: str, language: str) -> str:
            """Generate a code review prompt."""
            return self.prompts.codeReview.reviewRequest(
                language=language,
                code=code,
                focus_areas="correctness, efficiency, and readability"
            )

        def improve_code_prompt(self, code: str, feedback: str) -> str:
            """Generate a code improvement prompt."""
            return self.prompts.chat.userQuery(
                question="Improve this code based on the review",
                context=f"Original code:\n{code}\n\nFeedback:\n{feedback}"
            )

    # Use the workflow
    workflow = CodeGenerationWorkflow(prompts)

    print("\n1. Generate initial code:")
    gen_prompt = workflow.generate_code_prompt(
        task="read a CSV file and calculate average of a column",
        language="Python"
    )
    print(gen_prompt[:100] + "...")

    print("\n2. Review the code:")
    mock_code = "def read_csv(file): ..."
    review_prompt = workflow.review_code_prompt(mock_code, "Python")
    print(review_prompt[:100] + "...")

    print("\n3. Improve based on feedback:")
    improve_prompt = workflow.improve_code_prompt(
        code=mock_code,
        feedback="Add error handling for file not found"
    )
    print(improve_prompt[:100] + "...")


def example_prompt_versioning() -> None:
    """Example of managing different prompt versions."""
    print("\n" + "=" * 60)
    print("Prompt Versioning Strategy")
    print("=" * 60)

    print("""
    Recommended approach for prompt versioning:

    1. Use Git for version control:
       - Commit prompt changes with descriptive messages
       - Use branches for experimental prompts
       - Tag releases (v1.0, v1.1, etc.)

    2. Directory structure for versions:
       prompts/
       ├── v1/
       │   └── chat/
       │       └── system.md
       └── v2/
           └── chat/
               └── system.md

    3. Access different versions:
       prompts_v1 = Prompteer("prompts/v1")
       prompts_v2 = Prompteer("prompts/v2")

    4. Use metadata for version info:
       ---
       version: 2.0
       deprecated: false
       ---
    """)


def main() -> None:
    """Run all advanced examples."""
    print("=" * 60)
    print("prompteer Advanced Usage Examples")
    print("=" * 60)

    example_dynamic_prompt_selection()
    example_prompt_composition()
    example_error_handling()
    example_custom_workflow()
    example_prompt_versioning()

    print("\n" + "=" * 60)
    print("All advanced examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
