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

# TriggerForge - PluginRunner Unit Tests
# Author: zybcode
# Description: Verifies the process-level plugin contract documented in
#             docs/plugin_dev.md: argv[1] target file, argv[2]/env params,
#             python_path fallback, JSON output parsing and failure semantics.

from __future__ import annotations

from pathlib import Path

import pytest

from triggerforge.core.runner.plugin_runner import PluginRunner


def _write_plugin(plugins_root: Path, name: str, source: str) -> Path:
    """在临时插件根目录下按扁平规范写入插件入口。"""
    plugin_dir = plugins_root / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    main_py = plugin_dir / "main.py"
    main_py.write_text(source, encoding="utf-8")
    return main_py


@pytest.fixture
def plugin_workspace(tmp_path: Path) -> Path:
    return tmp_path / "plugins"


@pytest.fixture
def target_file(tmp_path: Path) -> Path:
    payload = tmp_path / "payload.txt"
    payload.write_text("triggerforge", encoding="utf-8")
    return payload


def test_runner_passes_target_file_and_params(
    plugin_workspace: Path, target_file: Path
):
    """插件应能从 argv[1] 拿到目标文件，从 argv[2] 与环境变量拿到 JSON 参数。"""
    _write_plugin(
        plugin_workspace,
        "param_probe",
        "import json, os, sys\n"
        "params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}\n"
        "env_params = json.loads(os.environ.get('TRIGGERFORGE_PARAMS', '{}'))\n"
        "result = {\n"
        "    'status': 'success',\n"
        "    'target': sys.argv[1],\n"
        "    'params': params,\n"
        "    'env_params': env_params,\n"
        "}\n"
        "print(json.dumps(result))\n",
    )

    runner = PluginRunner(plugin_name="param_probe", plugins_root=plugin_workspace)
    result = runner.run(file_path=target_file, params={"mode": "strict", "level": 3})

    assert result["status"] == "success"
    assert Path(result["target"]) == target_file
    assert result["params"] == {"mode": "strict", "level": 3}
    assert result["env_params"] == {"mode": "strict", "level": 3}
    # 诊断元数据应被附加到结果中，供 Clerk 生成 panic 报告
    assert result["exit_code"] == 0
    assert "stdout" in result


def test_runner_without_params_keeps_argv_compatible(
    plugin_workspace: Path, target_file: Path
):
    """未配置 params 时不应追加 argv[2]，保持向后兼容。"""
    _write_plugin(
        plugin_workspace,
        "argv_probe",
        "import json, sys\n"
        "print(json.dumps({'status': 'success', 'argc': len(sys.argv)}))\n",
    )

    runner = PluginRunner(plugin_name="argv_probe", plugins_root=plugin_workspace)
    result = runner.run(file_path=target_file)

    assert result["status"] == "success"
    assert result["argc"] == 2  # 脚本名 + 目标文件


def test_runner_non_zero_exit_is_failure(plugin_workspace: Path, target_file: Path):
    """非零退出码应判定为失败，并保留 stderr 作为错误摘要。"""
    _write_plugin(
        plugin_workspace,
        "boom_plugin",
        "import sys\n" "sys.stderr.write('kernel panic')\n" "raise SystemExit(3)\n",
    )

    runner = PluginRunner(plugin_name="boom_plugin", plugins_root=plugin_workspace)
    result = runner.run(file_path=target_file)

    assert result["status"] == "failed"
    assert result["exit_code"] == 3
    assert "kernel panic" in result["error"]


def test_runner_invalid_json_output_is_failure(
    plugin_workspace: Path, target_file: Path
):
    """stdout 不是合法 JSON 时应判定为失败（避免误判成功）。"""
    _write_plugin(
        plugin_workspace,
        "chatty_plugin",
        "print('hello, this is not json')\n",
    )

    runner = PluginRunner(plugin_name="chatty_plugin", plugins_root=plugin_workspace)
    result = runner.run(file_path=target_file)

    assert result["status"] == "failed"
    assert "JSON" in result["error"]


def test_runner_timeout_is_failure(plugin_workspace: Path, target_file: Path):
    """超过 timeout 的子进程应被强制终止并判定失败。"""
    _write_plugin(
        plugin_workspace,
        "sleepy_plugin",
        "import time\n" "time.sleep(5)\n",
    )

    runner = PluginRunner(plugin_name="sleepy_plugin", plugins_root=plugin_workspace)
    result = runner.run(file_path=target_file, timeout=1)

    assert result["status"] == "failed"
    assert "timed out" in result["error"]


def test_runner_invalid_python_path_falls_back(
    plugin_workspace: Path, target_file: Path
):
    """python_path 指向不存在的解释器时应告警并回退到当前解释器。"""
    _write_plugin(
        plugin_workspace,
        "fallback_plugin",
        "import json\nprint(json.dumps({'status': 'success'}))\n",
    )

    runner = PluginRunner(plugin_name="fallback_plugin", plugins_root=plugin_workspace)
    result = runner.run(
        file_path=target_file, python_path="/nonexistent/venv/bin/python"
    )

    assert result["status"] == "success"


def test_runner_missing_plugin_raises(plugin_workspace: Path):
    """插件目录不存在且非内置插件时应抛出 FileNotFoundError。"""
    runner = PluginRunner(plugin_name="ghost_plugin", plugins_root=plugin_workspace)
    with pytest.raises(FileNotFoundError):
        runner.run(file_path=Path("whatever.txt"))
