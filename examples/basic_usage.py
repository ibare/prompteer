"""
Basic usage examples for prompteer.

This example demonstrates:
1. Loading prompts from a directory
2. Accessing prompts with dot notation
3. Using variables in prompts
4. Working with metadata and defaults
"""

from pathlib import Path

from prompteer import create_prompts

# Get prompts directory relative to this file (not CWD)
PROMPTS_DIR = Path(__file__).parent / "prompts"


def main() -> None:
    """Run basic usage examples."""
    # Initialize Prompteer with prompts directory
    print("=" * 60)
    print("prompteer Basic Usage Examples")
    print("=" * 60)

    # Create prompts with full type hints
    # Using Path(__file__).parent ensures it works regardless of CWD
    prompts = create_prompts(PROMPTS_DIR)

    # Example 1: Simple prompt access
    print("\n1. Accessing chat system prompt:")
    print("-" * 60)
    system_msg = prompts.chat.system(
        role="helpful programming assistant",
        personality="friendly and patient"
    )
    print(system_msg)

    # Example 2: User query with context
    print("\n2. Creating user query with context:")
    print("-" * 60)
    user_query = prompts.chat.userQuery(
        question="How do I read a file in Python?",
        context="I'm a beginner and want to learn best practices."
    )
    print(user_query)

    # Example 3: Code review request
    print("\n3. Code review request:")
    print("-" * 60)
    code_sample = '''
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total = total + num
    return total
'''

    review_request = prompts.codeReview.reviewRequest(
        language="Python",
        code=code_sample,
        focus_areas="performance and readability"
    )
    print(review_request)

    # Example 4: Translation request
    print("\n4. Translation request:")
    print("-" * 60)
    translation = prompts.translation.translate(
        source_lang="English",
        target_lang="Korean",
        text="Hello, how are you today?",
        style="casual"
    )
    print(translation)

    # Example 5: Using defaults (omitting optional parameters)
    print("\n5. Using defaults for optional parameters:")
    print("-" * 60)
    # If metadata defines defaults, you can omit parameters
    simple_query = prompts.chat.userQuery(
        question="What is Python?"
    )
    print(simple_query)

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
