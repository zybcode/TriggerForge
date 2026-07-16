import time
import pytest
from pathlib import Path
from unittest.mock import patch
from triggerforge.core.sentry.watcher import SentryWatcher
from triggerforge.core.sentry.queue import EventBufferQueue
from watchdog.events import FileCreatedEvent, DirCreatedEvent

def test_event_handler_captures_creation(temp_workspace):
    queue = EventBufferQueue()
    watcher = SentryWatcher(watch_configs=[{"path": str(temp_workspace)}], dispatch_queue=queue)
    test_file = temp_workspace / "test.txt"
    event = FileCreatedEvent(src_path=str(test_file))
    
    with patch.object(watcher, '_dispatch_debounced_event') as mock_dispatch:
        watcher.event_handler.on_created(event)
        mock_dispatch.assert_called_once_with(test_file)

def test_watcher_ignores_directory_events(temp_workspace):
    queue = EventBufferQueue()
    watcher = SentryWatcher(watch_configs=[{"path": str(temp_workspace)}], dispatch_queue=queue)
    event = DirCreatedEvent(src_path=str(temp_workspace / "subdir"))
    
    with patch.object(watcher, '_dispatch_debounced_event') as mock_dispatch:
        watcher.event_handler.on_created(event)
        mock_dispatch.assert_not_called()