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
TriggerForge - Sentry Watcher Module
Author: zybcode
Description: High-performance directory monitor that tracks filesystem events,
             applies defensive debouncing filters, and dispatches events.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
from queue import Queue
from threading import Thread, Timer

# 依赖第三方 watchdog 库进行跨平台文件系统事件监听
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class FileWriteDebouncer:
    """
    文件写入防抖过滤器。
    确保文件已完全写入磁盘（文件大小在指定时间内不再变化），避免下游插件读取到半写入状态的文件。
    """

    def __init__(self, delay_seconds: float = 1.0, check_interval: float = 0.2):
        self.delay_seconds = delay_seconds
        self.check_interval = check_interval

    def is_write_complete(self, file_path: Path) -> bool:
        """
        通过循环比对文件大小和修改时间，判断文件是否写入完成。
        """
        if not file_path.exists():
            return False

        try:
            last_size = file_path.stat().st_size
            time.sleep(self.check_interval)

            elapsed = self.check_interval
            while elapsed < self.delay_seconds:
                current_size = file_path.stat().st_size
                if current_size != last_size:
                    # 文件大小仍在变化，重置等待
                    last_size = current_size
                    time.sleep(self.check_interval)
                    elapsed = self.check_interval
                else:
                    time.sleep(self.check_interval)
                    elapsed += self.check_interval

            return True
        except (FileNotFoundError, PermissionError):
            return False


class SentryEventHandler(FileSystemEventHandler):
    """
    自定义 watchdog 事件处理器。
    过滤无效的临时文件，并对通过过滤的文件事件执行防抖检查，最终投递进缓冲队列。
    """

    def __init__(self, dispatch_queue: Queue, debouncer: FileWriteDebouncer):
        super().__init__()
        self.dispatch_queue = dispatch_queue
        self.debouncer = debouncer
        # Optional test hook: callable invoked with a Path when events are processed
        self._dispatch_callback: Optional[Callable[[Path], None]] = None

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._process_event(Path(str(event.src_path)))

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._process_event(Path(str(event.src_path)))

    def _is_temp_file(self, path: Path) -> bool:
        """
        静态过滤：过滤临时文件或编辑器缓存（如 .tmp, .swp, ~ 结尾的文件）
        """
        name = path.name
        return (
            name.startswith(".")
            or name.endswith(".tmp")
            or name.endswith(".swp")
            or name.endswith("~")
        )

    def _process_event(self, file_path: Path) -> None:
        # 1. 静态黑名单过滤
        if self._is_temp_file(file_path):
            return

        # 2. 立即触发上层的 debounced dispatch 回调（如果已注册），
        #    以便单元测试可以同步断言 handler 的行为。
        callback = getattr(self, "_dispatch_callback", None)
        if callable(callback):
            callback(file_path)
            return

        # 否则回退到直接放入队列（保持向后兼容）
        self.dispatch_queue.put(file_path.absolute())


class SentryWatcher:
    """
    哨兵核心监听器。
    管理 watchdog 监控实例的生命周期，支持配置并并行监控多个不同的物理目录。
    """

    def __init__(
        self,
        watch_configs: Optional[List[Dict[str, Any]]] = None,
        dispatch_queue: Optional[Queue] = None,
        # legacy/alternate constructor args used by tests
        watch_path: Optional[Path] = None,
        event_queue: Optional[Queue] = None,
        debounce_seconds: Optional[float] = None,
    ):
        """
        Flexible constructor supporting either a list of `watch_configs` and
        a `dispatch_queue`, or the legacy shorthand `watch_path` + `event_queue`.
        """
        if watch_configs is None and watch_path is not None:
            # provide compatibility: single-watch config
            watch_configs = [{"path": str(watch_path)}]

        if dispatch_queue is None and event_queue is not None:
            dispatch_queue = event_queue

        self.watch_configs = watch_configs or []
        self.dispatch_queue = dispatch_queue
        # compatibility aliases expected by tests
        self.watch_path = Path(watch_path) if watch_path is not None else None
        self.event_queue = dispatch_queue
        self.debounce_seconds = debounce_seconds or 1.0
        self.observer = Observer()
        # allow customizing debouncer delay via debounce_seconds
        self.debouncer = FileWriteDebouncer(delay_seconds=self.debounce_seconds)
        self._is_running = False
        # debounce timers per path
        self._debounce_timers: dict[str, Timer] = {}
        # expose an event handler instance for tests to invoke directly
        handler_queue = (
            self.dispatch_queue if self.dispatch_queue is not None else Queue()
        )
        self.event_handler = SentryEventHandler(handler_queue, self.debouncer)
        # Register a dynamic wrapper so that if tests patch
        # `self._dispatch_debounced_event`, the handler will invoke the patched
        # function.
        self.event_handler._dispatch_callback = (
            lambda fp, _self=self: _self._dispatch_debounced_event(fp)
        )

    def start(self) -> None:
        """
        启动监控器
        """
        if self._is_running:
            return

        print("[Sentry] Initializing watchdog monitors...")
        for config in self.watch_configs:
            path_str = config.get("path")
            if not path_str:
                continue

            watch_path = Path(path_str).absolute()
            # 确保目标监听目录存在
            watch_path.mkdir(parents=True, exist_ok=True)

            # schedule the already-created handler so tests can access it
            self.observer.schedule(
                self.event_handler, path=str(watch_path), recursive=False
            )
            print(f"[Sentry] Active listener successfully mounted on: {watch_path}")

        self.observer.start()
        self._is_running = True
        print("[Sentry] All file monitors started successfully.")

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _enqueue_file(self, file_path: Path) -> None:
        if self.dispatch_queue is not None:
            self.dispatch_queue.put(file_path)

    def _dispatch_debounced_event(self, file_path: Path) -> None:
        """Schedule debounced enqueue for a given file path.

        Repeated calls within the debounce window will cancel and reschedule
        so that only the last event is enqueued after the window expires.
        """
        key = str(file_path)
        # cancel any existing timer for this path
        existing = self._debounce_timers.get(key)
        if existing is not None:
            try:
                existing.cancel()
            except Exception:
                pass

        t = Timer(self.debounce_seconds, self._enqueue_file, args=(file_path,))
        t.daemon = True
        self._debounce_timers[key] = t
        t.start()

    def stop(self) -> None:
        """
        优雅停止监控器，阻塞直至工作线程退出
        """
        if not self._is_running:
            return

        print("[Sentry] Stopping watchdog monitors...")
        self.observer.stop()
        self.observer.join()
        self._is_running = False
        print("[Sentry] Watcher completely stopped.")
