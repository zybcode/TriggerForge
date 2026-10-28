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

import logging
import threading
import time
from pathlib import Path
from typing import Any

from triggerforge.core.clerk.archiver import ClerkArchiver
from triggerforge.core.clerk.journal import ClerkJournal
from triggerforge.core.runner.plugin_runner import PluginRunner
from triggerforge.core.sentry.queue import EventBufferQueue
from triggerforge.core.sentry.watcher import SentryWatcher

logger = logging.getLogger(__name__)


class TriggerForgeLooper:
    """
    编排核心：将 Sentry 文件监听、事件缓冲队列、插件执行管道与 Clerk 归档
    完整地串联起来。

    数据流:
        SentryWatcher(监听目录) --防抖--> EventBufferQueue --消费--> Worker 线程
        Worker: 依次执行 strategies(PluginRunner 子进程沙箱)
              -> 全部成功: ClerkArchiver.archive_success
              -> 任一失败: ClerkJournal.dump_panic_report + archive_error
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config or {}
        self.watchers: list[SentryWatcher] = []
        self.queues: list[EventBufferQueue] = []
        self.workers: list[threading.Thread] = []
        self.is_running = False
        # True 表示所有 watcher 与 worker 均已就绪（可安全投递文件）
        self._ready = False

        # 插件根目录：可通过顶层 plugin_directory 配置（默认 ./plugins）
        self.plugins_root = Path(self.config.get("plugin_directory", "./plugins"))
        # 诊断报告目录（懒初始化，避免在未运行时产生副作用）
        self._log_dir = self.config.get("log_dir", "logs")
        self._archiver = ClerkArchiver()
        self._journal: ClerkJournal | None = None

    # ------------------------------------------------------------------
    # 配置解析
    # ------------------------------------------------------------------
    def _resolve_watch_configs(self) -> list[dict[str, Any]]:
        watch_folders_config = self.config.get("watch_folders", [])
        if watch_folders_config:
            return list(watch_folders_config)

        watch_path = self.config.get("watch_path")
        if watch_path:
            return [
                {
                    "path": watch_path,
                    "debounce_seconds": self.config.get("debounce_seconds", 1.0),
                }
            ]

        return []

    def _get_journal(self) -> ClerkJournal:
        """懒加载运行记录员，避免 Looper 构造时产生文件系统副作用。"""
        if self._journal is None:
            self._journal = ClerkJournal(log_dir=Path(self._log_dir))
        return self._journal

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self):
        logger.info("Initializing TriggerForge looper...")
        watch_folders_config = self._resolve_watch_configs()

        if not watch_folders_config:
            logger.warning("No watch folders configured in config.yaml.")
            return

        self.is_running = True

        # 遍历配置，为每个监听目录启动一个 SentryWatcher + 消费线程池
        for folder_config in watch_folders_config:
            path = folder_config.get("path")
            if not path:
                continue

            queue = EventBufferQueue()

            logger.info(f"Starting watcher thread for directory: {path}")
            watcher = SentryWatcher(
                watch_configs=[folder_config],
                dispatch_queue=queue,
                debounce_seconds=float(
                    folder_config.get(
                        "debounce_seconds", self.config.get("debounce_seconds", 1.0)
                    )
                ),
            )
            watcher.start()
            self.watchers.append(watcher)
            self.queues.append(queue)

            # 为每个监控目录按 concurrency 启动独立的工作线程消费事件，
            # 调用插件流水线并归档文件——这是"投递文件 -> 触发接口应用"的关键链路。
            concurrency = int(folder_config.get("concurrency", 1))
            for index in range(concurrency):
                worker = threading.Thread(
                    target=self._worker_loop,
                    args=(folder_config, queue),
                    name=f"forge-worker-{Path(path).name}-{index}",
                    daemon=True,
                )
                worker.start()
                self.workers.append(worker)

            logger.info(
                f"Dispatched {concurrency} pipeline worker(s) for directory: {path}"
            )

        # 至此所有监听器与工作线程均已挂载，可以安全地接收投递文件
        self._ready = True
        logger.info("TriggerForge looper is ready to receive files.")

        # 保持主线程存活
        try:
            while self.is_running:
                time.sleep(1)
        except (KeyboardInterrupt, InterruptedError):
            self.stop()
            raise
        except Exception:
            self.stop()
            raise

    @property
    def ready(self) -> bool:
        """所有监听器与工作线程是否已挂载完毕（可安全投递文件）。"""
        return self._ready

    def stop(self):
        logger.info("Stopping TriggerForge looper...")
        self.is_running = False
        self._ready = False
        for watcher in self.watchers:
            try:
                watcher.stop()
            except Exception as exc:
                logger.warning(f"Watcher stop raised: {exc}")
        for worker in self.workers:
            worker.join(timeout=2.0)
        logger.info("All watchers stopped safely.")

    # ------------------------------------------------------------------
    # 事件消费与插件管道
    # ------------------------------------------------------------------
    def _worker_loop(self, folder_config: dict[str, Any], queue: EventBufferQueue):
        """工作线程主循环：从缓冲队列消费文件事件并驱动插件流水线。"""
        success_path = folder_config.get("success_path")
        error_path = folder_config.get("error_path")
        strategies = folder_config.get("strategies", [])

        while self.is_running:
            try:
                file_path = queue.get(timeout=0.5)
            except Exception:
                continue

            if file_path is None:
                continue

            try:
                self._process_file(file_path, strategies, success_path, error_path)
            except Exception:
                # 故障隔离：任何未预期的异常都不允许击穿工作线程
                logger.exception(f"Unhandled pipeline error for '{file_path}'")
            finally:
                try:
                    queue.task_done()
                except Exception:
                    pass

    def _process_file(
        self,
        file_path: Path,
        strategies: list[dict[str, Any]],
        success_path: str | None,
        error_path: str | None,
    ) -> None:
        """对单个触发文件按顺序执行插件策略流水线，并归档。"""
        file_path = Path(file_path)

        # 防抖窗口后文件可能已被移走，直接跳过
        if not file_path.exists():
            logger.warning(f"Triggered file no longer exists, skipping: {file_path}")
            return

        logger.info(f"Pipeline started for file: {file_path}")

        overall_success = True
        for strategy in strategies:
            plugin_name = strategy.get("plugin_name", "")
            params = strategy.get("params") or {}

            try:
                runner = PluginRunner(
                    plugin_name=plugin_name,
                    plugins_root=self.plugins_root,
                    plugin_version=strategy.get("plugin_version"),
                )
                result = runner.run(
                    file_path=file_path,
                    params=params,
                    timeout=int(strategy.get("timeout", 30)),
                    python_path=strategy.get("python_path"),
                )
            except Exception as exc:
                result = {"status": "failed", "error": str(exc)}

            if result.get("status") != "success":
                overall_success = False
                logger.error(
                    f"Plugin '{plugin_name}' failed for '{file_path}': "
                    f"{result.get('error')}"
                )
                # 记录员导出故障现场诊断报告（.panic.json）
                try:
                    self._get_journal().dump_panic_report(
                        file_path=file_path,
                        plugin_name=plugin_name,
                        exit_code=result.get("exit_code"),
                        error_message=str(result.get("error", "unknown")),
                        stdout=str(result.get("stdout", "")),
                        stderr=str(result.get("stderr", "")),
                        strategy_params=params,
                    )
                except Exception as exc:
                    logger.warning(f"Failed to dump panic report: {exc}")
                break  # 熔断：流水线中任一策略失败立即中断后续策略

            logger.info(f"Plugin '{plugin_name}' succeeded for '{file_path}'")

        # 归档：成功进 success_path，失败进 error_path（故障隔离区）
        try:
            if overall_success:
                if success_path:
                    final = self._archiver.archive_success(file_path, success_path)
                    logger.info(f"File archived to success zone: {final}")
            else:
                if error_path:
                    final = self._archiver.archive_error(file_path, error_path)
                    logger.warning(f"File quarantined to error zone: {final}")
        except Exception as exc:
            logger.error(f"Failed to archive file '{file_path}': {exc}")


def run_looper(config: dict[str, Any]):
    looper = TriggerForgeLooper(config)
    looper.start()
