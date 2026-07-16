"""Top-level package shim to expose `src/triggerforge` during testing.

This file ensures that running `python -m triggerforge.cli` from the
repository root will resolve to the implementation under `src/triggerforge`,
and that `triggerforge.core` resolves to `src/core`.
"""
from __future__ import annotations

from pathlib import Path
import sys
import types

pkg_root = Path(__file__).resolve().parent
src_root = pkg_root.parent / "src"
impl = src_root / "triggerforge"
core_path = src_root / "core"

if impl.exists():
    sys.path.insert(0, str(src_root))
    __path__.insert(0, str(impl))

if core_path.exists():
    core_pkg = types.ModuleType("triggerforge.core")
    core_pkg.__path__ = [str(core_path)]
    sys.modules.setdefault("triggerforge.core", core_pkg)
    globals()["core"] = core_pkg
