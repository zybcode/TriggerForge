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
import logging
from typing import Dict, Any, List
from triggerforge.core.sentry.watcher import SentryWatcher

logger = logging.getLogger(__name__)


class TriggerForgeLooper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.watchers: List[SentryWatcher] = []
        self.is_running = False

    def _resolve_watch_configs(self) -> List[Dict[str, Any]]:
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

    def start(self):
        logger.info("Initializing TriggerForge looper...")
        watch_folders_config = self._resolve_watch_configs()

        if not watch_folders_config:
            logger.warning("No watch folders configured in config.yaml.")
            return

        self.is_running = True

        # 遍历配置，为每个监听目录启动一个 SentryWatcher
        for folder_config in watch_folders_config:
            path = folder_config.get("path")
            if not path:
                continue

            logger.info(f"Starting watcher thread for directory: {path}")
            # 包装为 SentryWatcher 期望的配置结构，传递 debounce_seconds
            watcher = SentryWatcher(
                watch_configs=[folder_config],
                debounce_seconds=float(
                    folder_config.get(
                        "debounce_seconds", self.config.get("debounce_seconds", 1.0)
                    )
                ),
            )
            watcher.start()
            self.watchers.append(watcher)

        # 保持主线程存活
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt, InterruptedError:
            self.stop()
            raise
        except Exception:
            self.stop()
            raise

    def stop(self):
        logger.info("Stopping TriggerForge looper...")
        self.is_running = False
        for watcher in self.watchers:
            watcher.stop()
        logger.info("All watchers stopped safely.")


def run_looper(config: Dict[str, Any]):
    looper = TriggerForgeLooper(config)
    looper.start()
