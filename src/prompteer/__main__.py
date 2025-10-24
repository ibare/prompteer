"""
Allow running prompteer as a module: python -m prompteer
"""

from __future__ import annotations

import sys

from prompteer.cli import main

if __name__ == "__main__":
    sys.exit(main())
