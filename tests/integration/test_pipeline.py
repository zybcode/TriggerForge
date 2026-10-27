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
from typing import Dict

from tests.conftest import wait_for_watcher_ready
from triggerforge.core.clerk.archiver import ClerkArchiver
from triggerforge.core.looper import TriggerForgeLooper
from triggerforge.core.runner.plugin_runner import PluginRunner
from triggerforge.core.sentry.queue import EventBufferQueue
from triggerforge.core.sentry.watcher import SentryWatcher


def test_full_pipeline_success(integration_env: Dict[str, Path]):
    """完整端到端成功链路测试。"""
    watch_dir = integration_env["watch"]
    success_dir = integration_env["success"]

    config = {
        "path": str(watch_dir),
        "success_path": str(success_dir),
        "error_path": str(integration_env["error"]),
        "strategies": [{"plugin_name": "test_echo", "timeout": 5}],
    }

    queue = EventBufferQueue()
    watcher = SentryWatcher(watch_configs=[config], dispatch_queue=queue)  # type: ignore[arg-type]
    watcher.start()
    wait_for_watcher_ready(watcher)

    trigger_file = watch_dir / "test.txt"
    trigger_file.write_text("data")

    retrieved_file = queue.get(timeout=2.0)
    assert retrieved_file is not None

    runner = PluginRunner(
        plugin_name="test_echo", plugins_root=integration_env["plugins"]
    )
    runner.run(file_path=retrieved_file)

    archiver = ClerkArchiver()
    final_path = archiver.archive_success(retrieved_file, success_dir)
    assert final_path.exists()

    watcher.stop()


def test_full_pipeline_failure(integration_env: Dict[str, Path]):
    """插件执行失败后的错误归档测试。"""
    archiver = ClerkArchiver()
    # 模拟文件被归档至错误目录
    dummy_file = integration_env["watch"] / "error.txt"
    dummy_file.write_text("bad data")

    final_path = archiver.archive_error(dummy_file, integration_env["error"])
    assert final_path.exists()


# ----------------------------------------------------------------------
# 真实端到端：投递文件必须能触发插件应用（Looper 全链路）
# ----------------------------------------------------------------------
def _write_plugin(plugins_root: Path, name: str, source: str) -> None:
    plugin_dir = plugins_root / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "main.py").write_text(source, encoding="utf-8")


def _looper_config(integration_env: Dict[str, Path], plugin_name: str, timeout: int = 10) -> dict:
    return {
        "plugin_directory": str(integration_env["plugins"]),
        "log_dir": str(integration_env["base"] / "logs"),
        "watch_folders": [
            {
                "path": str(integration_env["watch"]),
                "success_path": str(integration_env["success"]),
                "error_path": str(integration_env["error"]),
                "concurrency": 2,
                "debounce_seconds": 0.3,
                "strategies": [{"plugin_name": plugin_name, "timeout": timeout}],
            }
        ],
    }


def _wait_until(predicate, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return predicate()


def test_looper_end_to_end_trigger_success(integration_env: Dict[str, Path]):
    """投递文件到监控目录后，插件子进程被调用且文件归档到成功目录。"""
    _write_plugin(
        integration_env["plugins"],
        "e2e_ok",
        "import json, sys\n"
        "print(json.dumps({'status': 'success', 'file': sys.argv[1]}))\n",
    )

    looper = TriggerForgeLooper(_looper_config(integration_env, "e2e_ok"))
    thread = threading.Thread(target=looper.start, daemon=True)
    thread.start()
    try:
        assert _wait_until(lambda: looper.ready, timeout=10), "looper failed to become ready"
        # 给 watchdog 事件后端一点时间完成挂载后的初始化
        time.sleep(0.5)

        trigger_file = integration_env["watch"] / "e2e.txt"
        trigger_file.write_text("data", encoding="utf-8")

        assert _wait_until(
            lambda: (integration_env["success"] / "e2e.txt").exists()
        ), "file was never archived to the success zone (pipeline not triggered)"
        assert not trigger_file.exists()
        assert list(integration_env["error"].iterdir()) == []
    finally:
        looper.stop()
        thread.join(timeout=5)


def test_looper_end_to_end_trigger_failure(integration_env: Dict[str, Path]):
    """插件失败时文件进入故障隔离区，并生成 panic 诊断报告。"""
    _write_plugin(
        integration_env["plugins"],
        "e2e_bad",
        "import json, sys\n"
        "sys.stderr.write('e2e synthetic failure')\n"
        "print(json.dumps({'status': 'failed', 'error': 'synthetic'}))\n"
        "raise SystemExit(1)\n",
    )

    looper = TriggerForgeLooper(_looper_config(integration_env, "e2e_bad"))
    thread = threading.Thread(target=looper.start, daemon=True)
    thread.start()
    try:
        assert _wait_until(lambda: looper.ready, timeout=10), "looper failed to become ready"
        # 给 watchdog 事件后端一点时间完成挂载后的初始化
        time.sleep(0.5)

        trigger_file = integration_env["watch"] / "broken.txt"
        trigger_file.write_text("bad data", encoding="utf-8")

        assert _wait_until(
            lambda: (integration_env["error"] / "broken.txt").exists()
        ), "failed file was never quarantined"
        assert list(integration_env["success"].iterdir()) == []
        assert _wait_until(
            lambda: len(list((integration_env["base"] / "logs").glob("panic_*.json"))) == 1
        ), "panic report was not generated"
    finally:
        looper.stop()
        thread.join(timeout=5)
