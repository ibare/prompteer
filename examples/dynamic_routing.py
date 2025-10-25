"""
Dynamic routing example for prompteer.

Demonstrates Next.js-style dynamic prompt selection.
"""

from pathlib import Path

from prompteer import create_prompts, PromptNotFoundError

# Get prompts directory relative to this file (not CWD)
PROMPTS_DIR = Path(__file__).parent / "prompts-dynamic"


def main():
    """Run dynamic routing examples."""
    print("=" * 60)
    print("prompteer Dynamic Routing Examples")
    print("=" * 60)

    # Use the example prompts directory
    prompts = create_prompts(PROMPTS_DIR)

    # Example 1: Basic type
    print("\n1. Basic user query:")
    print("-" * 60)
    result = prompts.question.user(type="basic", name="Alice")
    print(result)

    # Example 2: Advanced type
    print("\n2. Advanced user query:")
    print("-" * 60)
    result = prompts.question.user(
        type="advanced", name="Bob", context="Learning Python with prompteer"
    )
    print(result)

    # Example 3: Fallback to default
    print("\n3. Fallback to default:")
    print("-" * 60)
    result = prompts.question.user(type="expert")
    print(result)
    print("(Used default.md because 'expert' directory doesn't exist)")

    # Example 4: Multiple prompts in dynamic directory
    print("\n4. Multiple prompts (user and system):")
    print("-" * 60)
    user_msg = prompts.chat.user(type="friendly", message="Hello!")
    print(f"User: {user_msg}")
    system_msg = prompts.chat.system(type="friendly")
    print(f"System: {system_msg}")

    # Example 5: Error handling
    print("\n5. Error handling:")
    print("-" * 60)
    try:
        # This will fail because type parameter is required
        result = prompts.question.user(name="Charlie")
    except TypeError as e:
        print(f"✓ Caught expected error: {e}")

    try:
        # This will fail if no default.md exists
        result = prompts.nonexistent.prompt(type="any")
    except PromptNotFoundError as e:
        print(f"✓ Caught expected error: {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
