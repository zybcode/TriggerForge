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

from __future__ import annotations

from pathlib import Path

import pytest

from triggerforge.core.runner.plugin_runner import PluginRunner


@pytest.fixture
def dummy_plugin_package(integration_env: dict):
    """创建符合扁平化规范的测试插件目录。"""
    plugin_dir = integration_env["plugins"] / "test_echo"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    main_py = plugin_dir / "main.py"
    main_py.write_text('import json; print(json.dumps({"status": "success"}))')
    return plugin_dir


def test_plugin_runner_loading(integration_env: dict, dummy_plugin_package):
    """✅ 验证 PluginRunner 能正确加载扁平路径下的插件。"""
    runner = PluginRunner(
        plugin_name="test_echo", plugins_root=integration_env["plugins"]
    )
    # 路径匹配校验
    assert runner._plugin_main_path().exists()
    assert runner._plugin_main_path().name == "main.py"


def test_plugin_runner_file_not_found():
    """验证找不到插件时的异常处理。"""
    runner = PluginRunner(plugin_name="non_existent", plugins_root=Path("/tmp/fake"))
    with pytest.raises(FileNotFoundError):
        runner._plugin_main_path()
