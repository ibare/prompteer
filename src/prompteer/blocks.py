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

# 변수 참조와 이스케이프를 한 번의 스캔으로 함께 소비하는 통합 패턴.
# {{ 와 }} 를 같은 패스에서 리터럴로 흡수하므로, 언이스케이프된 결과가
# 다시 변수로 해석되는 경로가 존재하지 않는다.
VARIABLE_PATTERN = re.compile(r"\{\{|\}\}|\{(\w+(?:\.\w+)*)\}")

# 블록 태그 키워드. 텍스트에 {if} 처럼 단독으로 나타나면 변수가 아니라
# 리터럴로 취급한다.
BLOCK_KEYWORDS = frozenset({"if", "for", "else"})


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


def substitute_variables(
    text: str,
    variables: dict[str, Any],
    local_vars: dict[str, Any] | None = None,
    *,
    missing: set[str] | None = None,
    missing_default: str | None = None,
) -> str:
    """텍스트의 변수 참조를 단일 패스로 치환한다.

    이 함수는 prompteer 의 유일한 치환 구현이다. 텍스트를 정확히 한 번만
    훑으며, 치환으로 만들어진 출력은 같은 패스 안에서 다시 검사되지 않는다.
    따라서 주입값 안에 들어 있는 중괄호는 변수로 해석되지 않는다.

    Args:
        text: {variable} 자리표시자를 포함한 텍스트
        variables: 전역 변수
        local_vars: 지역 변수 (for 루프에서 전달)
        missing: 해결하지 못한 변수 이름을 수집할 집합. None 이면 수집하지 않는다.
        missing_default: 해결하지 못한 변수를 대체할 문자열.
            None 이면 자리표시자를 원문 그대로 남긴다.

    Returns:
        변수가 치환된 텍스트

    Examples:
        >>> substitute_variables("Hello {name}", {"name": "Alice"})
        'Hello Alice'
        >>> substitute_variables("A: {a}", {"a": "x {foo} y"})
        'A: x {foo} y'
        >>> substitute_variables("{{literal}}", {})
        '{literal}'
    """
    if local_vars is None:
        local_vars = {}

    def replacer(match: re.Match) -> str:
        token = match.group(0)

        # 이스케이프: 리터럴 중괄호로 환원하고 그대로 확정한다.
        if token == "{{":
            return "{"
        if token == "}}":
            return "}"

        var_name = match.group(1)

        # 블록 키워드는 변수가 아니므로 원문 유지
        if var_name in BLOCK_KEYWORDS:
            return token

        try:
            return str(resolve_value(var_name, variables, local_vars))
        except TemplateVariableError:
            # 미해결 변수는 이 지점에서만 알 수 있다. 렌더 결과를 다시
            # 훑어서는 템플릿에서 온 자리표시자와 주입값에서 온 중괄호를
            # 구분할 수 없으므로, 판정에 필요한 정보를 여기서 수집한다.
            if missing is not None:
                missing.add(var_name)
            if missing_default is not None:
                return missing_default
            return token

    return VARIABLE_PATTERN.sub(replacer, text)


def render_blocks(
    blocks: List[Block],
    variables: dict[str, Any],
    local_vars: dict[str, Any] | None = None,
    *,
    missing: set[str] | None = None,
    missing_default: str | None = None,
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
            rendered_text = substitute_variables(
                block.content,
                variables,
                local_vars,
                missing=missing,
                missing_default=missing_default,
            )
            result_parts.append(rendered_text)

        elif isinstance(block, IfBlock):
            if _evaluate_condition(block, variables, local_vars):
                result_parts.append(
                    render_blocks(
                        block.then_blocks,
                        variables,
                        local_vars,
                        missing=missing,
                        missing_default=missing_default,
                    )
                )
            elif block.else_blocks:
                result_parts.append(
                    render_blocks(
                        block.else_blocks,
                        variables,
                        local_vars,
                        missing=missing,
                        missing_default=missing_default,
                    )
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
                    render_blocks(
                        block.body_blocks,
                        variables,
                        loop_vars,
                        missing=missing,
                        missing_default=missing_default,
                    )
                )

    return "".join(result_parts)
