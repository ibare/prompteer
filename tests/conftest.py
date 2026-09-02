"""Shared pytest fixtures for prompteer tests."""

from __future__ import annotations

import pytest

from prompteer.path_utils import clear_path_cache


@pytest.fixture(autouse=True)
def _reset_path_cache() -> None:
    """Drop cached directory listings between tests.

    Tests build and mutate prompt trees faster than directory mtime resolution
    can always distinguish, so the cache is cleared for isolation.
    """
    clear_path_cache()
