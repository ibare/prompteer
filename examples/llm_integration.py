"""
LLM integration example with prompteer.

This example demonstrates how to use prompteer with popular LLM APIs.
Note: This is a mock example. To run with real APIs, you need API keys.
"""

from pathlib import Path

from prompteer import create_prompts

# Get prompts directory relative to this file (not CWD)
PROMPTS_DIR = Path(__file__).parent / "prompts"


def example_with_openai() -> None:
    """Example using prompteer with OpenAI API (mock)."""
    print("\n" + "=" * 60)
    print("OpenAI Integration Example")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Prepare messages for ChatGPT
    messages = [
        {
            "role": "system",
            "content": prompts.chat.system(
                role="Python programming expert",
                personality="concise and technical"
            )
        },
        {
            "role": "user",
            "content": prompts.chat.userQuery(
                question="What's the difference between list and tuple in Python?",
                context="Please explain with examples."
            )
        }
    ]

    print("\nPrepared messages for OpenAI API:")
    for msg in messages:
        print(f"\n[{msg['role'].upper()}]")
        print(msg['content'])

    # Mock API call (uncomment and add API key to use real API)
    # import openai
    # openai.api_key = "your-api-key"
    # response = openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=messages
    # )
    # print("\nResponse:", response.choices[0].message.content)


def example_with_anthropic() -> None:
    """Example using prompteer with Anthropic Claude API (mock)."""
    print("\n" + "=" * 60)
    print("Anthropic Claude Integration Example")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Prepare prompt for Claude
    system_prompt = prompts.chat.system(
        role="helpful coding assistant",
        personality="patient and educational"
    )

    user_prompt = prompts.codeReview.reviewRequest(
        language="JavaScript",
        code="""
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n-1) + fibonacci(n-2);
}
        """.strip(),
        focus_areas="performance issues and optimization suggestions"
    )

    print("\nSystem prompt:")
    print(system_prompt)
    print("\nUser prompt:")
    print(user_prompt)

    # Mock API call (uncomment and add API key to use real API)
    # import anthropic
    # client = anthropic.Anthropic(api_key="your-api-key")
    # message = client.messages.create(
    #     model="claude-3-opus-20240229",
    #     max_tokens=1024,
    #     system=system_prompt,
    #     messages=[
    #         {"role": "user", "content": user_prompt}
    #     ]
    # )
    # print("\nResponse:", message.content[0].text)


def example_batch_processing() -> None:
    """Example of processing multiple prompts in a batch."""
    print("\n" + "=" * 60)
    print("Batch Processing Example")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Prepare multiple translation requests
    texts_to_translate = [
        "Hello, how are you?",
        "Good morning!",
        "Thank you very much.",
    ]

    translation_requests = []
    for text in texts_to_translate:
        request = prompts.translation.translate(
            source_lang="English",
            target_lang="Spanish",
            text=text,
            style="formal"
        )
        translation_requests.append(request)

    print("\nPrepared batch translation requests:")
    for i, request in enumerate(translation_requests, 1):
        print(f"\n{i}. {request}")

    # In a real scenario, you would send these to an LLM API
    # and collect the responses


def example_multi_step_workflow() -> None:
    """Example of a multi-step LLM workflow."""
    print("\n" + "=" * 60)
    print("Multi-Step Workflow Example")
    print("=" * 60)

    prompts = create_prompts(PROMPTS_DIR)

    # Step 1: Generate code
    print("\nStep 1: Request code generation")
    code_request = prompts.chat.userQuery(
        question="Write a Python function to calculate factorial",
        context="Include error handling for negative numbers."
    )
    print(code_request)

    # Simulate LLM response
    generated_code = """
def factorial(n):
    if n < 0:
        raise ValueError("Negative numbers not allowed")
    if n == 0:
        return 1
    return n * factorial(n - 1)
"""

    # Step 2: Review the generated code
    print("\nStep 2: Review generated code")
    review_request = prompts.codeReview.reviewRequest(
        language="Python",
        code=generated_code,
        focus_areas="edge cases, recursion limits, and best practices"
    )
    print(review_request)

    # Step 3: Request improvements based on review
    print("\nStep 3: Request improvements")
    improvement_request = prompts.chat.userQuery(
        question="Please improve the factorial function based on the review",
        context="Add memoization and handle large numbers better."
    )
    print(improvement_request)


def main() -> None:
    """Run all LLM integration examples."""
    print("=" * 60)
    print("prompteer LLM Integration Examples")
    print("=" * 60)

    example_with_openai()
    example_with_anthropic()
    example_batch_processing()
    example_multi_step_workflow()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nNote: These are mock examples.")
    print("To use with real LLM APIs, uncomment the API calls")
    print("and provide your API keys.")


if __name__ == "__main__":
    main()
