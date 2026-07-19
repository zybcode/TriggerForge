# TriggerForge - Event-driven directory orchestration engine.
# Copyright (C) 2026  [zybcode]

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# TriggerForge main entrypoint exposed as triggerforge.main.

# Pydantic schemas for TriggerForge configuration validation.

# Defines `TriggerForgeConfigSchema`, `WatchFolderSchema` and strategy model used
# by the unit tests. Uses simple validations for required fields and numeric bounds.


from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategySchema(BaseModel):
    plugin_name: str
    plugin_version: str
    timeout: int = Field(30, gt=0)
    params: Dict[str, Any] = Field(default_factory=dict)
    python_path: Optional[str] = None


class WatchFolderSchema(BaseModel):
    path: str
    success_path: str
    error_path: str
    concurrency: int = Field(1, gt=0)
    strategies: List[StrategySchema]


class TriggerForgeConfigSchema(BaseModel):
    watch_folders: List[WatchFolderSchema]
