# src/triggerforge/plugins/base.py
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
