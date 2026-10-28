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

# TriggerForge v1.2 配置审计引擎（ForgeConfigManager）。
#
# 依据 docs/zh/dev_plan_v1.2.md §3.2：
#   - --check 模式 + 结构化 JSON 输出（CI=true 环境自动切换）
#   - 退出码规范：0 合规 / 1 违规 / 2 文件缺失或 YAML 语法错误 / 3 内部异常
#   - 违规检测：Schema 校验（含 priority 双重约束）+ 超时越权策略审计
#   - 弃用配置项触发 DeprecationWarning，归档进审计报告 warnings 分区
#
# 审计结果同时写入审计日志（logs/config_audit.log，RotatingFileHandler）。


from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import yaml

from triggerforge.core.schema import TriggerForgeConfigSchema

logger = logging.getLogger("triggerforge.audit")

EXIT_OK = 0  # 合规
EXIT_VIOLATION = 1  # 违规（含 Schema 校验失败）
EXIT_SYNTAX = 2  # 文件缺失或 YAML 语法错误
EXIT_INTERNAL = 3  # 内部执行异常


def _setup_audit_log() -> None:
    """审计日志：logs/config_audit.log（50MB × 3）。"""
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "config_audit.log",
            maxBytes=50 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        audit = logging.getLogger("triggerforge.audit")
        if not any(isinstance(h, RotatingFileHandler) for h in audit.handlers):
            audit.addHandler(handler)
        audit.setLevel(logging.INFO)
    except OSError:
        # 审计日志不可写不阻断审计本身（如只读环境）
        pass


@dataclass
class AuditIssue:
    """单条审计发现。field 为配置定位路径（点分），message 为人可读描述。"""

    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


@dataclass
class AuditReport:
    """审计报告：结构化输出与人可读渲染共用同一数据源。

    config 字段在审计通过时携带校验后的 TriggerForgeConfigSchema 实例，
    供热加载引擎直接执行"校验-替换"原子切换，避免二次解析。
    """

    exit_code: int
    errors: list[AuditIssue] = field(default_factory=list)
    warnings: list[AuditIssue] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    config: TriggerForgeConfigSchema | None = None

    @property
    def status(self) -> str:
        if self.exit_code == EXIT_OK:
            return "pass"
        if self.exit_code in (EXIT_VIOLATION, EXIT_SYNTAX):
            return "fail"
        return "error"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
            "summary": self.summary,
        }

    def render_human(self) -> str:
        lines = ["=" * 60, "TriggerForge 配置审计报告", "=" * 60]
        verdict = {
            EXIT_OK: "✅ 合规（PASS）",
            EXIT_VIOLATION: "❌ 违规（FAIL）",
            EXIT_SYNTAX: "❌ 语法/文件错误（FAIL）",
            EXIT_INTERNAL: "💥 内部异常（ERROR）",
        }
        lines.append(f"审计结论：{verdict.get(self.exit_code, '未知')}")
        if self.summary:
            lines.append("")
            lines.append("【配置摘要】")
            for key, value in self.summary.items():
                lines.append(f"  {key}：{value}")
        if self.errors:
            lines.append("")
            lines.append("【违规项】")
            for e in self.errors:
                lines.append(f"  - [{e.field}] {e.message}")
        if self.warnings:
            lines.append("")
            lines.append("【弃用警告】")
            for w in self.warnings:
                lines.append(f"  - [{w.field}] {w.message}")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


class ForgeConfigManager:
    """配置审计引擎：加载 → Schema 校验 → 策略越权审计 → 报告。"""

    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)

    # ------------------------------------------------------------------
    # 加载与校验
    # ------------------------------------------------------------------
    def load_raw(self) -> dict[str, Any]:
        """读取 YAML；文件缺失或语法错误抛 FileNotFoundError/YamlError。"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def audit(self) -> AuditReport:
        """执行完整审计，永不抛出业务异常（内部异常归档为 exit_code=3）。"""
        _setup_audit_log()
        try:
            return self._audit_inner()
        except (FileNotFoundError, yaml.YAMLError) as exc:
            report = AuditReport(
                exit_code=EXIT_SYNTAX,
                errors=[AuditIssue("config", str(exc))],
            )
        except Exception as exc:  # 内部执行异常兜底
            report = AuditReport(
                exit_code=EXIT_INTERNAL,
                errors=[AuditIssue("internal", f"{type(exc).__name__}: {exc}")],
            )
        self._log_audit(report)
        return report

    def _audit_inner(self) -> AuditReport:
        raw = self.load_raw()

        # 捕获弃用告警归档进报告
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            try:
                config = TriggerForgeConfigSchema(**raw)
            except Exception as exc:
                # Schema 校验失败 = 违规（含 priority 双重约束）
                return AuditReport(
                    exit_code=EXIT_VIOLATION,
                    errors=[AuditIssue("schema", str(exc))],
                    summary=self._summary(raw),
                )

        warn_issues = [AuditIssue("deprecated", str(w.message)) for w in caught]

        # 策略越权审计：超时硬上限
        errors = self._audit_timeout_policy(config)

        report = AuditReport(
            exit_code=EXIT_VIOLATION if errors else EXIT_OK,
            errors=errors,
            warnings=warn_issues,
            summary=self._summary(config.model_dump()),
            config=config,
        )
        self._log_audit(report)
        return report

    def _audit_timeout_policy(
        self, config: TriggerForgeConfigSchema
    ) -> list[AuditIssue]:
        """超时越权审计：无豁免的策略不得突破 max_execution_timeout。"""
        errors: list[AuditIssue] = []
        cap = config.max_execution_timeout
        if cap is None:
            return errors
        for i, folder in enumerate(config.watch_folders):
            for j, strategy in enumerate(folder.strategies):
                if strategy.timeout <= cap:
                    continue
                exempt = strategy.priority == "high" and strategy.allow_override_timeout
                if exempt:
                    continue
                errors.append(
                    AuditIssue(
                        field=(
                            f"watch_folders[{i}].strategies[{j}]"
                            f"({strategy.plugin_name})"
                        ),
                        message=(
                            f"timeout={strategy.timeout} 超过全局硬上限 "
                            f"max_execution_timeout={cap}，且未同时满足 "
                            'priority="high" + allow_override_timeout=true '
                            "的豁免条件（资源防锁死约束）"
                        ),
                    )
                )
        return errors

    @staticmethod
    def _summary(data: dict[str, Any]) -> dict[str, Any]:
        folders = data.get("watch_folders") or []
        return {
            "监控目录数": len(folders),
            "插件策略总数": sum(len(f.get("strategies") or []) for f in folders),
            "插件根目录": data.get("plugin_directory", "./plugins"),
            "全局超时上限": data.get("max_execution_timeout", "未设置"),
        }

    @staticmethod
    def _log_audit(report: AuditReport) -> None:
        level = logging.INFO if report.exit_code == EXIT_OK else logging.ERROR
        logger.log(
            level,
            "配置审计完成 path=%s status=%s exit_code=%s errors=%d warnings=%d",
            report.summary.get("配置摘要", ""),
            report.status,
            report.exit_code,
            len(report.errors),
            len(report.warnings),
        )
        for e in report.errors:
            logger.error("审计违规 [%s] %s", e.field, e.message)
        for w in report.warnings:
            logger.warning("弃用配置 [%s] %s", w.field, w.message)


# ----------------------------------------------------------------------
# CLI 入口（--check 模式）
# ----------------------------------------------------------------------
def _is_ci_mode() -> bool:
    return os.environ.get("CI", "").lower() == "true"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="config_manager", description="TriggerForge 配置审计引擎"
    )
    parser.add_argument("--check", action="store_true", help="执行配置合规性审计")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="待审计的配置文件路径（默认 ./config.yaml）",
    )
    return parser


def run_check(config_path: str | Path) -> int:
    """执行审计并输出报告，返回规范退出码（0/1/2/3）。"""
    manager = ForgeConfigManager(config_path)
    report = manager.audit()

    if _is_ci_mode():
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.render_human())
    return report.exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.check:
        print("未指定 --check，无事可做（usage: config_manager.py --check）")
        return EXIT_INTERNAL
    try:
        return run_check(args.config)
    except Exception as exc:  # 兜底：审计器自身崩溃
        logger.exception("审计引擎内部异常")
        if _is_ci_mode():
            print(
                json.dumps(
                    {
                        "status": "error",
                        "exit_code": EXIT_INTERNAL,
                        "errors": [{"field": "internal", "message": str(exc)}],
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"内部异常：{exc}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
