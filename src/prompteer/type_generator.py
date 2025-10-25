"""
Type stub generator for prompteer.

Generates .pyi files from prompt directories for IDE autocompletion.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from prompteer.metadata import parse_metadata
from prompteer.path_utils import extract_param_name, is_dynamic_dir, kebab_to_camel


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
    """
    type_mapping = {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "number": "Union[int, float]",
        "any": "Any",
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
    """
    defaults = {
        "str": '""',
        "int": "0",
        "float": "0.0",
        "bool": "False",
        "number": "0",
        "any": "None",
    }
    return defaults.get(yaml_type, "None")


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

    def scan_directory(self, current_dir: Path, depth: int = 0) -> dict[str, Any]:
        """Scan directory structure recursively.

        Args:
            current_dir: Directory to scan
            depth: Current recursion depth

        Returns:
            Dictionary representing directory structure
        """
        structure: dict[str, Any] = {}

        if not current_dir.is_dir():
            return structure

        for item in sorted(current_dir.iterdir()):
            if item.name.startswith("."):
                continue

            if item.is_dir():
                # Check if this is a dynamic directory
                if is_dynamic_dir(item.name):
                    # Dynamic directory - scan for available values and prompts
                    structure[item.name] = self._scan_dynamic_dir(item)
                else:
                    # Regular subdirectory - recursively scan
                    structure[item.name] = self.scan_directory(item, depth + 1)
            elif item.suffix == ".md":
                # Prompt file
                var_name = item.stem
                structure[var_name] = self._parse_prompt_file(item)

        return structure

    def _scan_dynamic_dir(self, dynamic_dir: Path) -> dict[str, Any]:
        """Scan a dynamic directory and extract available values and prompts.

        Args:
            dynamic_dir: Path to dynamic directory (e.g., [type])

        Returns:
            Dictionary with dynamic directory metadata
        """
        param_name = extract_param_name(dynamic_dir.name)
        available_values: list[str] = []
        prompts: dict[str, dict[str, Any]] = {}

        # Scan for value directories and prompts
        for item in sorted(dynamic_dir.iterdir()):
            if item.name.startswith("."):
                continue

            if item.is_dir():
                # Value directory (e.g., basic/, advanced/)
                available_values.append(item.name)

                # Scan for prompt files inside value directory
                for prompt_file in sorted(item.glob("*.md")):
                    prompt_name = prompt_file.stem

                    if prompt_name not in prompts:
                        # Parse metadata from this file
                        file_info = self._parse_prompt_file(prompt_file)
                        prompts[prompt_name] = {
                            "type": "dynamic",
                            "param": param_name,
                            "values": [item.name],
                            "description": file_info.get("description"),
                            "variables": file_info.get("variables", {}),
                        }
                    else:
                        # Add this value to the existing prompt
                        prompts[prompt_name]["values"].append(item.name)

            elif item.suffix == ".md" and item.stem == "default":
                # default.md file - this is a fallback
                # We don't need to add it to prompts, it's handled at runtime
                pass

        # Mark that we need Literal import
        if available_values:
            self.needs_literal = True

        return {
            "type": "dynamic_directory",
            "param": param_name,
            "available_values": available_values,
            "prompts": prompts,
        }

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

    def generate_type_stub(self, output_path: Path) -> None:
        """Generate type stub file.

        Args:
            output_path: Path to output .pyi file
        """
        # Scan directory structure
        structure = self.scan_directory(self.prompts_dir)

        # Generate type stub content
        lines = self._generate_header()
        lines.extend(self._generate_classes(structure))
        lines.append(self._generate_main_class(structure))
        lines.append("")
        lines.append(self._generate_factory_function())

        # Write to file
        output_path.write_text("\n".join(lines), encoding=self.encoding)

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
        ]

        # Add Union import if needed (we'll check this during generation)
        # For now, always add it since we might have 'number' type
        lines.append("from typing import Union")

        # Add Literal import if needed for dynamic routing
        if self.needs_literal:
            lines.append("from typing import Literal")

        lines.append("")

        return lines

    def _generate_classes(
        self, structure: dict[str, Any], parent_name: str = ""
    ) -> list[str]:
        """Generate proxy classes recursively.

        Args:
            structure: Directory structure dictionary
            parent_name: Parent class name prefix

        Returns:
            List of class definition lines
        """
        lines: list[str] = []

        # Process subdirectories first
        for name, content in sorted(structure.items()):
            if isinstance(content, dict) and content.get("type") == "file":
                continue  # Skip files for now

            # Check if this is a dynamic directory
            if isinstance(content, dict) and content.get("type") == "dynamic_directory":
                # Don't generate a class for dynamic directories
                # Their prompts will be added directly to the parent class
                continue

            # This is a regular directory
            class_name = f"_{self._to_class_name(parent_name + name.capitalize())}Proxy"

            # Recursively generate classes for subdirectories
            if isinstance(content, dict):
                lines.extend(self._generate_classes(content, parent_name + name.capitalize()))

            # Generate this class
            lines.append(f"class {class_name}:")
            lines.append(f'    """Proxy for {name}/ directory."""')
            lines.append("")

            # Add properties for subdirectories and methods for files
            has_members = False
            for sub_name, sub_content in sorted(content.items()):
                if isinstance(sub_content, dict):
                    if sub_content.get("type") == "file":
                        # File - add method
                        lines.extend(self._generate_method(sub_name, sub_content))
                        has_members = True
                    elif sub_content.get("type") == "dynamic_directory":
                        # Dynamic directory - add methods for its prompts
                        prompts = sub_content.get("prompts", {})
                        for prompt_name, prompt_info in sorted(prompts.items()):
                            lines.extend(self._generate_method(prompt_name, prompt_info))
                            has_members = True
                    else:
                        # Regular directory - add property
                        sub_class_name = f"_{self._to_class_name(parent_name + name.capitalize() + sub_name.capitalize())}Proxy"
                        lines.append("    @property")
                        lines.append(f"    def {kebab_to_camel(sub_name)}(self) -> {sub_class_name}: ...")
                        lines.append("")
                        has_members = True

            if not has_members:
                lines.append("    pass")
                lines.append("")

        return lines

    def _generate_method(self, name: str, file_info: dict[str, Any]) -> list[str]:
        """Generate method for a prompt file.

        Args:
            name: File name (without extension)
            file_info: File metadata

        Returns:
            List of method definition lines
        """
        lines: list[str] = []
        variables = file_info.get("variables", {})
        description = file_info.get("description")

        # Build method signature
        method_name = kebab_to_camel(name)
        params: list[str] = ["self"]

        # Check if this is a dynamic prompt
        if file_info.get("type") == "dynamic":
            # Add dynamic parameter with Literal type
            param_name = file_info.get("param")
            values = file_info.get("values", [])
            if values:
                # Create Literal type with all available values
                literal_values = ", ".join(f'"{v}"' for v in sorted(values))
                params.append(f"{param_name}: Literal[{literal_values}]")

        # Add parameters with types and defaults
        for var_name, var_info in sorted(variables.items()):
            var_type = get_python_type(var_info["type"])
            default_val = get_default_value(var_info["type"])
            params.append(f"{var_name}: {var_type} = {default_val}")

        # Always add **kwargs
        params.append("**kwargs: Any")

        # Format parameters (one per line if many)
        if len(params) <= 3:
            param_str = ", ".join(params)
            lines.append(f"    def {method_name}({param_str}) -> str:")
        else:
            lines.append(f"    def {method_name}(")
            for i, param in enumerate(params):
                if i == 0:
                    lines.append(f"        {param},")
                elif i == len(params) - 1:
                    lines.append(f"        {param}")
                else:
                    lines.append(f"        {param},")
            lines.append("    ) -> str:")

        # Add docstring
        lines.append('        """')
        if description:
            lines.append(f"        {description}")
            lines.append("")

        # Add dynamic parameter documentation if applicable
        if file_info.get("type") == "dynamic":
            param_name = file_info.get("param")
            values = file_info.get("values", [])
            lines.append("        Args:")
            lines.append(f"            {param_name}: Dynamic routing parameter. Available values: {', '.join(sorted(values))}")
            if variables:
                for var_name, var_info in sorted(variables.items()):
                    var_desc = var_info.get("description", "")
                    lines.append(f"            {var_name}: {var_desc}")
            lines.append("            **kwargs: Additional variables")
        elif variables:
            lines.append("        Args:")
            for var_name, var_info in sorted(variables.items()):
                var_desc = var_info.get("description", "")
                lines.append(f"            {var_name}: {var_desc}")
            lines.append("            **kwargs: Additional variables")

        lines.append('        """')
        lines.append("        ...")
        lines.append("")

        return lines

    def _generate_main_class(self, structure: dict[str, Any]) -> str:
        """Generate main Prompteer class.

        Args:
            structure: Directory structure

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

        # Add properties for top-level directories and methods for files
        for name, content in sorted(structure.items()):
            if isinstance(content, dict):
                if content.get("type") == "file":
                    # Top-level file - add method
                    lines.extend(
                        [
                            "    " + line if line else ""
                            for line in self._generate_method(name, content)
                        ]
                    )
                elif content.get("type") == "dynamic_directory":
                    # Top-level dynamic directory - add methods for its prompts
                    prompts = content.get("prompts", {})
                    for prompt_name, prompt_info in sorted(prompts.items()):
                        lines.extend(
                            [
                                "    " + line if line else ""
                                for line in self._generate_method(prompt_name, prompt_info)
                            ]
                        )
                else:
                    # Regular directory - add property
                    class_name = f"_{self._to_class_name(name.capitalize())}Proxy"
                    lines.append("    @property")
                    lines.append(f"    def {kebab_to_camel(name)}(self) -> {class_name}: ...")
                    lines.append("")

        return "\n".join(lines)

    def _to_class_name(self, name: str) -> str:
        """Convert name to class name format.

        Args:
            name: Name to convert

        Returns:
            Class name
        """
        # Remove hyphens and capitalize
        return "".join(word.capitalize() for word in name.replace("-", " ").split())

    def _generate_factory_function(self) -> str:
        """Generate create_prompts factory function stub.

        Returns:
            Factory function definition as string
        """
        lines: list[str] = []

        lines.append("def create_prompts(base_path: str, encoding: str = \"utf-8\") -> Prompteer:")
        lines.append('    """Create a Prompteer instance with automatic type inference.')
        lines.append("")
        lines.append("    This is a convenience factory function that creates a Prompteer instance")
        lines.append("    and returns it with proper type hints.")
        lines.append("")
        lines.append("    Usage:")
        lines.append("        >>> from prompts import create_prompts")
        lines.append('        >>> prompts = create_prompts("./prompts")')
        lines.append('        >>> prompts.chat.system(role="...", personality="...")  # Full autocomplete!')
        lines.append("")
        lines.append("    Args:")
        lines.append("        base_path: Root directory containing prompt files")
        lines.append("        encoding: File encoding for reading prompts (default: 'utf-8')")
        lines.append("")
        lines.append("    Returns:")
        lines.append("        Prompteer instance with full type hints")
        lines.append('    """')
        lines.append("    ...")

        return "\n".join(lines)
