"""
TriggerForge - Clerk Journal Module
Author: zybcode
Description: Subprocess output interceptor and crash dumper. Records execution
             logs and outputs structured panic reports upon pipeline failures.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# 初始化配置默认 Logger，方便在没有 Systemd 环境下本地调试
logger = logging.getLogger("triggerforge.clerk.journal")


class ClerkJournal:
    """
    运行记录员 (Clerk Journal)[cite: 1, 2]
    负责捕获并格式化插件子进程的 stdout/stderr 标准流，并在进程崩溃或硬超时熔断时保存现场诊断数据[cite: 1, 2]。
    """

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Args:
            log_dir: 诊断报告（Panic Dump）保存的目标根目录。若为 None，默认保存在项目根目录下的 logs/ 目录。
        """
        self.log_dir = log_dir or Path("logs")
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """
        确保诊断报告目录存在。
        """
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create logging directory '{self.log_dir}': {e}")

    def record_output(self, plugin_name: str, stdout: str, stderr: str) -> None:
        """
        收集并规范化子进程的标准流输出。
        格式化后输出到系统控制台，以便对接主进程的日志收集器或 Systemd / journald[cite: 1]。
        """
        if stdout and stdout.strip():
            for line in stdout.splitlines():
                # 使用标准 Syslog 优先级标识前缀，便于 journalctl 按级别过滤[cite: 1]
                sys.stdout.write(f"<6>[{plugin_name}][STDOUT] {line}\n")
            sys.stdout.flush()

        if stderr and stderr.strip():
            for line in stderr.splitlines():
                sys.stderr.write(f"<3>[{plugin_name}][STDERR] {line}\n")
            sys.stderr.flush()

    def dump_panic_report(
        self,
        file_path: Path,
        plugin_name: str,
        exit_code: Optional[int],
        error_message: str,
        stdout: str,
        stderr: str,
        strategy_params: Dict[str, Any]
    ) -> Path:
        """
        当插件遭遇硬超时、段错误或非零状态退出崩溃时，Clerk 自动导出结构化的故障现场诊断报告[cite: 1, 2]。
        
        Args:
            file_path: 触发任务的源文件路径
            plugin_name: 异常插件的唯一标识名
            exit_code: 子进程退出状态码（若超时熔断被强杀，该值可能为 None 或负数）
            error_message: 框架或捕获到的底层异常简述
            stdout: 子进程崩溃前输出的 stdout 缓存
            stderr: 子进程崩溃前输出的 stderr 堆栈
            strategy_params: 触发该插件时所传入的 YAML 动态参数字典
            
        Returns:
            Path: 生成的 .panic.json 诊断文件路径
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        panic_filename = f"panic_{plugin_name}_{timestamp}.json"
        panic_file_path = self.log_dir / panic_filename

        # 构建高可读、结构化的故障现场元数据
        panic_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_file": {
                "name": file_path.name,
                "absolute_path": str(file_path.absolute()),
                "size_bytes": file_path.stat().st_size if file_path.exists() else -1
            },
            "failed_plugin": {
                "name": plugin_name,
                "exit_code": exit_code,
                "error_summary": error_message,
                "strategy_params": strategy_params
            },
            "environment_context": {
                "python_version": sys.version,
                "platform": sys.platform,
                "cwd": os.getcwd()
            },
            "captured_streams": {
                "stdout": stdout,
                "stderr": stderr
            }
        }

        try:
            with open(panic_file_path, "w", encoding="utf-8") as f:
                json.dump(panic_data, f, indent=4, ensure_ascii=False)
            
            # 向主系统警报，输出标准的故障记录
            sys.stderr.write(
                f"<2>[Clerk] PANIC DUMP CRITICAL: Plugin '{plugin_name}' failed catastrophically. "
                f"Diagnostic context dumped to '{panic_file_path.absolute()}'.\n"
            )
            sys.stderr.flush()
            
            return panic_file_path
        except Exception as e:
            fallback_err = f"[Clerk] Failed to write panic dump JSON: {e}"
            sys.stderr.write(f"<2>{fallback_err}\n")
            sys.stderr.flush()
            # 降级返回临时目录下的路径
            return Path("/tmp") / panic_filename