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
