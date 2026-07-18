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

import time
import pytest
from pathlib import Path
from unittest.mock import patch
from triggerforge.core.sentry.watcher import SentryWatcher
from triggerforge.core.sentry.queue import EventBufferQueue
from watchdog.events import FileCreatedEvent, DirCreatedEvent


def test_event_handler_captures_creation(temp_workspace):
    queue = EventBufferQueue()
    watcher = SentryWatcher(
        watch_configs=[{"path": str(temp_workspace)}], dispatch_queue=queue
    )
    test_file = temp_workspace / "test.txt"
    event = FileCreatedEvent(src_path=str(test_file))

    with patch.object(watcher, "_dispatch_debounced_event") as mock_dispatch:
        watcher.event_handler.on_created(event)
        mock_dispatch.assert_called_once_with(test_file)


def test_watcher_ignores_directory_events(temp_workspace):
    queue = EventBufferQueue()
    watcher = SentryWatcher(
        watch_configs=[{"path": str(temp_workspace)}], dispatch_queue=queue
    )
    event = DirCreatedEvent(src_path=str(temp_workspace / "subdir"))

    with patch.object(watcher, "_dispatch_debounced_event") as mock_dispatch:
        watcher.event_handler.on_created(event)
        mock_dispatch.assert_not_called()
