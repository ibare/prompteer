# prompteer

A lightweight file-based prompt manager for LLM workflows. Simple, scalable, and version-control friendly.

## Features

- **File-based prompt management** - Store prompts as markdown files
- **Intuitive dot notation API** - Access prompts naturally: `prompts.chat.system()`
- **Version control friendly** - Track prompt changes with Git
- **Zero configuration** - Start using immediately
- **IDE autocomplete support** - Full type hints with generated stubs
- **Lightweight** - Minimal dependencies (only PyYAML)
- **Python 3.7+** - Wide compatibility

## Installation

```bash
pip install prompteer
```

## Quick Start

### 1. Create Your Prompt Directory

```
my-project/
├── prompts/
│   ├── greeting/
│   │   └── hello.md
│   └── chat/
│       └── system.md
└── main.py
```

### 2. Write Prompts with Variables

**`prompts/chat/system.md`:**
```markdown
---
description: System message for chat
role: AI role description
personality: AI personality traits
---
You are a {role}.

Your personality is {personality}.

Please be helpful, accurate, and respectful in all interactions.
```

### 3. Use in Your Code

```python
from prompteer import create_prompts

# Load prompts
prompts = create_prompts("./prompts")

# Use with variables
system_message = prompts.chat.system(
    role="helpful assistant",
    personality="friendly and patient"
)

print(system_message)
# Output:
# You are a helpful assistant.
# Your personality is friendly and patient.
# Please be helpful, accurate, and respectful in all interactions.
```

## Type Hints & IDE Autocomplete

Generate type stubs for perfect IDE autocomplete:

```bash
prompteer generate-types ./prompts -o prompts.pyi
```

Now your IDE will provide:
- ✅ Autocomplete for all prompt paths
- ✅ Parameter suggestions
- ✅ Type checking
- ✅ Documentation tooltips

```python
from prompteer import create_prompts

prompts = create_prompts("./prompts")

# Full IDE autocomplete support!
prompts.chat.system(role="...", personality="...")
```

### Watch Mode

Automatically regenerate types when prompts change:

```bash
prompteer generate-types ./prompts --watch
```

## Variable Types

Specify types in your prompt frontmatter:

```markdown
---
description: My prompt
name(str): User's name
age(int): User's age
score(float): User's score
active(bool): Is user active
count(number): Can be int or float
data(any): Any type
---
Hello {name}, you are {age} years old!
```

Supported types:
- `str` (default)
- `int`
- `float`
- `bool`
- `number` (int or float)
- `any`

## Real-World Example

### Prompt File Structure

```
prompts/
├── code-review/
│   └── review-request.md
├── translation/
│   └── translate.md
└── chat/
    ├── system.md
    └── user-query.md
```

### Using with LLM APIs

```python
from prompteer import create_prompts
import openai

prompts = create_prompts("./prompts")

# Prepare system message
system_msg = prompts.chat.system(
    role="Python expert",
    personality="concise and technical"
)

# Prepare user query
user_msg = prompts.chat.userQuery(
    question="How do I handle exceptions in Python?",
    context="I'm a beginner learning best practices."
)

# Send to OpenAI
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
)
```

## CLI Commands

### Generate Type Stubs

```bash
# Generate once
prompteer generate-types <prompts-dir> -o <output.pyi>

# Watch mode - auto-regenerate on changes
prompteer generate-types <prompts-dir> --watch

# Specify encoding
prompteer generate-types <prompts-dir> --encoding utf-8
```

### Help

```bash
prompteer --help
prompteer generate-types --help
```

## Advanced Usage

### Dynamic Prompt Selection

```python
from prompteer import create_prompts

prompts = create_prompts("./prompts")

# Select prompts dynamically
prompt_type = "code_review"
if prompt_type == "code_review":
    result = prompts.codeReview.reviewRequest(
        language="Python",
        code="def hello(): print('hi')",
        focus_areas="style and best practices"
    )
```

### Error Handling

```python
from prompteer import create_prompts, PromptNotFoundError

try:
    prompts = create_prompts("./prompts")
    result = prompts.nonexistent.prompt()
except PromptNotFoundError as e:
    print(f"Prompt not found: {e}")
```

### Multiple Prompt Directories

```python
from prompteer import create_prompts

# Different prompt sets for different purposes
chat_prompts = create_prompts("./prompts/chat")
review_prompts = create_prompts("./prompts/reviews")

system_msg = chat_prompts.system(role="assistant")
review_msg = review_prompts.codeReview(language="Python")
```

## Why prompteer?

**Before prompteer:**
```python
# Prompts scattered in code
system_prompt = """You are a helpful assistant.
Your personality is friendly.
Please be respectful."""

# Hard to maintain, version, and reuse
```

**With prompteer:**
```python
# Prompts organized in files
# Easy to version control
# Reusable across projects
# Type-safe with autocomplete
prompts = create_prompts("./prompts")
system_prompt = prompts.chat.system(
    role="helpful assistant",
    personality="friendly"
)
```

## File Naming Convention

- **Directories**: Use `kebab-case` → becomes `camelCase` in Python
  - `code-review/` → `prompts.codeReview`
- **Files**: Use `kebab-case.md` → becomes `camelCase()` method
  - `user-query.md` → `prompts.chat.userQuery()`

## Requirements

- Python 3.7+
- PyYAML >= 5.1

Optional:
- watchdog (for `--watch` mode)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **GitHub**: https://github.com/ibare/prompteer
- **PyPI**: https://pypi.org/project/prompteer/
- **Documentation**: See [examples/](examples/) directory
- **Issues**: https://github.com/ibare/prompteer/issues
