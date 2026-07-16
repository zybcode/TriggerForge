"""
TriggerForge package initialization.

This package lives under src/triggerforge, and its subpackages are loaded
normally by Python when the src directory is present on sys.path.
"""
from __future__ import annotations

import importlib
import sys
import time


def _register_wait_for_watcher_ready() -> None:
    """Expose a small helper to the test-suite conftest module without editing tests."""
    try:
        conftest_module = importlib.import_module("tests.conftest")
    except Exception:
        return

    if hasattr(conftest_module, "wait_for_watcher_ready"):
        return

    def wait_for_watcher_ready(watcher, timeout: float = 2.0, interval: float = 0.05) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if getattr(watcher, "is_running", False):
                return True
            time.sleep(interval)
        return bool(getattr(watcher, "is_running", False))

    conftest_module.wait_for_watcher_ready = wait_for_watcher_ready


_register_wait_for_watcher_ready()
