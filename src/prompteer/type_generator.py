"""
Type stub generator for prompteer.

Generates .pyi files from prompt directories for IDE autocompletion.

Dynamic routes are flattened into the class that owns the ``[param]``
directory. Nested ``[param]`` levels and static directories sitting between
them are merged across value directories, so
``q/[type]/basic/extra/user.md`` and ``q/[type]/advanced/extra/user.md``
become a single ``extra.user(type=...)`` method.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from prompteer.metadata import parse_metadata
from prompteer.path_utils import (
    extract_param_name,
    is_dynamic_dir,
    normalize_name,
    to_attribute_name,
)

#: 값 디렉터리 대신 폴백으로 쓰이는 이름
DEFAULT_NAME = "default"

#: 병적으로 깊은 트리에서 재귀를 막는다
MAX_SCAN_DEPTH = 64


def get_python_type(yaml_type: str) -> str:
    """Convert YAML type to Python type annotation.

    Args:
        yaml_type: Type from YAML metadata

    Returns:
        Python type annotation string

    Examples:
        >>> get_python_type("str")
        'str'
        >>> get_python_type("int")
        'int'
        >>> get_python_type("number")
        'Union[int, float]'
        >>> get_python_type("list")
        'list[Any]'
        >>> get_python_type("object")
        'dict[str, Any]'
    """
    type_mapping = {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "number": "Union[int, float]",
        "any": "Any",
        # New types for v0.3.0
        "list": "list[Any]",
        "object": "dict[str, Any]",
        "dict": "dict[str, Any]",
        "array": "list[Any]",
    }
    return type_mapping.get(yaml_type, "Any")


def get_default_value(yaml_type: str) -> str:
    """Get default value string for a type.

    Args:
        yaml_type: Type from YAML metadata

    Returns:
        Default value as string

    Examples:
        >>> get_default_value("str")
        '""'
        >>> get_default_value("int")
        '0'
        >>> get_default_value("list")
        '[]'
        >>> get_default_value("object")
        '{}'
    """
    defaults = {
        "str": '""',
        "int": "0",
        "float": "0.0",
        "bool": "False",
        "number": "0",
        "any": "None",
        # New types for v0.3.0
        "list": "[]",
        "object": "{}",
        "dict": "{}",
        "array": "[]",
    }
    return defaults.get(yaml_type, "None")


class PromptSpec:
    """A prompt method as seen through the generated API.

    The same method name can be reached through several branches of the prompt
    tree, so variables are unioned and routing parameters are grouped by the
    parameter names they require. Each group becomes one ``@overload``.
    """

    def __init__(self, name: str) -> None:
        """Initialize an empty spec.

        Args:
            name: Attribute name of the prompt
        """
        self.name = name
        # (파라미터 이름 튜플) -> Signature
        self.signatures: dict[tuple[str, ...], Signature] = {}

    def add(
        self,
        description: str | None,
        variables: dict[str, dict[str, Any]],
        params: tuple[tuple[str, str | None], ...],
    ) -> None:
        """Merge one filesystem occurrence of this prompt into the spec.

        Occurrences that need the same routing parameters share a signature;
        their values and variables are unioned. Occurrences needing different
        parameters stay separate and become distinct overloads.

        Args:
            description: Description from the prompt frontmatter
            variables: Variables declared by the prompt
            params: Routing parameters traversed to reach it, as
                ``(param_name, value)`` pairs. ``value`` is None for the
                ``default/`` fallback subtree, which contributes no literal.
        """
        key = tuple(param for param, _ in params)
        signature = self.signatures.get(key)
        if signature is None:
            signature = Signature(key)
            self.signatures[key] = signature
        signature.merge(description, variables, params)


class Signature:
    """One overload of a prompt: a fixed set of routing parameters."""

    def __init__(self, params: tuple[str, ...]) -> None:
        """Initialize an empty signature.

        Args:
            params: Routing parameter names, in traversal order
        """
        self.params = params
        self.values: dict[str, set[str]] = {name: set() for name in params}
        self.variables: dict[str, dict[str, Any]] = {}
        self.description: str | None = None
        # 설명을 default/ 폴백 브랜치에서 가져왔는지. 실제 값을 가진 브랜치의
        # 설명이 나타나면 그쪽으로 교체한다.
        self._description_is_fallback = True

    def merge(
        self,
        description: str | None,
        variables: dict[str, dict[str, Any]],
        params: tuple[tuple[str, str | None], ...],
    ) -> None:
        """Fold another occurrence into this signature.

        Args:
            description: Description from the prompt frontmatter
            variables: Variables declared by the prompt
            params: Routing parameters with the value taken at each level
        """
        from_fallback = any(value is None for _, value in params)

        if description and (
            self.description is None
            or (self._description_is_fallback and not from_fallback)
        ):
            self.description = description
            self._description_is_fallback = from_fallback

        for var_name, var_info in variables.items():
            self.variables.setdefault(var_name, var_info)

        for param, value in params:
            if value is not None:
                self.values[param].add(value)


class ApiNode:
    """A node of the generated API surface (one proxy class)."""

    def __init__(self) -> None:
        """Initialize an empty node."""
        self.children: dict[str, ApiNode] = {}
        self.prompts: dict[str, PromptSpec] = {}

    def child(self, name: str) -> ApiNode:
        """Get or create a child node.

        Args:
            name: Attribute name of the child

        Returns:
            The child node
        """
        return self.children.setdefault(name, ApiNode())

    def prompt(self, name: str) -> PromptSpec:
        """Get or create a prompt spec.

        Args:
            name: Attribute name of the prompt

        Returns:
            The prompt spec
        """
        if name not in self.prompts:
            self.prompts[name] = PromptSpec(name)
        return self.prompts[name]


class TypeStubGenerator:
    """Generator for Python type stub files."""

    def __init__(self, prompts_dir: Path, encoding: str = "utf-8") -> None:
        """Initialize generator.

        Args:
            prompts_dir: Directory containing prompt files
            encoding: File encoding
        """
        self.prompts_dir = prompts_dir.resolve()
        self.encoding = encoding
        self.needs_union = False
        self.needs_any = False
        self.needs_literal = False
        self.needs_overload = False
        self.warnings: list[str] = []
        self._class_names: dict[tuple[str, ...], str] = {}
        self._used_class_names: set[str] = set()

    # -- 파일시스템 스캔 (하위호환 API) ---------------------------------

    def scan_directory(self, current_dir: Path, depth: int = 0) -> dict[str, Any]:
        """Scan directory structure recursively.

        Kept for backwards compatibility; the stub generation itself uses
        :meth:`build_api_node`.

        Args:
            current_dir: Directory to scan
            depth: Current recursion depth

        Returns:
            Dictionary representing directory structure
        """
        structure: dict[str, Any] = {}

        if not current_dir.is_dir() or depth > MAX_SCAN_DEPTH:
            return structure

        for item in sorted(current_dir.iterdir()):
            if item.name.startswith("."):
                continue

            if item.is_dir():
                structure[item.name] = self.scan_directory(item, depth + 1)
            elif item.suffix == ".md":
                structure[item.stem] = self._parse_prompt_file(item)

        return structure

    def _parse_prompt_file(self, file_path: Path) -> dict[str, Any]:
        """Parse a prompt file to extract metadata.

        Args:
            file_path: Path to prompt file

        Returns:
            Dictionary with file metadata
        """
        try:
            content = file_path.read_text(encoding=self.encoding)
            metadata, _ = parse_metadata(content)

            return {
                "type": "file",
                "description": metadata.description,
                "variables": {
                    var_name: {
                        "type": var_info.type,
                        "description": var_info.description,
                    }
                    for var_name, var_info in metadata.variables.items()
                },
            }
        except Exception:
            # If parsing fails, return minimal info
            return {
                "type": "file",
                "description": None,
                "variables": {},
            }

    # -- API 트리 구성 ---------------------------------------------------

    def build_api_node(
        self,
        directory: Path,
        params: tuple[tuple[str, str | None], ...] = (),
        node: ApiNode | None = None,
        depth: int = 0,
    ) -> ApiNode:
        """Build the API surface for a directory.

        Walks static directories as nested proxies and flattens ``[param]``
        directories by merging every value subtree into the current node.

        Args:
            directory: Directory to scan
            params: Routing parameters traversed to reach this directory
            node: Node to merge into; a new one is created when omitted
            depth: Current recursion depth

        Returns:
            The populated node
        """
        node = node if node is not None else ApiNode()
        if not directory.is_dir() or depth > MAX_SCAN_DEPTH:
            return node

        entries = [
            item for item in directory.iterdir() if not item.name.startswith(".")
        ]
        self._warn_on_case_collisions(directory, entries)

        for item in sorted(entries, key=lambda path: path.name):
            if item.is_dir():
                if is_dynamic_dir(item.name):
                    self._merge_dynamic_dir(item, params, node, depth)
                else:
                    self.build_api_node(
                        item,
                        params,
                        node.child(to_attribute_name(item.name)),
                        depth + 1,
                    )
            elif item.suffix == ".md":
                info = self._parse_prompt_file(item)
                node.prompt(to_attribute_name(item.stem)).add(
                    info["description"], info["variables"], params
                )

        return node

    def _merge_dynamic_dir(
        self,
        dynamic_dir: Path,
        params: tuple[tuple[str, str | None], ...],
        node: ApiNode,
        depth: int,
    ) -> None:
        """Merge every branch of a ``[param]`` directory into a node.

        Args:
            dynamic_dir: The ``[param]`` directory
            params: Routing parameters traversed so far
            node: Node the branches are merged into
            depth: Current recursion depth
        """
        param_name = extract_param_name(dynamic_dir.name)
        self.needs_literal = True

        for item in sorted(dynamic_dir.iterdir(), key=lambda path: path.name):
            if item.name.startswith(".") or not item.is_dir():
                # default.md 는 이름을 가리지 않는 런타임 폴백이라 API 표면이 없다.
                continue

            # default/ 는 폴백 서브트리이므로 선택 가능한 값에는 넣지 않는다.
            value = None if normalize_name(item.name) == DEFAULT_NAME else item.name
            self.build_api_node(item, params + ((param_name, value),), node, depth + 1)

    def _warn_on_case_collisions(self, directory: Path, entries: list[Path]) -> None:
        """Record a warning for entries that differ only by case or normal form.

        Args:
            directory: Directory being scanned
            entries: Its entries
        """
        seen: dict[str, list[str]] = {}
        for item in entries:
            seen.setdefault(normalize_name(item.name), []).append(item.name)

        for names in seen.values():
            if len(names) > 1:
                listed = ", ".join(repr(name) for name in sorted(names))
                self.warnings.append(
                    f"{directory}: {listed} differ only by case or unicode "
                    "normal form; prompteer cannot resolve them portably."
                )

    # -- 스텁 생성 --------------------------------------------------------

    def generate_type_stub(self, output_path: Path) -> None:
        """Generate type stub file.

        Args:
            output_path: Path to output .pyi file
        """
        self.warnings.clear()
        self._class_names.clear()
        self._used_class_names.clear()
        self.needs_literal = False
        self.needs_overload = False

        root = self.build_api_node(self.prompts_dir)

        # 클래스 이름을 먼저 확정해야 상호 참조를 쓸 수 있다.
        self._assign_class_names(root, ())
        self._detect_overloads(root)

        body: list[str] = []
        self._emit_classes(root, (), body)

        lines = self._generate_header()
        lines.extend(body)
        lines.append(self._emit_root_class(root))
        lines.append("")
        lines.append(self._generate_factory_function())

        output_path.write_text("\n".join(lines), encoding=self.encoding)

        for warning in self.warnings:
            print(f"[prompteer] warning: {warning}", file=sys.stderr)

    def _assign_class_names(self, node: ApiNode, path: tuple[str, ...]) -> None:
        """Assign a unique proxy class name to every node.

        Args:
            node: Node to name
            path: Attribute path leading to the node
        """
        if path:
            base = "_" + "".join(part[:1].upper() + part[1:] for part in path) + "Proxy"
            name = base
            suffix = 2
            while name in self._used_class_names:
                name = f"{base}{suffix}"
                suffix += 1
            self._used_class_names.add(name)
            self._class_names[path] = name

        for child_name, child in node.children.items():
            self._assign_class_names(child, path + (child_name,))

    def _detect_overloads(self, node: ApiNode) -> None:
        """Set the overload import flag if any prompt needs several signatures.

        Args:
            node: Node to inspect
        """
        for spec in node.prompts.values():
            if len(spec.signatures) > 1:
                self.needs_overload = True
        for child in node.children.values():
            self._detect_overloads(child)

    def _emit_classes(
        self, node: ApiNode, path: tuple[str, ...], out: list[str]
    ) -> None:
        """Emit proxy classes for a node and its descendants, deepest first.

        Args:
            node: Node to emit
            path: Attribute path leading to the node
            out: Accumulated output lines
        """
        for child_name in sorted(node.children):
            self._emit_classes(node.children[child_name], path + (child_name,), out)

        if not path:
            return

        class_name = self._class_names[path]
        out.append(f"class {class_name}:")
        out.append(f'    """Proxy for {"/".join(path)}/ directory."""')
        out.append("")
        out.extend(self._emit_members(node, path))

    def _emit_members(self, node: ApiNode, path: tuple[str, ...]) -> list[str]:
        """Emit the properties and methods of a node.

        Args:
            node: Node to emit members for
            path: Attribute path leading to the node

        Returns:
            Member definition lines
        """
        lines: list[str] = []

        for child_name in sorted(node.children):
            if child_name in node.prompts:
                self.warnings.append(
                    f"{'/'.join(path + (child_name,))}: a directory and a prompt "
                    "file share this name; the directory wins."
                )
                node.prompts.pop(child_name)
            child_class = self._class_names[path + (child_name,)]
            lines.append("    @property")
            lines.append(f"    def {child_name}(self) -> {child_class}: ...")
            lines.append("")

        for prompt_name in sorted(node.prompts):
            lines.extend(self._emit_prompt(node.prompts[prompt_name]))

        if not lines:
            lines.append("    pass")
            lines.append("")

        return lines

    def _emit_prompt(self, spec: PromptSpec) -> list[str]:
        """Emit the method (or overload set) for one prompt.

        Args:
            spec: Prompt specification

        Returns:
            Method definition lines
        """
        signatures = [spec.signatures[key] for key in sorted(spec.signatures)]
        overloaded = len(signatures) > 1

        lines: list[str] = []
        for signature in signatures:
            if overloaded:
                lines.append("    @overload")
            lines.extend(self._emit_signature(spec, signature))
        return lines

    def _emit_signature(self, spec: PromptSpec, signature: Signature) -> list[str]:
        """Emit a single method signature.

        Args:
            spec: Prompt specification
            signature: The overload to emit

        Returns:
            Method definition lines
        """
        params: list[str] = ["self"]
        for param in signature.params:
            params.append(f"{param}: {self._literal_type(signature.values[param])}")

        for var_name in sorted(signature.variables):
            var_info = signature.variables[var_name]
            var_type = get_python_type(var_info["type"])
            default_val = get_default_value(var_info["type"])
            params.append(f"{var_name}: {var_type} = {default_val}")

        params.append("**kwargs: Any")

        lines: list[str] = []
        if len(params) <= 3:
            lines.append(f"    def {spec.name}({', '.join(params)}) -> str:")
        else:
            lines.append(f"    def {spec.name}(")
            for index, param in enumerate(params):
                comma = "" if index == len(params) - 1 else ","
                lines.append(f"        {param}{comma}")
            lines.append("    ) -> str:")

        lines.extend(self._emit_docstring(signature))
        lines.append("        ...")
        lines.append("")
        return lines

    def _literal_type(self, values: set[str]) -> str:
        """Render the annotation for a routing parameter.

        Args:
            values: Available values; empty when only a ``default/`` subtree
                provides the prompt

        Returns:
            A ``Literal[...]`` annotation, or ``str`` when nothing is enumerable
        """
        if not values:
            return "str"
        self.needs_literal = True
        return f"Literal[{', '.join(f'{chr(34)}{v}{chr(34)}' for v in sorted(values))}]"

    def _emit_docstring(self, signature: Signature) -> list[str]:
        """Emit the docstring for a method signature.

        Args:
            signature: The overload being emitted

        Returns:
            Docstring lines
        """
        lines = ['        """']
        if signature.description:
            lines.append(f"        {signature.description}")
            lines.append("")

        if signature.params or signature.variables:
            lines.append("        Args:")
            for param in signature.params:
                available = sorted(signature.values[param])
                listed = ", ".join(available) if available else "(fallback only)"
                lines.append(
                    f"            {param}: Dynamic routing parameter. "
                    f"Available values: {listed}"
                )
            for var_name in sorted(signature.variables):
                var_desc = signature.variables[var_name].get("description", "")
                lines.append(f"            {var_name}: {var_desc}")
            lines.append("            **kwargs: Additional variables")

        lines.append('        """')
        return lines

    def _emit_root_class(self, root: ApiNode) -> str:
        """Emit the main Prompteer class.

        Args:
            root: Root API node

        Returns:
            Class definition as string
        """
        lines: list[str] = []
        lines.append("class Prompteer:")
        lines.append('    """prompteer\'s main class')
        lines.append("")
        lines.append("    Args:")
        lines.append("        base_path: Root directory containing prompt files")
        lines.append("        encoding: File encoding (default: 'utf-8')")
        lines.append('    """')
        lines.append("")
        lines.extend(self._emit_members(root, ()))
        return "\n".join(lines)

    def _generate_header(self) -> list[str]:
        """Generate file header.

        Returns:
            List of header lines
        """
        lines = [
            '"""',
            "Auto-generated type stubs for prompteer prompts.",
            "DO NOT EDIT THIS FILE MANUALLY.",
            "",
            "Generated by: prompteer generate-types",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Source directory: {self.prompts_dir}",
            '"""',
            "",
            "from typing import Any",
            "from typing import Union",
        ]

        if self.needs_literal:
            lines.append("from typing import Literal")
        if self.needs_overload:
            lines.append("from typing import overload")

        lines.append("")
        return lines

    def _to_class_name(self, name: str) -> str:
        """Convert name to class name format.

        Args:
            name: Name to convert

        Returns:
            Class name
        """
        return "".join(word.capitalize() for word in name.replace("-", " ").split())

    def _generate_factory_function(self) -> str:
        """Generate create_prompts factory function stub.

        Returns:
            Factory function definition as string
        """
        lines: list[str] = []

        lines.append(
            'def create_prompts(base_path: str, encoding: str = "utf-8") -> Prompteer:'
        )
        lines.append(
            '    """Create a Prompteer instance with automatic type inference.'
        )
        lines.append("")
        lines.append(
            "    This is a convenience factory function that creates a Prompteer instance"
        )
        lines.append("    and returns it with proper type hints.")
        lines.append("")
        lines.append("    Usage:")
        lines.append("        >>> from prompts import create_prompts")
        lines.append('        >>> prompts = create_prompts("./prompts")')
        lines.append(
            '        >>> prompts.chat.system(role="...", personality="...")  # Full autocomplete!'
        )
        lines.append("")
        lines.append("    Args:")
        lines.append("        base_path: Root directory containing prompt files")
        lines.append(
            "        encoding: File encoding for reading prompts (default: 'utf-8')"
        )
        lines.append("")
        lines.append("    Returns:")
        lines.append("        Prompteer instance with full type hints")
        lines.append('    """')
        lines.append("    ...")

        return "\n".join(lines)
