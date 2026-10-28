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

# TriggerForge - Pydantic Schema Unit Tests
# Author: zybcode
# Description: Unit tests for validating the strict config schemas (schema.py),
#             ensuring robust verification of custom parameters and system bounds.

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

# 假设核心 schema 模型导出为 TriggerForgeConfigSchema, WatchFolderSchema
from triggerforge.core.schema import TriggerForgeConfigSchema, WatchFolderSchema


def test_schema_valid_config(sample_config_dict: dict[str, Any]):
    """
    测试合法的完整配置字典解析。
    验证数据能被正确转换为强类型对象，且所有默认值与层级结构读取正常。
    """
    config = TriggerForgeConfigSchema(**sample_config_dict)

    # 验证全局配置
    assert len(config.watch_folders) == 1

    # 验证监控目录子配置
    folder = config.watch_folders[0]
    assert folder.path == "./storage/watch_folder"
    assert folder.success_path == "./storage/success_folder"
    assert folder.error_path == "./storage/error_folder"
    assert folder.concurrency == 2

    # 验证策略链子配置
    assert len(folder.strategies) == 1
    strategy = folder.strategies[0]
    assert strategy.plugin_name == "dummy_plugin"
    assert strategy.plugin_version == "1.0.0"
    assert strategy.timeout == 10
    assert strategy.params == {"mode": "test"}


def test_schema_missing_required_fields():
    """
    测试缺失必须字段时的错误拦截。
    """
    # 1. 缺失整个监控文件夹列表
    with pytest.raises(ValidationError) as exc_info:
        TriggerForgeConfigSchema()
    assert "watch_folders" in str(exc_info.value)

    # 2. 监控文件夹配置缺失关键的监控路径 `path`
    bad_folder_config: dict[str, Any] = {
        "watch_folders": [{"success_path": "./success", "error_path": "./error"}]
    }
    with pytest.raises(ValidationError) as exc_info:
        TriggerForgeConfigSchema(**bad_folder_config)
    assert "path" in str(exc_info.value)


def test_schema_concurrency_validation(sample_config_dict: dict[str, Any]):
    """
    测试并发线程数 (concurrency) 的边界校验。
    concurrency 应该是一个大于 0 的整数。
    """
    # 将并发数篡改为 0 (不合法的运行状态)
    sample_config_dict["watch_folders"][0]["concurrency"] = 0

    with pytest.raises(ValidationError) as exc_info:
        TriggerForgeConfigSchema(**sample_config_dict)

    # 校验是否触发了数值限制错误 (Greater than 0)
    assert "concurrency" in str(exc_info.value)


def test_schema_timeout_validation(sample_config_dict: dict[str, Any]):
    """
    测试超时时效 (timeout) 的边界校验。
    timeout 应该是一个正数或限定在有效合理的时间范围内（例如大于0）。
    """
    # 将超时设置为负数
    sample_config_dict["watch_folders"][0]["strategies"][0]["timeout"] = -5

    with pytest.raises(ValidationError) as exc_info:
        TriggerForgeConfigSchema(**sample_config_dict)

    assert "timeout" in str(exc_info.value)


def test_schema_default_values():
    """
    测试部分可选配置字段的默认缺省值填充。
    例如：当用户在 YAML 中未指定策略超时或并发数时，模型能够自动填充合理的默认行为。
    """
    minimal_folder_config = {
        "path": "./watch",
        "success_path": "./success",
        "error_path": "./error",
        "strategies": [{"plugin_name": "basic_plugin", "plugin_version": "0.1.0"}],
    }

    folder = WatchFolderSchema(**minimal_folder_config)

    # 验证未手动指定时自动解析出的合理默认配置
    assert folder.concurrency == 1  # 默认采用单线程/单任务串行队列
    assert (
        folder.strategies[0].timeout == 30
    )  # 默认限制单插件最大硬超时熔断时间为 30 秒
    assert folder.strategies[0].params == {}  # 默认参数为空字典
    assert (
        folder.strategies[0].python_path is None
    )  # 默认不使用隔离环境，使用系统全局 python


def test_schema_optional_fields_have_safe_defaults():
    """
    验证新增可选字段的默认值：
    plugin_directory / debounce_seconds 以及可省略的 plugin_version。
    """
    config = TriggerForgeConfigSchema(
        watch_folders=[
            {
                "path": "./watch",
                "success_path": "./success",
                "error_path": "./error",
                "strategies": [{"plugin_name": "minimal_plugin"}],
            }
        ]
    )

    assert config.plugin_directory == "./plugins"
    assert config.debounce_seconds == 1.0

    folder = config.watch_folders[0]
    assert folder.debounce_seconds == 1.0
    # plugin_version 未显式声明时应回落到占位版本，不阻断配置解析
    assert folder.strategies[0].plugin_version == "0.0.0"


def test_schema_debounce_must_be_positive():
    """防抖窗口必须大于 0，否则视为非法配置。"""
    with pytest.raises(ValidationError) as exc_info:
        WatchFolderSchema(
            path="./watch",
            success_path="./success",
            error_path="./error",
            debounce_seconds=0,
            strategies=[{"plugin_name": "p"}],
        )

    assert "debounce_seconds" in str(exc_info.value)


def test_repo_sample_config_is_valid():
    """
    仓库自带的 config.sample.yaml / config.yaml 必须能通过 Schema 校验，
    防止示例配置与代码实现漂移。
    """
    import yaml

    repo_root = Path(__file__).resolve().parents[2]
    for name in ("config.sample.yaml", "config.yaml"):
        config_path = repo_root / name
        assert config_path.exists(), f"missing {name}"
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        config = TriggerForgeConfigSchema(**data)
        assert config.watch_folders, f"{name} must declare at least one watch folder"
        for folder in config.watch_folders:
            assert folder.strategies, f"{name} strategies must not be empty"
