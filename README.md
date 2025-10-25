# prompteer

A lightweight file-based prompt manager for LLM workflows. Simple, scalable, and version-control friendly.

## Features

- **File-based prompt management** - Store prompts as markdown files
- **Intuitive dot notation API** - Access prompts naturally: `prompts.chat.system()`
- **Dynamic routing** - Next.js-style `[param]` directories for flexible prompt selection
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

### 1. Initialize Your Prompt Directory

Use the `init` command to create a prompt directory with example prompts:

```bash
prompteer init
```

This creates a `prompts/` directory with:
- Basic chat prompts
- Dynamic routing examples
- Variable types demonstrations

Or initialize in a custom directory:

```bash
prompteer init my-prompts
```

### 2. Or Create Your Own Structure

```
my-project/
├── prompts/
│   ├── greeting/
│   │   └── hello.md
│   └── chat/
│       └── system.md
└── main.py
```

### 3. Write Prompts with Variables

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

### 4. Use in Your Code

```python
from pathlib import Path
from prompteer import create_prompts

# Option 1: Relative to current working directory
prompts = create_prompts("./prompts")

# Option 2: Relative to your script file (recommended for packages/libraries)
PROMPTS_DIR = Path(__file__).parent / "prompts"
prompts = create_prompts(PROMPTS_DIR)

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

**Path Resolution:**
- Relative paths (e.g., `"./prompts"`) are resolved from the current working directory
- For packages/libraries, use `Path(__file__).parent / "prompts"` to ensure it works regardless of where the code is run from
- Absolute paths always work but are less portable

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

## Dynamic Routing

Create flexible prompts that adapt based on runtime parameters, similar to Next.js dynamic routes.

### Basic Example

**File Structure:**
```
prompts/
└── question/
    └── [type]/              # Dynamic parameter: type
        ├── basic/           # type="basic"
        │   └── user.md
        ├── advanced/        # type="advanced"
        │   └── user.md
        └── default.md       # Fallback when no match
```

**Usage:**
```python
from prompteer import create_prompts

prompts = create_prompts("./prompts")

# Select different prompt versions
basic = prompts.question.user(type="basic", name="Alice")
advanced = prompts.question.user(type="advanced", name="Bob", context="Python expert")

# Fallback to default.md if type not found
fallback = prompts.question.user(type="expert")  # Uses default.md
```

### How It Works

1. `[type]` directory = dynamic parameter
2. `basic/`, `advanced/` = possible values for the parameter
3. `default.md` = fallback when value doesn't match any directory
4. If no default.md exists, raises `PromptNotFoundError`

### Type Hints with Dynamic Routing

Generate type stubs to get IDE autocomplete for available values:

```bash
prompteer generate-types ./prompts -o prompts.pyi
```

Your generated type stub will include `Literal` types:
```python
def user(
    self,
    type: Literal["basic", "advanced"],  # Autocomplete with available values!
    name: str = "",
    **kwargs: Any
) -> str: ...
```

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

### Initialize Project

Create a new prompts directory with example prompts:

```bash
# Create in default 'prompts/' directory
prompteer init

# Create in custom directory
prompteer init my-prompts

# Overwrite existing directory
prompteer init prompts --force
```

The `init` command creates:
- Basic chat prompts with variables
- Dynamic routing examples (`[type]` directories)
- Sample prompts demonstrating all features

### Generate Type Stubs

```bash
# Default command - can omit 'generate-types'
prompteer ./prompts -o prompts.pyi

# Or explicitly use generate-types
prompteer generate-types ./prompts -o prompts.pyi

# Watch mode - auto-regenerate on changes
prompteer ./prompts --watch

# Specify encoding
prompteer ./prompts --encoding utf-8
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

---

## For AI Agents & LLM Tools

### Quick Integration Guide

**Installation from GitHub (before PyPI release):**
```bash
pip install git+https://github.com/ibare/prompteer.git
```

**Installation from PyPI (when available):**
```bash
pip install prompteer
```

### Essential Usage Pattern

```python
from pathlib import Path
from prompteer import create_prompts

# 1. Load prompts from directory
# Option A: Relative to current working directory
prompts = create_prompts("./prompts")

# Option B: Relative to script file (recommended for packages)
PROMPTS_DIR = Path(__file__).parent / "prompts"
prompts = create_prompts(PROMPTS_DIR)

# 2. Access prompts with dot notation
result = prompts.chat.system(
    role="helpful assistant",
    personality="friendly and patient"
)

# 3. Use the rendered prompt
print(result)
```

**Important - Path Resolution:**
- Relative paths are resolved from current working directory (CWD)
- For library/package usage, use `Path(__file__).parent / "prompts"` pattern
- This ensures prompts are found regardless of where the host application runs from

### Prompt File Format

Create markdown files with YAML frontmatter:

```markdown
---
description: System message prompt
role: AI role description
personality: AI personality traits
---
You are a {role}.
Your personality is {personality}.
```

### File Structure Convention

```
prompts/
├── chat/
│   ├── system.md       → prompts.chat.system()
│   └── user-query.md   → prompts.chat.userQuery()
└── code-review/
    └── review.md       → prompts.codeReview.review()
```

**Key Convention**: `kebab-case` files/directories → `camelCase` Python methods

### Dynamic Routing (v0.2.0+)

Use `[param]` directories for runtime prompt selection:

```
prompts/
└── question/
    └── [type]/              # Dynamic parameter
        ├── basic/
        │   └── user.md
        ├── advanced/
        │   └── user.md
        └── default.md       # Fallback
```

```python
prompts = create_prompts("./prompts")

# Select different versions based on runtime parameter
basic = prompts.question.user(type="basic", name="Alice")
advanced = prompts.question.user(type="advanced", name="Bob", context="expert")

# Automatic fallback to default.md if value doesn't match
fallback = prompts.question.user(type="expert")  # Uses default.md
```

**Type safety with Literal types:**
```python
# Generated type stub includes available values
def user(
    self,
    type: Literal["basic", "advanced"],  # IDE autocomplete!
    name: str = "",
    **kwargs: Any
) -> str: ...
```

### Type Hints (Optional)

```bash
# Generate type stubs for IDE autocomplete
prompteer generate-types ./prompts -o prompts.pyi
```

### Key Implementation Files

- `src/prompteer/core.py` - Main `Prompteer` class and `create_prompts()` function
- `src/prompteer/proxy.py` - Dynamic attribute access via `__getattr__`
- `src/prompteer/template.py` - Variable substitution engine
- `src/prompteer/metadata.py` - YAML frontmatter parsing
- `src/prompteer/type_generator.py` - Type stub generation

### Common Patterns

**Dynamic prompt selection:**
```python
prompts = create_prompts("./prompts")

# Select prompt based on runtime condition
if task_type == "code_review":
    prompt = prompts.codeReview.reviewRequest(language="Python", code=code)
elif task_type == "translation":
    prompt = prompts.translation.translate(source="EN", target="KO", text=text)
```

**Error handling:**
```python
from prompteer import create_prompts, PromptNotFoundError

try:
    prompts = create_prompts("./prompts")
    result = prompts.some.prompt()
except PromptNotFoundError as e:
    print(f"Prompt not found: {e}")
```

### Supported Variable Types

In YAML frontmatter:
- `name: description` - defaults to `str`
- `age(int): description` - integer
- `score(float): description` - float
- `active(bool): description` - boolean
- `count(number): description` - int or float
- `data(any): description` - any type

### Testing

Examples available in `examples/` directory:
- `examples/basic_usage.py` - Basic features
- `examples/llm_integration.py` - LLM API integration
- `examples/advanced_usage.py` - Advanced patterns
- `examples/dynamic_routing.py` - Dynamic routing examples

---

## Links

- **GitHub**: https://github.com/ibare/prompteer
- **PyPI**: https://pypi.org/project/prompteer/
- **Documentation**: See [examples/](examples/) directory
- **Issues**: https://github.com/ibare/prompteer/issues
