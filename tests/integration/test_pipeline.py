"""
TriggerForge - Event-driven directory orchestration engine.
Copyright (C) 2026  [zybcode]

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import pytest
from pathlib import Path
from typing import Dict
from triggerforge.core.sentry.watcher import SentryWatcher
from triggerforge.core.sentry.queue import EventBufferQueue
from triggerforge.core.runner.plugin_runner import PluginRunner
from triggerforge.core.clerk.archiver import ClerkArchiver
from tests.conftest import wait_for_watcher_ready


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
    watcher = SentryWatcher(watch_configs=[config], dispatch_queue=queue)
    watcher.start()
    wait_for_watcher_ready(watcher)

    trigger_file = watch_dir / "test.txt"
    trigger_file.write_text("data")

    retrieved_file = queue.get(timeout=2.0)
    assert retrieved_file is not None

    runner = PluginRunner(
        plugin_name="test_echo", plugins_root=integration_env["plugins"]
    )
    result = runner.run(file_path=retrieved_file)

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
