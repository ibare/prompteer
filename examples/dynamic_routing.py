"""
Dynamic routing example for prompteer.

Demonstrates Next.js-style dynamic prompt selection.
"""

from pathlib import Path

from prompteer import DynamicParameterError, PromptNotFoundError, create_prompts

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

    # Example 5: Nested [param] directories
    print("\n5. Nested dynamic routing (tier -> language):")
    print("-" * 60)
    result = prompts.support.reply(
        tier="pro", lang="ko", customer="김민태", issue="결제 오류"
    )
    print(result)

    # Example 6: A static directory between two dynamic levels
    print("\n6. Static directory inside a dynamic route:")
    print("-" * 60)
    result = prompts.support.escalation.manager(
        tier="pro", customer="김민태", summary="3회 재발한 결제 오류"
    )
    print(result)

    # Example 7: default/ subtree covers a whole path, not just one file
    print("\n7. Fallback through the default/ subtree:")
    print("-" * 60)
    result = prompts.support.escalation.manager(
        tier="unknown", customer="이서준", summary="등급 미확인 고객 문의"
    )
    print(result)

    # Example 8: The routing value itself is available in the prompt body
    print("\n8. Routing value used inside the prompt:")
    print("-" * 60)
    result = prompts.support.reply(tier="starter", customer="박도윤", issue="배송 지연")
    print(result)

    # Example 9: Names match regardless of case
    print("\n9. Case-insensitive routing values:")
    print("-" * 60)
    result = prompts.question.user(type="BASIC", name="Dana")
    print(result)

    # Example 10: Error handling
    print("\n10. Error handling:")
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

    try:
        # An empty routing value is rejected instead of resolving ambiguously
        result = prompts.question.user(type="", name="Erin")
    except DynamicParameterError as e:
        print(f"✓ Caught expected error: {e}")

    try:
        # default.md cannot stand in for a multi-segment path
        result = prompts.support.escalation.manager(
            tier="free", customer="한지우", summary="문의"
        )
        print(f"free tier escalation resolved: {result.splitlines()[0]}")
    except PromptNotFoundError as e:
        print(f"✓ Caught expected error: {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
