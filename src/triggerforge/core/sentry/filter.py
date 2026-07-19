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


# TriggerForge - Event Filter Module
# Author: zybcode
# Description: Advanced filtering engine supporting static path pattern matching,
#             regex-based blacklist/whitelist checks, and stateful event deduplication.

from __future__ import annotations

import fnmatch
import re
import time
from pathlib import Path
from typing import Dict, List, Optional


class EventFilter:
    """
    事件过滤器，兼容多种老接口参数名并提供基于后缀、正则和简单时间窗口的去重。

    支持构造参数（任何组合）:
      - allowed_extensions: List[str]
      - denied_extensions: List[str]
      - regex_pattern: str
      - duplicate_cooldown_seconds: float
    """

    def __init__(
        self,
        whitelist_patterns: Optional[List[str]] = None,
        blacklist_patterns: Optional[List[str]] = None,
        regex_blacklist: Optional[List[str]] = None,
        deduplication_window_size: int = 1000,
        # compatibility params used by tests
        allowed_extensions: Optional[List[str]] = None,
        denied_extensions: Optional[List[str]] = None,
        regex_pattern: Optional[str] = None,
        duplicate_cooldown_seconds: Optional[float] = None,
    ):
        # core pattern lists
        self.whitelist_patterns = whitelist_patterns or []
        self.blacklist_patterns = blacklist_patterns or []

        # compile regex lists: support both blacklist and an allow-pattern
        self.regex_blacklist = [re.compile(p) for p in (regex_blacklist or [])]
        self.regex_allow = re.compile(regex_pattern) if regex_pattern else None

        # extension based allow/deny (preferred by tests)
        self.allowed_extensions = [ext.lower() for ext in (allowed_extensions or [])]
        self.denied_extensions = [ext.lower() for ext in (denied_extensions or [])]

        # time-based dedup map (path -> last_seen_timestamp)
        self.duplicate_cooldown_seconds = duplicate_cooldown_seconds
        self._last_seen: Dict[str, float] = {}

        # legacy count-based window kept for compatibility but not used by tests
        self.dedup_window_size = deduplication_window_size
        self.processed_history: List[str] = []
        self.processed_set: set[str] = set()

    def should_allow(self, file_path: Path) -> bool:
        return self._should_process_impl(file_path)

    # tests expect `should_process` name
    def should_process(self, file_path: Path) -> bool:
        return self._should_process_impl(file_path)

    def _should_process_impl(self, file_path: Path) -> bool:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        name = file_path.name
        ext = (file_path.suffix or "").lower()

        # allowed_extensions semantics: if provided, only allow those
        if self.allowed_extensions:
            if ext not in self.allowed_extensions:
                return False

        # denied extensions check
        if self.denied_extensions and ext in self.denied_extensions:
            return False

        # legacy wildcard patterns
        if self.whitelist_patterns:
            if not any(fnmatch.fnmatch(name, pat) for pat in self.whitelist_patterns):
                return False

        if self.blacklist_patterns:
            if any(fnmatch.fnmatch(name, pat) for pat in self.blacklist_patterns):
                return False

        # regex allow pattern: if provided, only allow matches
        if self.regex_allow:
            if not self.regex_allow.search(name):
                return False

        # regex blacklist
        if self.regex_blacklist:
            if any(p.search(str(file_path)) for p in self.regex_blacklist):
                return False

        # time-based duplicate cooldown
        if self.duplicate_cooldown_seconds is not None:
            now = time.time()
            key = str(file_path)
            last = self._last_seen.get(key)
            if last is not None and (now - last) < self.duplicate_cooldown_seconds:
                return False
            # mark as seen
            self._last_seen[key] = now

        # legacy count-based dedup (kept for backwards compat)
        path_str = str(file_path.absolute())
        if path_str in self.processed_set:
            return False

        return True

    def mark_processed(self, file_path: Path) -> None:
        path_str = str(file_path.absolute())
        if path_str not in self.processed_set:
            self.processed_set.add(path_str)
            self.processed_history.append(path_str)
            if len(self.processed_history) > self.dedup_window_size:
                oldest = self.processed_history.pop(0)
                self.processed_set.discard(oldest)

    def clear_history(self) -> None:
        self.processed_history.clear()
        self.processed_set.clear()
        self._last_seen.clear()


# compatibility alias for tests
SentryFilter = EventFilter
