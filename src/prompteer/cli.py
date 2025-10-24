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
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
    )

    # generate-types command
    generate_parser = subparsers.add_parser(
        "generate-types",
        help="Generate Python type stub files from prompt directory",
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
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "generate-types":
        return cmd_generate_types(args)

    # Should not reach here due to subparsers
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
