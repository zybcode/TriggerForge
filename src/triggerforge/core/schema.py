"""
Pydantic schemas for TriggerForge configuration validation.

Defines `TriggerForgeConfigSchema`, `WatchFolderSchema` and strategy model used
by the unit tests. Uses simple validations for required fields and numeric bounds.
"""
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
