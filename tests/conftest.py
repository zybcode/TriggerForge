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

"""
TriggerForge - Unit Test Configuration & Shared Fixtures
Author: zybcode
Description: Centralized Pytest fixtures providing isolated, self-cleaning
             file system environments and mock data structures for unit testing.
"""

import pytest
import shutil
import time
from pathlib import Path
from typing import Generator, Dict, Any

# 将项目的 src 目录绝对路径强制加入系统路径
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def wait_for_watcher_ready(watcher, timeout: float = 2.0) -> None:
    """Wait until the watcher has started running."""
    start = time.time()
    while not getattr(watcher, "is_running", False) and (time.time() - start) < timeout:
        time.sleep(0.05)
    assert getattr(watcher, "is_running", False)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Generator[Path, None, None]:
    """
    提供一个完全隔离的、线程安全的临时测试工作空间。
    测试结束后，Pytest 会自动递归清理该目录下的所有产生文
    """
    workspace = tmp_path / "triggerforge_test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
    if workspace.exists():
        try:
            shutil.rmtree(workspace)
        except OSError:
            pass  # 忽略 Windows 下可能因文件句柄未释放导致的清理失败


@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """
    提供一套标准的、符合 Schema 校验的配置字典，用于测试 schema.py 的解析。
    """
    return {
        "watch_folders": [
            {
                "path": "./storage/watch_folder",
                "success_path": "./storage/success_folder",
                "error_path": "./storage/error_folder",
                "concurrency": 2,
                "strategies": [
                    {
                        "plugin_name": "dummy_plugin",
                        "plugin_version": "1.0.0",
                        "timeout": 10,
                        "params": {"mode": "test"},
                    }
                ],
            }
        ]
    }


@pytest.fixture
def dummy_file(temp_workspace: Path) -> Path:
    """
    在临时工作空间中预先创建一个填充了测试数据的源文件，
    用于模拟 Sentry 捕获事件或 Clerk 进行归档移动。
    """
    file_path = temp_workspace / "mock_trigger_file.txt"
    file_path.write_text("TriggerForge unit test payload.", encoding="utf-8")
    return file_path
