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
#
# v1.2 变更（依据 docs/zh/dev_plan_v1.2.md）：
#   - StrategySchema 新增 priority 枚举（high/standard/low）、
#     allow_override_timeout 开关与 metadata 商业扩展槽。
#   - 双重约束：allow_override_timeout=True 必须搭配 priority="high"，
#     违规在启动预检阶段抛 ValueError 拒绝启动（资源防锁死机制）。
#   - 迁移兼容（migration_v1.2.md）：
#       * 全局 timeout → max_execution_timeout（自动映射 + DeprecationWarning）
#       * strategies[].timeout → strategies[].strategy.timeout 嵌套对象
#         （旧扁平写法兼容 + DeprecationWarning，v1.4 移除）


from __future__ import annotations

import warnings
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# 优先级枚举（v1.2 对齐标准）：仅 high 支持超时覆盖
Priority = Literal["high", "standard", "low"]

# 迁移辅助：旧扁平 strategy 字段 → 新嵌套 strategy 对象允许承载的键
_STRATEGY_NESTED_KEYS = ("timeout", "priority", "allow_override_timeout")


def _warn_deprecated(field: str, replacement: str, removal: str) -> None:
    warnings.warn(
        f"配置项 '{field}' 已弃用，请改用 '{replacement}'（计划于 {removal} 移除）。"
        "参考 docs/zh/migration_v1.2.md 完成迁移。",
        DeprecationWarning,
        stacklevel=4,
    )


class StrategySchema(BaseModel):
    """插件策略（v1.2：优先级 + 超时覆盖豁免 + 商业扩展槽）。"""

    plugin_name: str
    # 版本号改为可选：未指定时视为不校验，降低配置门槛
    plugin_version: str = "0.0.0"
    timeout: int = Field(30, gt=0)
    params: dict[str, Any] = Field(default_factory=dict)
    python_path: str | None = None

    # ---- v1.2 新增 ----
    # 优先级枚举：high / standard / low（默认 standard）
    priority: Priority = "standard"
    # 超时覆盖豁免：仅允许 priority="high" 时开启（双重约束，见校验器）
    allow_override_timeout: bool = False
    # 商业扩展预留槽：数字签名 / License Hash / 客户授权信息。
    # v1.2 开源版仅占位，启动校验阶段忽略，保证向前兼容。
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _migrate_nested_strategy(cls, data: Any) -> Any:
        """迁移：strategies[].strategy 嵌套对象 → 扁平字段。

        新标准写法为嵌套对象；旧扁平 timeout 写法兼容但触发弃用告警。
        嵌套对象中的键优先于扁平字段。
        """
        if not isinstance(data, dict):
            return data
        nested = data.get("strategy")
        if isinstance(nested, dict):
            merged = {k: v for k, v in data.items() if k != "strategy"}
            for key in _STRATEGY_NESTED_KEYS:
                if key in nested:
                    merged[key] = nested[key]
            return merged
        if "timeout" in data:
            _warn_deprecated("strategies[].timeout", "strategy.timeout", "v1.4")
        return data

    @model_validator(mode="after")
    def _validate_timeout_override_privilege(self) -> StrategySchema:
        """双重约束（资源防锁死）：仅 priority="high" 可开启超时覆盖。"""
        if self.allow_override_timeout and self.priority != "high":
            raise ValueError(
                "双重约束违规：allow_override_timeout=true 时必须同时指定 "
                f'priority="high"（当前 priority="{self.priority}"）。'
                "standard 与 low 级别不支持超时覆盖。"
            )
        return self


class WatchFolderSchema(BaseModel):
    path: str
    success_path: str
    error_path: str
    concurrency: int = Field(1, gt=0)
    # 文件写入防抖等待秒数（事件产生后等待文件写入完成的时间窗口）
    debounce_seconds: float = Field(1.0, gt=0)
    strategies: list[StrategySchema]


class TriggerForgeConfigSchema(BaseModel):
    watch_folders: list[WatchFolderSchema]
    # 插件根目录：PipelineRunner 在该目录下查找 {plugin_name}/main.py
    plugin_directory: str = "./plugins"
    # 全局默认防抖秒数（可被每个 watch_folder 覆盖）
    debounce_seconds: float = Field(1.0, gt=0)
    # ---- v1.2 新增 ----
    # 全局执行超时硬上限（安全底线）。策略 timeout 超过该值时被钳制，
    # 除非策略同时满足 priority="high" 且 allow_override_timeout=true。
    max_execution_timeout: int | None = Field(default=None, gt=0)

    @model_validator(mode="before")
    @classmethod
    def _migrate_global_timeout(cls, data: Any) -> Any:
        """迁移：全局 timeout → max_execution_timeout（v1.4 移除旧键）。"""
        if isinstance(data, dict) and "timeout" in data:
            _warn_deprecated("timeout (全局)", "max_execution_timeout", "v1.4")
            if "max_execution_timeout" not in data:
                data = {**data, "max_execution_timeout": data["timeout"]}
            data = {k: v for k, v in data.items() if k != "timeout"}
        return data
