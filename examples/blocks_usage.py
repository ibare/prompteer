"""
Blocks usage examples for prompteer v0.3.0+.

This example demonstrates:
1. Conditional blocks with {#if}, {#else}, {/if}
2. Loop blocks with {#for item in items}, {/for}
3. Comparison operators (==, !=)
4. Negation with {#if not condition}
5. Nested blocks
6. Dot notation for object properties
"""

from pathlib import Path

from prompteer import create_prompts

# Get prompts directory relative to this file
PROMPTS_DIR = Path(__file__).parent / "prompts"


def main() -> None:
    """Run blocks usage examples."""
    print("=" * 60)
    print("prompteer Blocks Usage Examples (v0.3.0+)")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Example 1: Conditional blocks - formal vs casual greeting
    print("\n1. Conditional Blocks - Formal Greeting:")
    print("-" * 60)
    formal_greeting = prompts.blocks.greeting(
        formal=True,
        name="Dr. Smith",
        title="Professor"
    )
    print(formal_greeting)

    print("\n   Casual Greeting:")
    print("-" * 60)
    casual_greeting = prompts.blocks.greeting(
        formal=False,
        name="John"
    )
    print(casual_greeting)

    # Example 2: Loop blocks - task list
    print("\n2. Loop Blocks - Task List with Priority:")
    print("-" * 60)
    tasks = [
        {"name": "Review PR #123", "description": "Check code changes", "priority": "high"},
        {"name": "Update docs", "description": "Add new API endpoints", "priority": "medium"},
        {"name": "Fix typo", "description": "README.md line 42", "priority": "low"},
    ]
    task_list = prompts.blocks.taskList(
        title="Today's Tasks",
        tasks=tasks,
        show_priority=True
    )
    print(task_list)

    print("\n   Task List without Priority:")
    print("-" * 60)
    task_list_simple = prompts.blocks.taskList(
        title="Simple Task List",
        tasks=tasks,
        show_priority=False
    )
    print(task_list_simple)

    # Example 3: Nested blocks with comparison - code review
    print("\n3. Nested Blocks - Code Review (Friendly Tone):")
    print("-" * 60)
    code_sample = '''def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total'''

    checklist = [
        {"category": "Style", "description": "Check naming conventions and formatting"},
        {"category": "Logic", "description": "Verify algorithm correctness"},
        {"category": "Performance", "description": "Look for optimization opportunities"},
        {"category": "Security", "description": "Check for potential vulnerabilities"},
    ]

    friendly_review = prompts.blocks.codeReview(
        language="python",
        code=code_sample,
        tone="friendly",
        include_checklist=True,
        checklist=checklist
    )
    print(friendly_review)

    print("\n   Code Review (Strict Tone, No Checklist):")
    print("-" * 60)
    strict_review = prompts.blocks.codeReview(
        language="python",
        code=code_sample,
        tone="strict",
        include_checklist=False,
        checklist=[]
    )
    print(strict_review)

    # Example 4: Complex nested structure - multilingual
    print("\n4. Complex Nested Blocks - Multilingual Assistant:")
    print("-" * 60)
    languages = [
        {"name": "English", "code": "en"},
        {"name": "Korean", "code": "ko"},
        {"name": "Japanese", "code": "ja"},
    ]
    examples = [
        {"language": "English", "greeting": "Hello!", "farewell": "Goodbye!"},
        {"language": "Korean", "greeting": "안녕하세요!", "farewell": "안녕히 가세요!"},
        {"language": "Japanese", "greeting": "こんにちは!", "farewell": "さようなら!"},
    ]

    multilingual = prompts.blocks.multilingual(
        languages=languages,
        primary_language="ko",
        include_examples=True,
        examples=examples
    )
    print(multilingual)

    print("\n   Without Examples:")
    print("-" * 60)
    multilingual_simple = prompts.blocks.multilingual(
        languages=languages,
        primary_language="en",
        include_examples=False,
        examples=[]
    )
    print(multilingual_simple)

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
