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

import threading
from triggerforge.core.sentry.queue import EventBufferQueue
from pathlib import Path


def test_queue_thread_safety():
    queue = EventBufferQueue()
    results = []
    errors = []

    def producer():
        for i in range(50):
            queue.put(Path(f"/file_{i}.txt"))

    def consumer():
        for _ in range(50):
            try:
                item = queue.get(timeout=2.0)
                if item:
                    results.append(item)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=producer) for _ in range(3)] + [
        threading.Thread(target=consumer) for _ in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)

    assert len(errors) == 0
    assert len(results) == 150
