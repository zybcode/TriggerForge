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


# TriggerForge - Clerk Archiver Module
# Author: zybcode
# Description: High-reliability file archiver for atomic file moving, directory
#            self-healing, and duplicate resolution in success/error storage zones.

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Union


class ClerkArchiver:
    """
    高可靠文件归档器 (Clerk Archiver)[cite: 1, 2]
    负责在插件管道执行完毕后，将触发文件原子化地移动至指定的归档目录或故障隔离目录[cite: 1, 2]。
    """

    def __init__(self):
        pass

    def archive_success(
        self, file_path: Union[str, Path], success_path: Union[str, Path]
    ) -> Path:
        """
        将文件归档至成功归档目录[cite: 1, 2]。

        Args:
            file_path: 待归档的源文件路径。
            success_path: 目标成功归档目录。

        Returns:
            Path: 归档后的最终目标文件路径。
        """
        return self._safe_move(Path(file_path), Path(success_path))

    def archive_error(
        self, file_path: Union[str, Path], error_path: Union[str, Path]
    ) -> Path:
        """
        将文件移动至失败/故障隔离目录（Quarantine）[cite: 1, 2]。

        Args:
            file_path: 待隔离的源文件路径。
            error_path: 目标故障隔离目录。

        Returns:
            Path: 隔离后的最终目标文件路径。
        """
        return self._safe_move(Path(file_path), Path(error_path))

    def _safe_move(self, src: Path, dst_dir: Path) -> Path:
        """
        安全且原子化的物理文件移动核心逻辑。
        支持目录自动创建（自愈）与同名文件重命名避让[cite: 2]。
        """
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        # 1. 目录自愈机制：如果目标归档或隔离目录不存在，则自动递归创建
        if not dst_dir.exists():
            dst_dir.mkdir(parents=True, exist_ok=True)

        # 2. 解决重名冲突：若目标目录已存在同名文件，自动应用时间戳重命名策略[cite: 2]
        target_path = dst_dir / src.name
        if target_path.exists():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            new_name = f"{src.stem}_{timestamp}{src.suffix}"
            target_path = dst_dir / new_name

        try:
            # 3. 执行物理移动
            # shutil.move 在同文件系统/分区下会自动使用原子性的 os.rename
            # 若跨物理分区，它会自动降级为先安全 copy 后物理 delete，确保操作的高可用性
            shutil.move(str(src), str(target_path))
            return target_path
        except Exception as e:
            raise IOError(
                f"Failed to atomically archive file from '{src}' to '{target_path}' due to: {str(e)}"
            )
