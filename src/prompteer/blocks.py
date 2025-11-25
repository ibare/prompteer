"""
Block parser for prompteer.

Handles conditional and loop blocks using {#if}, {#for}, {#else}, {/if}, {/for} syntax.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Union

from prompteer.exceptions import TemplateVariableError


# Block types
@dataclass
class TextBlock:
    """Plain text content."""

    content: str


@dataclass
class IfBlock:
    """Conditional block with optional else clause."""

    condition: str
    negated: bool = False
    operator: str | None = None  # ==, !=
    compare_value: str | None = None
    then_blocks: List[Block] = field(default_factory=list)
    else_blocks: List[Block] = field(default_factory=list)


@dataclass
class ForBlock:
    """Loop block for iterating over collections."""

    item_name: str
    collection_name: str
    index_name: str | None = None
    body_blocks: List[Block] = field(default_factory=list)


Block = Union[TextBlock, IfBlock, ForBlock]


class BlockSyntaxError(TemplateVariableError):
    """Raised when block syntax is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(variable="block", message=message)


# Regex patterns for block tags
BLOCK_PATTERN = re.compile(
    r"\{#(if|for|else)\s*(.*?)\}|\{/(if|for)\}",
    re.DOTALL,
)

# Pattern for if condition: "not var", "var == value", "var != value", or just "var"
# Supports dot notation like "item.active" or "user.profile.name"
IF_CONDITION_PATTERN = re.compile(
    r"^(not\s+)?(\w+(?:\.\w+)*)(?:\s*(==|!=)\s*[\"']?([^\"']*)[\"']?)?$"
)

# Pattern for for loop: "item in collection" or "item, index in collection"
FOR_PATTERN = re.compile(
    r"^(\w+)(?:\s*,\s*(\w+))?\s+in\s+(\w+)$"
)


def parse_blocks(template: str) -> List[Block]:
    """Parse a template string into a list of blocks.

    Args:
        template: Template string with block syntax

    Returns:
        List of Block objects representing the template structure

    Raises:
        BlockSyntaxError: If block syntax is invalid

    Examples:
        >>> blocks = parse_blocks("Hello {#if show}World{/if}")
        >>> len(blocks)
        2
    """
    tokens = _tokenize(template)
    blocks, remaining = _parse_block_list(tokens, None)

    if remaining:
        # Check for unclosed blocks
        for token in remaining:
            if token[0] == "close":
                raise BlockSyntaxError(f"Unexpected closing tag: {{/{token[1]}}}")

    return blocks


def _tokenize(template: str) -> List[tuple]:
    """Tokenize template into a list of tokens.

    Returns list of tuples:
        ("text", content)
        ("if", condition_str)
        ("for", loop_str)
        ("else", "")
        ("close", "if" or "for")
    """
    tokens = []
    last_end = 0

    for match in BLOCK_PATTERN.finditer(template):
        # Add text before this match
        if match.start() > last_end:
            text = template[last_end : match.start()]
            if text:
                tokens.append(("text", text))

        # Determine token type
        if match.group(1):  # Opening tag: if, for, else
            tag_type = match.group(1)
            tag_content = match.group(2).strip() if match.group(2) else ""
            tokens.append((tag_type, tag_content))
        elif match.group(3):  # Closing tag
            tokens.append(("close", match.group(3)))

        last_end = match.end()

    # Add remaining text
    if last_end < len(template):
        text = template[last_end:]
        if text:
            tokens.append(("text", text))

    return tokens


def _parse_block_list(
    tokens: List[tuple], end_tag: str | None
) -> tuple[List[Block], List[tuple]]:
    """Parse tokens into blocks until end_tag is found.

    Args:
        tokens: List of tokens to parse
        end_tag: Tag that ends this block list (None for top level)

    Returns:
        Tuple of (parsed blocks, remaining tokens)
    """
    blocks: List[Block] = []
    i = 0

    while i < len(tokens):
        token = tokens[i]
        token_type, token_value = token

        if token_type == "text":
            blocks.append(TextBlock(content=token_value))
            i += 1

        elif token_type == "if":
            if_block, remaining_tokens = _parse_if_block(token_value, tokens[i + 1 :])
            blocks.append(if_block)
            i = len(tokens) - len(remaining_tokens)
            tokens = tokens[:i] + remaining_tokens

        elif token_type == "for":
            for_block, remaining_tokens = _parse_for_block(token_value, tokens[i + 1 :])
            blocks.append(for_block)
            i = len(tokens) - len(remaining_tokens)
            tokens = tokens[:i] + remaining_tokens

        elif token_type == "else":
            if end_tag == "if":
                # Return with else marker
                return blocks, [("else_marker", "")] + tokens[i + 1 :]
            else:
                raise BlockSyntaxError("{#else} without matching {#if}")

        elif token_type == "close":
            if token_value == end_tag:
                return blocks, tokens[i + 1 :]
            elif end_tag is None:
                raise BlockSyntaxError(f"Unexpected closing tag: {{/{token_value}}}")
            else:
                raise BlockSyntaxError(
                    f"Mismatched closing tag: expected {{/{end_tag}}}, got {{/{token_value}}}"
                )

        else:
            i += 1

    if end_tag is not None:
        raise BlockSyntaxError(f"Unclosed block: {{#{end_tag}}} without {{/{end_tag}}}")

    return blocks, []


def _parse_if_block(condition_str: str, tokens: List[tuple]) -> tuple[IfBlock, List[tuple]]:
    """Parse an if block from tokens."""
    # Parse condition
    match = IF_CONDITION_PATTERN.match(condition_str.strip())
    if not match:
        raise BlockSyntaxError(f"Invalid if condition: {condition_str}")

    negated = match.group(1) is not None
    variable = match.group(2)
    operator = match.group(3)
    compare_value = match.group(4)

    if_block = IfBlock(
        condition=variable,
        negated=negated,
        operator=operator,
        compare_value=compare_value,
    )

    # Parse then blocks
    then_blocks, remaining = _parse_block_list(tokens, "if")

    # Check for else
    if remaining and remaining[0][0] == "else_marker":
        if_block.then_blocks = then_blocks
        # Parse else blocks
        else_blocks, remaining = _parse_block_list(remaining[1:], "if")
        if_block.else_blocks = else_blocks
    else:
        if_block.then_blocks = then_blocks

    return if_block, remaining


def _parse_for_block(loop_str: str, tokens: List[tuple]) -> tuple[ForBlock, List[tuple]]:
    """Parse a for block from tokens."""
    match = FOR_PATTERN.match(loop_str.strip())
    if not match:
        raise BlockSyntaxError(
            f"Invalid for syntax: {loop_str}. Expected 'item in collection' or 'item, index in collection'"
        )

    item_name = match.group(1)
    index_name = match.group(2)  # May be None
    collection_name = match.group(3)

    for_block = ForBlock(
        item_name=item_name,
        collection_name=collection_name,
        index_name=index_name,
    )

    # Parse body blocks
    body_blocks, remaining = _parse_block_list(tokens, "for")
    for_block.body_blocks = body_blocks

    return for_block, remaining


def resolve_value(name: str, variables: dict[str, Any], local_vars: dict[str, Any] | None = None) -> Any:
    """Resolve a variable name to its value, supporting dot notation.

    Args:
        name: Variable name, may include dots for property access
        variables: Global variables dictionary
        local_vars: Local variables (from for loops)

    Returns:
        Resolved value

    Raises:
        TemplateVariableError: If variable not found

    Examples:
        >>> resolve_value("name", {"name": "Alice"}, None)
        'Alice'
        >>> resolve_value("user.name", {"user": {"name": "Bob"}}, None)
        'Bob'
    """
    if local_vars is None:
        local_vars = {}

    parts = name.split(".")
    var_name = parts[0]

    # Check local vars first, then global
    if var_name in local_vars:
        value = local_vars[var_name]
    elif var_name in variables:
        value = variables[var_name]
    else:
        raise TemplateVariableError(
            variable=var_name,
            message=f"Variable not found: {var_name}",
        )

    # Navigate through dot notation
    for part in parts[1:]:
        if isinstance(value, dict):
            if part not in value:
                raise TemplateVariableError(
                    variable=name,
                    message=f"Property '{part}' not found in '{'.'.join(parts[:parts.index(part)])}'"
                )
            value = value[part]
        elif hasattr(value, part):
            value = getattr(value, part)
        else:
            raise TemplateVariableError(
                variable=name,
                message=f"Cannot access property '{part}' on value of type {type(value).__name__}"
            )

    return value


def _evaluate_condition(
    block: IfBlock, variables: dict[str, Any], local_vars: dict[str, Any] | None = None
) -> bool:
    """Evaluate an if block's condition."""
    try:
        value = resolve_value(block.condition, variables, local_vars)
    except TemplateVariableError:
        value = None

    if block.operator == "==":
        # Check if compare_value is a variable reference
        compare_val = block.compare_value
        if compare_val and re.match(r"^\w+(?:\.\w+)*$", compare_val):
            # Try to resolve as variable
            try:
                compare_val = str(resolve_value(compare_val, variables, local_vars))
            except TemplateVariableError:
                pass  # Keep as literal string
        result = str(value) == compare_val
    elif block.operator == "!=":
        compare_val = block.compare_value
        if compare_val and re.match(r"^\w+(?:\.\w+)*$", compare_val):
            try:
                compare_val = str(resolve_value(compare_val, variables, local_vars))
            except TemplateVariableError:
                pass
        result = str(value) != compare_val
    else:
        # Truthy check
        result = bool(value)

    if block.negated:
        result = not result

    return result


def _substitute_text_variables(
    text: str, variables: dict[str, Any], local_vars: dict[str, Any]
) -> str:
    """Substitute variables in a text block.

    Args:
        text: Text with {variable} placeholders
        variables: Global variables
        local_vars: Local variables (from for loops)

    Returns:
        Text with variables substituted
    """
    import re

    # Match both {word} and {word.word...} patterns
    pattern = r"\{(\w+(?:\.\w+)*)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        try:
            value = resolve_value(var_name, variables, local_vars)
            return str(value)
        except TemplateVariableError:
            # If variable not found, leave placeholder as-is
            return match.group(0)

    return re.sub(pattern, replacer, text)


def render_blocks(
    blocks: List[Block],
    variables: dict[str, Any],
    local_vars: dict[str, Any] | None = None,
) -> str:
    """Render a list of blocks to a string.

    Args:
        blocks: List of Block objects
        variables: Dictionary of variable values
        local_vars: Local variables (from for loops)

    Returns:
        Rendered string

    Examples:
        >>> blocks = [TextBlock(content="Hello "), TextBlock(content="World")]
        >>> render_blocks(blocks, {})
        'Hello World'
    """
    if local_vars is None:
        local_vars = {}

    result_parts = []

    for block in blocks:
        if isinstance(block, TextBlock):
            # Substitute variables in text content
            rendered_text = _substitute_text_variables(
                block.content, variables, local_vars
            )
            result_parts.append(rendered_text)

        elif isinstance(block, IfBlock):
            if _evaluate_condition(block, variables, local_vars):
                result_parts.append(
                    render_blocks(block.then_blocks, variables, local_vars)
                )
            elif block.else_blocks:
                result_parts.append(
                    render_blocks(block.else_blocks, variables, local_vars)
                )

        elif isinstance(block, ForBlock):
            try:
                collection = resolve_value(block.collection_name, variables, local_vars)
            except TemplateVariableError:
                collection = []

            if not hasattr(collection, "__iter__") or isinstance(collection, (str, bytes)):
                raise TemplateVariableError(
                    variable=block.collection_name,
                    message=f"'{block.collection_name}' is not iterable",
                )

            for index, item in enumerate(collection):
                loop_vars = local_vars.copy()
                loop_vars[block.item_name] = item
                if block.index_name:
                    loop_vars[block.index_name] = index

                result_parts.append(
                    render_blocks(block.body_blocks, variables, loop_vars)
                )

    return "".join(result_parts)
