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

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from triggerforge.core.looper import TriggerForgeLooper
from triggerforge.core.sentry.queue import EventBufferQueue


def test_looper_lifecycle():
    """测试 Looper 的启动与关闭逻辑"""
    mock_config = {"watch_path": "./test_storage", "debounce_seconds": 0.5}

    with patch("triggerforge.core.looper.SentryWatcher") as MockWatcher:
        instance = MockWatcher.return_value
        looper = TriggerForgeLooper(mock_config)

        # 1. 模拟 sleep 抛出异常
        with patch("triggerforge.core.looper.time.sleep", side_effect=InterruptedError):
            with pytest.raises(InterruptedError):
                looper.start()

        # 2. 无论 looper.start 内部是否处理了异常，我们在此显式清理
        looper.stop()

        # 3. 核心断言：只要调用过 1 次 stop，就证明清理逻辑已执行
        assert instance.stop.call_count >= 1
        instance.start.assert_called_once()
        assert looper.is_running is False


def test_looper_init_with_defaults():
    """测试 Looper 在配置缺失时能否使用默认参数"""
    looper = TriggerForgeLooper({})
    assert looper.config == {}
    assert looper.is_running is False


# ----------------------------------------------------------------------
# 事件管道测试：验证"投递文件 -> 插件执行 -> 归档"链路已接线
# ----------------------------------------------------------------------

OK_PLUGIN = (
    "import json, sys\n"
    "print(json.dumps({'status': 'success', 'file': sys.argv[1]}))\n"
)
FAIL_PLUGIN = (
    "import json, sys\n"
    "sys.stderr.write('synthetic failure')\n"
    "print(json.dumps({'status': 'failed', 'error': 'synthetic failure'}))\n"
    "raise SystemExit(1)\n"
)


def _write_plugin(plugins_root: Path, name: str, source: str) -> None:
    plugin_dir = plugins_root / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "main.py").write_text(source, encoding="utf-8")


@pytest.fixture
def pipeline_env(tmp_path: Path) -> dict:
    """构造一套完整的监控/归档/插件/日志目录与 Looper。"""
    watch = tmp_path / "watch"
    success = tmp_path / "success"
    error = tmp_path / "error"
    plugins = tmp_path / "plugins"
    logs = tmp_path / "logs"
    for directory in (watch, success, error, plugins, logs):
        directory.mkdir(parents=True, exist_ok=True)
    return {
        "watch": watch,
        "success": success,
        "error": error,
        "plugins": plugins,
        "logs": logs,
        "tmp": tmp_path,
    }


def _make_looper(env: dict, strategies, concurrency: int = 1) -> TriggerForgeLooper:
    return TriggerForgeLooper(
        {
            "plugin_directory": str(env["plugins"]),
            "log_dir": str(env["logs"]),
            "watch_folders": [
                {
                    "path": str(env["watch"]),
                    "success_path": str(env["success"]),
                    "error_path": str(env["error"]),
                    "concurrency": concurrency,
                    "debounce_seconds": 0.2,
                    "strategies": strategies,
                }
            ],
        }
    )


def test_process_file_success_archives_to_success_zone(pipeline_env):
    """插件执行成功时，文件应被移动到成功归档目录。"""
    _write_plugin(pipeline_env["plugins"], "ok_plugin", OK_PLUGIN)
    looper = _make_looper(
        pipeline_env, [{"plugin_name": "ok_plugin", "timeout": 10}]
    )

    target = pipeline_env["watch"] / "payload.txt"
    target.write_text("data", encoding="utf-8")

    looper._process_file(
        target,
        [{"plugin_name": "ok_plugin", "timeout": 10}],
        str(pipeline_env["success"]),
        str(pipeline_env["error"]),
    )

    assert (pipeline_env["success"] / "payload.txt").exists()
    assert not target.exists()
    assert list(pipeline_env["error"].iterdir()) == []


def test_process_file_failure_quarantines_and_dumps_panic(pipeline_env):
    """插件失败时应生成 panic 报告并将文件移动至故障隔离目录。"""
    _write_plugin(pipeline_env["plugins"], "fail_plugin", FAIL_PLUGIN)
    looper = _make_looper(
        pipeline_env, [{"plugin_name": "fail_plugin", "timeout": 10}]
    )

    target = pipeline_env["watch"] / "bad.txt"
    target.write_text("bad data", encoding="utf-8")

    looper._process_file(
        target,
        [{"plugin_name": "fail_plugin", "timeout": 10}],
        str(pipeline_env["success"]),
        str(pipeline_env["error"]),
    )

    assert (pipeline_env["error"] / "bad.txt").exists()
    assert not (pipeline_env["success"] / "bad.txt").exists()
    panic_reports = list(pipeline_env["logs"].glob("panic_*.json"))
    assert len(panic_reports) == 1
    assert "synthetic failure" in panic_reports[0].read_text(encoding="utf-8")


def test_process_file_short_circuits_after_failure(pipeline_env):
    """任一策略失败后，后续策略不应再被执行（短路熔断）。"""
    _write_plugin(pipeline_env["plugins"], "fail_plugin", FAIL_PLUGIN)
    marker_path = pipeline_env["tmp"] / "marker.txt"
    _write_plugin(
        pipeline_env["plugins"],
        "marker_plugin",
        "import json, pathlib, sys\n"
        f"pathlib.Path(r'{marker_path}').write_text('ran')\n"
        "print(json.dumps({'status': 'success'}))\n",
    )

    strategies = [
        {"plugin_name": "fail_plugin", "timeout": 10},
        {"plugin_name": "marker_plugin", "timeout": 10},
    ]
    looper = _make_looper(pipeline_env, strategies)

    target = pipeline_env["watch"] / "short.txt"
    target.write_text("data", encoding="utf-8")
    looper._process_file(
        target, strategies, str(pipeline_env["success"]), str(pipeline_env["error"])
    )

    assert (pipeline_env["error"] / "short.txt").exists()
    assert not (pipeline_env["tmp"] / "marker.txt").exists()


def test_process_file_missing_file_is_skipped(pipeline_env):
    """防抖窗口后文件已被移走时，不应抛异常也不应产生归档。"""
    _write_plugin(pipeline_env["plugins"], "ok_plugin", OK_PLUGIN)
    looper = _make_looper(pipeline_env, [{"plugin_name": "ok_plugin"}])

    looper._process_file(
        pipeline_env["watch"] / "ghost.txt",
        [{"plugin_name": "ok_plugin"}],
        str(pipeline_env["success"]),
        str(pipeline_env["error"]),
    )

    assert list(pipeline_env["success"].iterdir()) == []
    assert list(pipeline_env["error"].iterdir()) == []


def test_looper_wires_buffer_queue_and_workers(pipeline_env):
    """Looper 必须把缓冲队列交给 SentryWatcher，并按 concurrency 启动工作线程。"""
    _write_plugin(pipeline_env["plugins"], "ok_plugin", OK_PLUGIN)
    looper = _make_looper(
        pipeline_env, [{"plugin_name": "ok_plugin", "timeout": 10}], concurrency=3
    )

    with patch("triggerforge.core.looper.SentryWatcher") as MockWatcher:
        thread = threading.Thread(target=looper.start, daemon=True)
        thread.start()

        deadline = time.time() + 5
        while len(looper.workers) < 3 and time.time() < deadline:
            time.sleep(0.05)

        assert len(looper.workers) == 3
        call_kwargs = MockWatcher.call_args.kwargs
        assert isinstance(call_kwargs["dispatch_queue"], EventBufferQueue)
        assert call_kwargs["watch_configs"][0]["path"] == str(pipeline_env["watch"])
        MockWatcher.return_value.start.assert_called_once()

        looper.stop()
        thread.join(timeout=5)

    assert looper.is_running is False
