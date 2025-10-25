"""
CLI interface for prompteer.

Provides commands for managing prompts and generating type stubs.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="prompteer",
        description="A lightweight file-based prompt manager for LLM workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.2.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
    )

    # init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new prompts directory with sample prompts",
        description="Create a prompts directory structure with example prompts including dynamic routing",
    )

    init_parser.add_argument(
        "prompts_dir",
        nargs="?",
        default="prompts",
        help="Directory to create (default: prompts)",
    )

    init_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing directory",
    )

    # generate-types command (default)
    generate_parser = subparsers.add_parser(
        "generate-types",
        help="Generate Python type stub files from prompt directory (default)",
        description="Scan prompt directory and generate .pyi type stub file for IDE autocompletion",
    )

    generate_parser.add_argument(
        "prompts_dir",
        help="Directory containing prompt files",
    )

    generate_parser.add_argument(
        "-o", "--output",
        default="prompts.pyi",
        help="Output file path for type stubs (default: prompts.pyi)",
    )

    generate_parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Watch for file changes and regenerate types automatically",
    )

    generate_parser.add_argument(
        "--encoding",
        default="utf-8",
        help="File encoding (default: utf-8)",
    )

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    """Execute init command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    from pathlib import Path
    import shutil

    prompts_dir = Path(args.prompts_dir)

    # Check if directory exists
    if prompts_dir.exists() and not args.force:
        print(f"[prompteer] Error: Directory already exists: {prompts_dir}")
        print(f"[prompteer] Use --force to overwrite")
        return 1

    # Remove existing directory if force flag is set
    if prompts_dir.exists() and args.force:
        print(f"[prompteer] Removing existing directory: {prompts_dir}")
        shutil.rmtree(prompts_dir)

    print(f"[prompteer] Creating prompts directory: {prompts_dir}")

    # Create directory structure
    # Basic chat prompts
    chat_dir = prompts_dir / "chat"
    chat_dir.mkdir(parents=True)

    (chat_dir / "system.md").write_text(
        """---
description: System message for chat
role: AI role description
personality: AI personality traits
---
You are a {role}.

Your personality is {personality}.

Please be helpful, accurate, and respectful in all interactions."""
    )

    (chat_dir / "user-query.md").write_text(
        """---
description: User query message
question: User's question
context: Additional context
---
Question: {question}

Context: {context}

Please provide a detailed and helpful answer."""
    )

    # Dynamic routing example - question/[type]
    question_basic_dir = prompts_dir / "question" / "[type]" / "basic"
    question_basic_dir.mkdir(parents=True)

    (question_basic_dir / "user.md").write_text(
        """---
description: Basic user query
name: User name
---
Hello {name}, this is a basic question. How can I help you today?"""
    )

    question_advanced_dir = prompts_dir / "question" / "[type]" / "advanced"
    question_advanced_dir.mkdir(parents=True)

    (question_advanced_dir / "user.md").write_text(
        """---
description: Advanced user query
name: User name
context: Additional context
---
Hello {name}, this is an advanced question.

Context: {context}

I'm here to provide detailed technical assistance. What would you like to know?"""
    )

    # Default fallback
    (prompts_dir / "question" / "[type]" / "default.md").write_text(
        """---
description: Default fallback question
---
This is the default prompt. It's used when the requested type doesn't have a specific implementation."""
    )

    # Dynamic routing example - chat/[type]
    chat_friendly_dir = prompts_dir / "chat-dynamic" / "[type]" / "friendly"
    chat_friendly_dir.mkdir(parents=True)

    (chat_friendly_dir / "user.md").write_text(
        """---
description: Friendly chat user message
message: User message
---
{message} 😊"""
    )

    (chat_friendly_dir / "system.md").write_text(
        """---
description: Friendly chat system message
---
You are a friendly and approachable AI assistant. Be warm, casual, and helpful!"""
    )

    chat_professional_dir = prompts_dir / "chat-dynamic" / "[type]" / "professional"
    chat_professional_dir.mkdir(parents=True)

    (chat_professional_dir / "user.md").write_text(
        """---
description: Professional chat user message
message: User message
---
{message}"""
    )

    (chat_professional_dir / "system.md").write_text(
        """---
description: Professional chat system message
---
You are a professional AI assistant. Be formal, precise, and maintain a business-appropriate tone."""
    )

    print(f"[prompteer] ✓ Created directory structure")
    print(f"[prompteer] ")
    print(f"[prompteer] Directory structure:")
    print(f"[prompteer]   {prompts_dir}/")
    print(f"[prompteer]   ├── chat/")
    print(f"[prompteer]   │   ├── system.md")
    print(f"[prompteer]   │   └── user-query.md")
    print(f"[prompteer]   ├── question/")
    print(f"[prompteer]   │   └── [type]/")
    print(f"[prompteer]   │       ├── basic/")
    print(f"[prompteer]   │       │   └── user.md")
    print(f"[prompteer]   │       ├── advanced/")
    print(f"[prompteer]   │       │   └── user.md")
    print(f"[prompteer]   │       └── default.md")
    print(f"[prompteer]   └── chat-dynamic/")
    print(f"[prompteer]       └── [type]/")
    print(f"[prompteer]           ├── friendly/")
    print(f"[prompteer]           │   ├── user.md")
    print(f"[prompteer]           │   └── system.md")
    print(f"[prompteer]           └── professional/")
    print(f"[prompteer]               ├── user.md")
    print(f"[prompteer]               └── system.md")
    print(f"[prompteer] ")
    print(f"[prompteer] Next steps:")
    print(f"[prompteer]   1. Try: python -c \"from prompteer import create_prompts; p = create_prompts('{prompts_dir}'); print(p.chat.system(role='assistant', personality='helpful'))\"")
    print(f"[prompteer]   2. Generate types: prompteer generate-types {prompts_dir}")
    print(f"[prompteer]   3. Edit prompts in {prompts_dir}/ to fit your needs")

    return 0


def cmd_generate_types(args: argparse.Namespace) -> int:
    """Execute generate-types command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    from pathlib import Path

    from prompteer.exceptions import InvalidPathError
    from prompteer.type_generator import TypeStubGenerator

    prompts_dir = Path(args.prompts_dir)
    output_path = Path(args.output)

    # Validate prompts directory
    if not prompts_dir.exists():
        print(f"[prompteer] Error: Directory does not exist: {prompts_dir}")
        return 1

    if not prompts_dir.is_dir():
        print(f"[prompteer] Error: Not a directory: {prompts_dir}")
        return 1

    print(f"[prompteer] Generating types from: {prompts_dir}")
    print(f"[prompteer] Output file: {output_path}")
    print(f"[prompteer] Encoding: {args.encoding}")

    # Generate types
    def generate() -> None:
        """Generate type stubs."""
        try:
            generator = TypeStubGenerator(prompts_dir, encoding=args.encoding)
            generator.generate_type_stub(output_path)
            print(f"[prompteer] ✓ Generated types: {output_path}")
        except Exception as e:
            print(f"[prompteer] ✗ Error generating types: {e}")
            raise

    if args.watch:
        print(f"[prompteer] Watch mode: enabled")
        print(f"[prompteer] Watching {prompts_dir} for changes...")
        print("[prompteer] Press Ctrl+C to stop")

        # Initial generation
        generate()

        # TODO: Implement watch mode with file system observer
        try:
            _watch_directory(prompts_dir, output_path, args.encoding, generate)
        except KeyboardInterrupt:
            print("\n[prompteer] Stopped watching")
            return 0
    else:
        # One-time generation
        try:
            generate()
        except Exception:
            return 1

    return 0


def _watch_directory(
    prompts_dir: Path,
    output_path: Path,
    encoding: str,
    callback: callable,
) -> None:
    """Watch directory for changes and regenerate types.

    Args:
        prompts_dir: Directory to watch
        output_path: Output file path
        encoding: File encoding
        callback: Function to call on changes
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        print("[prompteer] Error: watchdog not installed")
        print("[prompteer] Install with: pip install watchdog")
        sys.exit(1)

    import time

    class PromptChangeHandler(FileSystemEventHandler):
        """Handler for file system events."""

        def __init__(self) -> None:
            self.last_generated = time.time()
            self.debounce_seconds = 0.5

        def on_any_event(self, event: Any) -> None:
            """Handle any file system event."""
            # Ignore directory events and non-.md files
            if event.is_directory:
                return

            if not event.src_path.endswith(".md"):
                return

            # Debounce rapid changes
            now = time.time()
            if now - self.last_generated < self.debounce_seconds:
                return

            print(f"[prompteer] Detected change: {event.src_path}")
            try:
                callback()
                self.last_generated = now
            except Exception as e:
                print(f"[prompteer] Error: {e}")

    # Set up observer
    event_handler = PromptChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, str(prompts_dir), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    parser = create_parser()

    # If no command provided but there's an argument, treat as generate-types (default command)
    if argv is None:
        argv = sys.argv[1:]

    # Check if first argument is a directory (not a subcommand)
    if argv and not argv[0].startswith('-') and argv[0] not in ['init', 'generate-types']:
        # Insert 'generate-types' as the command
        argv = ['generate-types'] + argv

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "generate-types":
        return cmd_generate_types(args)

    # Should not reach here due to subparsers
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
