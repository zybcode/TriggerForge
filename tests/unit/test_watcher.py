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

from queue import Queue
from unittest.mock import patch

from watchdog.events import DirCreatedEvent, FileCreatedEvent

from triggerforge.core.sentry.watcher import SentryWatcher


def test_event_handler_captures_creation(temp_workspace):
    queue = Queue()
    watcher = SentryWatcher(
        watch_configs=[{"path": str(temp_workspace)}], dispatch_queue=queue
    )
    test_file = temp_workspace / "test.txt"
    event = FileCreatedEvent(src_path=str(test_file))

    with patch.object(watcher, "_dispatch_debounced_event") as mock_dispatch:
        watcher.event_handler.on_created(event)
        mock_dispatch.assert_called_once_with(test_file)


def test_watcher_ignores_directory_events(temp_workspace):
    queue = Queue()
    watcher = SentryWatcher(
        watch_configs=[{"path": str(temp_workspace)}], dispatch_queue=queue
    )
    event = DirCreatedEvent(src_path=str(temp_workspace / "subdir"))

    with patch.object(watcher, "_dispatch_debounced_event") as mock_dispatch:
        watcher.event_handler.on_created(event)
        mock_dispatch.assert_not_called()


def test_watcher_creates_default_queue_when_none_provided(temp_workspace):
    """未显式传入 dispatch_queue 时应自动创建内部队列，避免事件静默丢失。"""
    watcher = SentryWatcher(watch_configs=[{"path": str(temp_workspace)}])

    assert watcher.dispatch_queue is not None
    assert watcher.event_handler.dispatch_queue is watcher.dispatch_queue


def test_watcher_reads_debounce_seconds_from_config(temp_workspace):
    """构造参数缺省时，防抖窗口应回落到监控目录配置中的 debounce_seconds。"""
    watcher = SentryWatcher(
        watch_configs=[{"path": str(temp_workspace), "debounce_seconds": 2.5}]
    )

    assert watcher.debounce_seconds == 2.5
