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

# TriggerForge v1.2 引擎核心（热加载机制）。
#
# 依据 docs/zh/dev_plan_v1.2.md §3.3：
#   - SIGHUP 信号监听（Windows 等不支持 SIGHUP 的平台优雅降级，
#     可通过 trigger_reload() 手动触发，测试亦走该入口）。
#   - 热加载原子性：接收信号后先经 ForgeConfigManager 完整审计，
#     校验失败则保持当前运行配置不变（回滚 = 不切换），输出错误
#     审计日志并告警；校验通过后以"校验-替换"原子操作整体切换
#     配置集（非逐字段替换），保证内存中配置集始终一致。
#   - 切换完成强制输出审计变更摘要（前后配置对比）。
#   - 回滚降级：新配置启动失败时自动回滚重启旧配置的 Looper。


from __future__ import annotations

import logging
import signal
import threading
from collections.abc import Callable
from pathlib import Path

from triggerforge.core.looper import TriggerForgeLooper
from triggerforge.core.schema import TriggerForgeConfigSchema
from triggerforge.utils.config_manager import AuditReport, ForgeConfigManager

logger = logging.getLogger("triggerforge.engine")

_READY_TIMEOUT_SECONDS = 15.0


class ConfigAuditError(Exception):
    """配置审计未通过（携带完整审计报告）。"""

    def __init__(self, report: AuditReport):
        self.report = report
        super().__init__(f"配置审计未通过（exit_code={report.exit_code}）")


class EngineCore:
    """引擎核心：持有 Looper 生命周期，提供配置热加载与回滚降级。"""

    def __init__(
        self,
        config_path: str | Path,
        looper_factory: Callable[[dict], TriggerForgeLooper] | None = None,
    ):
        self.config_path = Path(config_path)
        self._looper_factory = looper_factory or (
            lambda config: TriggerForgeLooper(config)
        )
        self.looper: TriggerForgeLooper | None = None
        self.current_config: dict | None = None
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        # 热加载状态
        self.reload_count = 0
        self.last_reload_error: str | None = None
        self.last_reload_summary: dict | None = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self) -> None:
        """审计启动配置并拉起 Looper（后台线程运行主循环）。"""
        config = self._audit_current_file()
        self._swap_looper(config)
        self.register_signal_handlers()
        logger.info(
            "TriggerForge engine started (config=%s, hot-reload=%s)",
            self.config_path,
            "SIGHUP" if hasattr(signal, "SIGHUP") else "manual/SIGHUP 不可用",
        )

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            if self.looper is not None:
                try:
                    self.looper.stop()
                except Exception as exc:
                    logger.warning("Looper stop raised: %s", exc)
                self.looper = None
                self.current_config = None

    def wait_ready(self, timeout: float = _READY_TIMEOUT_SECONDS) -> bool:
        """等待当前 Looper 完全就绪（监听器与工作线程挂载完毕）。"""
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            looper = self.looper
            if looper is not None and looper.ready:
                return True
            time.sleep(0.1)
        return False

    def serve_forever(self) -> None:
        """阻塞主线程直到 stop() 被调用（供 CLI 主进程驻留）。"""
        self._stop_event.wait()

    # ------------------------------------------------------------------
    # 信号监听（SIGHUP 热加载）
    # ------------------------------------------------------------------
    def register_signal_handlers(self) -> None:
        if not hasattr(signal, "SIGHUP"):
            logger.info("当前平台不支持 SIGHUP，热加载请调用 trigger_reload()")
            return
        try:
            signal.signal(signal.SIGHUP, self._handle_sighup)
            logger.info("已注册 SIGHUP 热加载信号处理")
        except (ValueError, OSError) as exc:
            # 非主线程注册等场景：优雅降级，不阻断启动
            logger.warning("SIGHUP 注册失败（%s），热加载降级为手动触发", exc)

    def _handle_sighup(self, signum, frame) -> None:
        logger.info("收到 SIGHUP（%s），触发配置热加载...", signum)
        self.trigger_reload()

    # ------------------------------------------------------------------
    # 热加载：审计 → 原子切换 → 回滚降级
    # ------------------------------------------------------------------
    def trigger_reload(self) -> bool:
        """热加载入口。返回 True 表示切换成功，False 表示保持原配置。"""
        with self._lock:
            before_config = self.current_config
            try:
                manager = ForgeConfigManager(self.config_path)
                report = manager.audit()
            except Exception as exc:
                return self._reject_reload(None, f"审计引擎异常：{exc}")

            if report.exit_code != 0 or report.config is None:
                detail = (
                    "；".join(f"[{e.field}] {e.message}" for e in report.errors)
                    or f"exit_code={report.exit_code}"
                )
                return self._reject_reload(report, detail)

            new_config = report.config.model_dump()

            # ---- 原子切换："校验-替换"，非逐字段替换 ----
            old_looper = self.looper
            new_looper = self._looper_factory(new_config)
            new_thread = threading.Thread(
                target=new_looper.start,
                name="engine-looper",
                daemon=True,
            )
            try:
                if old_looper is not None:
                    old_looper.stop()
                new_thread.start()
                if not self._await_ready(new_looper):
                    raise RuntimeError("新配置 Looper 未在时限内就绪")
            except Exception as exc:
                # ---- 回滚降级：重启旧配置的 Looper ----
                logger.error("新配置启动失败，执行回滚降级：%s", exc)
                try:
                    new_looper.stop()
                except Exception:
                    pass
                if old_looper is not None:
                    rollback_thread = threading.Thread(
                        target=old_looper.start,
                        name="engine-looper-rollback",
                        daemon=True,
                    )
                    rollback_thread.start()
                    self._await_ready(old_looper)
                    self.looper = old_looper
                return self._reject_reload(report, f"新配置启动失败：{exc}")

            # ---- 切换成功：强制输出审计变更摘要 ----
            self.looper = new_looper
            self.current_config = new_config
            self.reload_count += 1
            self.last_reload_error = None
            self.last_reload_summary = {
                "before": self._config_digest(before_config),
                "after": self._config_digest(new_config),
            }
            logger.info(
                "配置热加载成功（第 %d 次）：%s",
                self.reload_count,
                self._diff_summary(before_config, new_config),
            )
            return True

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _audit_current_file(self) -> TriggerForgeConfigSchema:
        manager = ForgeConfigManager(self.config_path)
        report = manager.audit()
        if report.exit_code != 0 or report.config is None:
            raise ConfigAuditError(report)
        return report.config

    def _swap_looper(self, config: TriggerForgeConfigSchema) -> None:
        looper = self._looper_factory(config.model_dump())
        self.looper = looper
        self.current_config = config.model_dump()
        thread = threading.Thread(
            target=looper.start, name="engine-looper", daemon=True
        )
        thread.start()
        self._thread = thread
        if not self._await_ready(looper):
            raise RuntimeError("Looper 未在时限内就绪，启动失败")

    @staticmethod
    def _await_ready(looper: TriggerForgeLooper) -> bool:
        import time

        deadline = time.monotonic() + _READY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if looper.ready:
                return True
            time.sleep(0.1)
        return False

    def _reject_reload(self, report: AuditReport | None, detail: str) -> bool:
        """热加载失败：保持当前运行配置不变，输出错误审计日志并告警。"""
        self.last_reload_error = detail
        code = report.exit_code if report is not None else None
        logger.error(
            "配置热加载被拒绝（exit_code=%s），保持当前运行配置不变：%s",
            code,
            detail,
        )
        logger.warning("⚠️ 配置热加载告警：请修正 %s 后重新触发", self.config_path)
        if report is not None:
            for e in report.errors:
                logger.error("审计违规 [%s] %s", e.field, e.message)
        return False

    @staticmethod
    def _config_digest(config: dict | None) -> dict:
        if not config:
            return {}
        folders = config.get("watch_folders") or []
        return {
            "监控目录数": len(folders),
            "监控目录": [f.get("path") for f in folders],
            "策略总数": sum(len(f.get("strategies") or []) for f in folders),
            "插件根目录": config.get("plugin_directory"),
            "全局超时上限": config.get("max_execution_timeout"),
        }

    @staticmethod
    def _diff_summary(before: dict | None, after: dict) -> str:
        b = EngineCore._config_digest(before)
        a = EngineCore._config_digest(after)
        changes = []
        for key in a:
            if b.get(key) != a.get(key):
                changes.append(f"{key}: {b.get(key)} → {a.get(key)}")
        return "；".join(changes) if changes else "配置无实质变化"
