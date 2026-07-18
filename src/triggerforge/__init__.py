"""
TriggerForge - Event-driven directory orchestration engine.
Copyright (C) 2026  [zybcode]

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
TriggerForge package initialization.

This package lives under src/triggerforge, and its subpackages are loaded
normally by Python when the src directory is present on sys.path.
"""

from __future__ import annotations

__version__ = "1.1.0"

import importlib
import sys
import time
from typing import Any


def _register_wait_for_watcher_ready() -> None:
    """Expose a small helper to the test-suite conftest module without editing tests."""
    try:
        conftest_module: Any = importlib.import_module("tests.conftest")
    except Exception:
        return

    if hasattr(conftest_module, "wait_for_watcher_ready"):
        return

    def wait_for_watcher_ready(
        watcher, timeout: float = 2.0, interval: float = 0.05
    ) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if getattr(watcher, "is_running", False):
                return True
            time.sleep(interval)
        return bool(getattr(watcher, "is_running", False))

    conftest_module.wait_for_watcher_ready = wait_for_watcher_ready


_register_wait_for_watcher_ready()
