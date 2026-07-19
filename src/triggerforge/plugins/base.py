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

# src/triggerforge/plugins/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BasePlugin(ABC):
    """所有插件必须继承的抽象基类"""

    @abstractmethod
    def execute(self, file_path: Path) -> bool:
        """
        执行插件逻辑。
        Args:
            file_path: 触发事件的文件路径
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        pass
