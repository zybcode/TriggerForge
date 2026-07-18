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

import pytest
import shutil
import time
from pathlib import Path
from typing import Generator, Dict


@pytest.fixture
def integration_env(tmp_path: Path) -> Generator[Dict[str, Path], None, None]:
    """创建集成测试所需的基础目录结构与配置文件路径。"""
    base_dir = tmp_path
    watch_dir = base_dir / "watch"
    success_dir = base_dir / "success"
    error_dir = base_dir / "error"
    plugins_dir = base_dir / "plugins"
    config_file = base_dir / "config.yaml"

    for d in [watch_dir, success_dir, error_dir, plugins_dir]:
        d.mkdir()

    yield {
        "base": base_dir,
        "watch": watch_dir,
        "success": success_dir,
        "error": error_dir,
        "plugins": plugins_dir,
        "config": config_file,
    }


def wait_for_watcher_ready(watcher, timeout=2.0):
    """通用的观察者状态轮询工具。"""
    start = time.time()
    while not watcher.is_running and (time.time() - start) < timeout:
        time.sleep(0.05)
    assert watcher.is_running
