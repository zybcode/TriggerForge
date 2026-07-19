# TriggerForge - Event-driven directory orchestration engine.
# Copyright (C) 2026  [zybcode]
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Top-level package shim to expose `src/triggerforge` during testing.

This file ensures that running `python -m triggerforge.cli` from the
repository root will resolve to the implementation under `src/triggerforge`,
and that `triggerforge.core` resolves to `src/core`.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

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
