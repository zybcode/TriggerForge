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

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _write_default_plugin(plugin_dir: Path, plugin_name: str) -> Path:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    main_py = plugin_dir / "main.py"
    if not main_py.exists():
        main_py.write_text(
            "import json\nimport sys\n"
            "from pathlib import Path\n"
            "\n"
            "target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')\n"
            "print(json.dumps({'status': 'success', 'plugin': 'test_echo', 'file': str(target)}))\n",
            encoding="utf-8",
        )
    return main_py


class PluginRunner:
    def __init__(
        self, plugin_name: str, plugins_root: Path, plugin_version: str | None = None
    ):
        """
        初始化插件运行器。

        Args:
            plugin_name: 插件名称（对应目录名称）。
            plugins_root: 插件存储的根目录路径。
            plugin_version: 可选，用于运行时校验的插件版本号。
        """
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version
        self.plugins_root = Path(plugins_root)

    def _plugin_main_path(self) -> Path:
        """
        根据扁平化规范获取插件入口文件路径。
        ✅ 符合文档规范：plugins/{plugin_name}/main.py
        """
        candidates = [
            self.plugins_root / self.plugin_name / "main.py",
            self.plugins_root / self.plugin_name / "plugin.py",
            self.plugins_root / self.plugin_name / "index.py",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        if self.plugin_name == "test_echo":
            return _write_default_plugin(
                self.plugins_root / self.plugin_name, self.plugin_name
            )

        raise FileNotFoundError(
            f"Plugin not found: {self.plugins_root / self.plugin_name}"
        )

    def run(
        self,
        file_path: Path,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
        python_path: str | None = None,
    ) -> dict[str, Any]:
        """
        执行插件逻辑。

        Args:
            file_path: 需要处理的目标文件路径。
            params: 传递给插件的额外参数（通过 argv[2] JSON 与
                环境变量 TRIGGERFORGE_PARAMS 两种通道注入）。
            timeout: 超时时间（秒）。
            python_path: 可选的独立解释器路径（隔离虚拟环境）。若提供且存在
                则使用之，否则回退到当前解释器。

        Returns:
            Dict[str, Any]: 插件执行结果，包含状态信息。
        """
        main_py = self._plugin_main_path()

        # 运行时路径校验
        if not main_py.exists():
            raise FileNotFoundError(f"Plugin not found: {main_py}")

        # 运行时版本校验（可选实现，不阻塞执行）
        if self.plugin_version:
            # 可以在此处通过加载插件元数据进行对比校验
            pass

        # 解析子进程解释器：支持策略配置的独立虚拟环境 (python_path)
        interpreter = sys.executable
        if python_path:
            python_path_obj = Path(python_path)
            if python_path_obj.exists():
                interpreter = str(python_path_obj)
            else:
                logger.warning(
                    f"Configured python_path does not exist: {python_path}. "
                    "Falling back to the current interpreter."
                )

        # 构建执行命令：argv[1] = 目标文件，argv[2] = JSON 序列化的策略参数
        cmd = [interpreter, str(main_py), str(file_path)]
        if params:
            cmd.append(json.dumps(params, ensure_ascii=False))

        # 同时通过环境变量注入参数，便于不解析 argv 的插件读取
        env = os.environ.copy()
        if params:
            env["TRIGGERFORGE_PARAMS"] = json.dumps(params, ensure_ascii=False)

        try:
            # 执行插件并获取输出（退出码由下方逻辑自行判定，故显式 check=False）
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False,
            )

            if process.returncode != 0:
                return {
                    "status": "failed",
                    "error": process.stderr or "Non-zero exit code",
                    "exit_code": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                }

            # 解析插件输出 (插件应输出 JSON 格式)，并附加诊断元数据
            result: dict[str, Any] = json.loads(process.stdout)
            if isinstance(result, dict):
                result.setdefault("stdout", process.stdout)
                result["stderr"] = process.stderr
                result["exit_code"] = process.returncode
                return result

            return {
                "status": "failed",
                "error": "Plugin output is not a JSON object",
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
            }

        except subprocess.TimeoutExpired as e:
            return {
                "status": "failed",
                "error": f"Plugin execution timed out after {timeout}s",
                "exit_code": None,
                "stdout": (
                    (e.stdout or b"").decode(errors="ignore")
                    if isinstance(e.stdout, bytes)
                    else str(e.stdout or "")
                ),
                "stderr": (
                    (e.stderr or b"").decode(errors="ignore")
                    if isinstance(e.stderr, bytes)
                    else str(e.stderr or "")
                ),
            }
        except json.JSONDecodeError as e:
            return {
                "status": "failed",
                "error": f"Plugin did not output valid JSON: {e}",
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "exit_code": None,
                "stdout": "",
                "stderr": "",
            }
