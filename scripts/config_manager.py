# TriggerForge - Event-driven directory orchestration engine.
# Copyright (C) 2026  [zybcode]
# GNU General Public License v3 or later. See <https://www.gnu.org/licenses/>.

"""配置审计引擎命令行入口（v1.2 迁移指引引用）。

用法（见 docs/zh/migration_v1.2.md 第三步）：
    python scripts/config_manager.py --check
    python scripts/config_manager.py --check --config path/to/config.yaml
    CI=true python scripts/config_manager.py --check   # 结构化 JSON 输出

退出码：0 合规 / 1 违规 / 2 文件缺失或 YAML 语法错误 / 3 内部异常。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 保证从任意工作目录执行均可导入 src 布局的项目包
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from triggerforge.utils.config_manager import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
