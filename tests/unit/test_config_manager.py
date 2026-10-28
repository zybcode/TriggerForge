# TriggerForge - Event-driven directory orchestration engine.
# Copyright (C) 2026  [zybcode]
# GNU General Public License v3 or later. See <https://www.gnu.org/licenses/>.

"""ForgeConfigManager 配置审计引擎专项测试（v1.2 §3.2 / §5）。

覆盖退出码规范（0/1/2/3）、CI 结构化 JSON 输出、
priority 双重约束与超时越权审计、弃用配置项迁移告警。
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from triggerforge.core.schema import TriggerForgeConfigSchema
from triggerforge.utils.config_manager import (
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_SYNTAX,
    EXIT_VIOLATION,
    ForgeConfigManager,
    run_check,
)


def _write_config(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _base_config(**strategy_extra) -> dict:
    strategy = {"plugin_name": "test_echo", "timeout": 10}
    strategy.update(strategy_extra)
    return {
        "watch_folders": [
            {
                "path": "./watch",
                "success_path": "./success",
                "error_path": "./error",
                "strategies": [strategy],
            }
        ]
    }


# ----------------------------------------------------------------------
# 退出码 0：合规
# ----------------------------------------------------------------------
def test_audit_pass_valid_config(tmp_path: Path):
    config = _write_config(tmp_path / "config.yaml", _base_config())
    report = ForgeConfigManager(config).audit()

    assert report.exit_code == EXIT_OK
    assert report.status == "pass"
    assert report.errors == []
    assert report.config is not None


def test_run_check_exit_code_zero(tmp_path: Path, capsys):
    config = _write_config(tmp_path / "config.yaml", _base_config())
    assert run_check(config) == EXIT_OK
    assert "合规" in capsys.readouterr().out


# ----------------------------------------------------------------------
# 退出码 1：违规（双重约束 + 超时越权）
# ----------------------------------------------------------------------
def test_dual_constraint_requires_high_priority(tmp_path: Path):
    config = _write_config(
        tmp_path / "config.yaml",
        _base_config(allow_override_timeout=True, priority="standard"),
    )
    report = ForgeConfigManager(config).audit()

    assert report.exit_code == EXIT_VIOLATION
    assert any("allow_override_timeout" in e.message for e in report.errors)


def test_dual_constraint_low_priority_also_blocked(tmp_path: Path):
    config = _write_config(
        tmp_path / "config.yaml",
        _base_config(allow_override_timeout=True, priority="low"),
    )
    report = ForgeConfigManager(config).audit()
    assert report.exit_code == EXIT_VIOLATION


def test_exempt_high_priority_with_override_passes(tmp_path: Path):
    config = _write_config(
        tmp_path / "config.yaml",
        _base_config(allow_override_timeout=True, priority="high", timeout=999),
    )
    report = ForgeConfigManager(config).audit()
    assert report.exit_code == EXIT_OK


def test_timeout_violation_without_exemption(tmp_path: Path):
    data = _base_config(timeout=999)
    data["max_execution_timeout"] = 60
    config = _write_config(tmp_path / "config.yaml", data)
    report = ForgeConfigManager(config).audit()

    assert report.exit_code == EXIT_VIOLATION
    assert any("max_execution_timeout" in e.message for e in report.errors)


def test_timeout_within_cap_passes(tmp_path: Path):
    data = _base_config(timeout=30)
    data["max_execution_timeout"] = 60
    config = _write_config(tmp_path / "config.yaml", data)
    report = ForgeConfigManager(config).audit()
    assert report.exit_code == EXIT_OK


def test_bad_strategy_type_is_violation_not_crash(tmp_path: Path):
    data = _base_config()
    data["watch_folders"][0]["strategies"][0]["timeout"] = "not-a-number"
    config = _write_config(tmp_path / "config.yaml", data)
    report = ForgeConfigManager(config).audit()
    assert report.exit_code == EXIT_VIOLATION


# ----------------------------------------------------------------------
# 退出码 2：文件缺失 / YAML 语法错误
# ----------------------------------------------------------------------
def test_missing_file_is_syntax_exit(tmp_path: Path):
    report = ForgeConfigManager(tmp_path / "nope.yaml").audit()
    assert report.exit_code == EXIT_SYNTAX
    assert report.errors


def test_yaml_syntax_error_is_syntax_exit(tmp_path: Path):
    config = tmp_path / "broken.yaml"
    config.write_text("watch_folders: [unclosed", encoding="utf-8")
    report = ForgeConfigManager(config).audit()
    assert report.exit_code == EXIT_SYNTAX


# ----------------------------------------------------------------------
# CI 模式：结构化 JSON 输出
# ----------------------------------------------------------------------
def test_ci_mode_outputs_structured_json(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.setenv("CI", "true")
    data = _base_config(allow_override_timeout=True, priority="standard")
    config = _write_config(tmp_path / "config.yaml", data)

    exit_code = run_check(config)
    output = capsys.readouterr().out

    assert exit_code == EXIT_VIOLATION
    payload = json.loads(output)
    assert payload["status"] == "fail"
    assert payload["exit_code"] == EXIT_VIOLATION
    assert isinstance(payload["errors"], list)
    assert {"field", "message"} <= set(payload["errors"][0])


def test_ci_mode_pass_payload(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.setenv("CI", "true")
    config = _write_config(tmp_path / "config.yaml", _base_config())
    exit_code = run_check(config)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == EXIT_OK
    assert payload["status"] == "pass"
    assert payload["errors"] == []


# ----------------------------------------------------------------------
# 弃用配置项迁移（migration_v1.2.md）
# ----------------------------------------------------------------------
def test_global_timeout_deprecated_mapping(tmp_path: Path):
    data = _base_config()
    data["timeout"] = 120  # 旧全局 timeout
    config = _write_config(tmp_path / "config.yaml", data)

    report = ForgeConfigManager(config).audit()

    assert report.exit_code == EXIT_OK
    assert report.config is not None
    assert report.config.max_execution_timeout == 120
    assert report.config.model_dump().get("timeout") is None
    # 弃用告警归档进审计报告 warnings 分区
    assert any("timeout" in w.message for w in report.warnings)


def test_legacy_flat_strategy_timeout_warns(tmp_path: Path):
    config = _write_config(tmp_path / "config.yaml", _base_config(timeout=45))
    report = ForgeConfigManager(config).audit()

    assert report.exit_code == EXIT_OK
    assert report.config.watch_folders[0].strategies[0].timeout == 45
    assert any("strategies[].timeout" in w.message for w in report.warnings)


def test_nested_strategy_object_is_new_standard(tmp_path: Path):
    data = _base_config()
    data["watch_folders"][0]["strategies"][0] = {
        "plugin_name": "test_echo",
        "strategy": {"timeout": 60, "priority": "standard"},
    }
    config = _write_config(tmp_path / "config.yaml", data)
    report = ForgeConfigManager(config).audit()

    assert report.exit_code == EXIT_OK
    strategy = report.config.watch_folders[0].strategies[0]
    assert strategy.timeout == 60
    assert strategy.priority == "standard"
    assert report.warnings == []


def test_nested_overrides_flat_on_conflict(tmp_path: Path):
    data = _base_config(timeout=10)
    data["watch_folders"][0]["strategies"][0]["strategy"] = {"timeout": 99}
    config = TriggerForgeConfigSchema(**data)
    assert config.watch_folders[0].strategies[0].timeout == 99


# ----------------------------------------------------------------------
# 商业扩展槽与内部异常兜底
# ----------------------------------------------------------------------
def test_metadata_slot_is_accepted_and_ignored(tmp_path: Path):
    data = _base_config(metadata={"signature": "sha256:abc", "license_hash": "xyz"})
    config = _write_config(tmp_path / "config.yaml", data)
    report = ForgeConfigManager(config).audit()

    assert report.exit_code == EXIT_OK
    assert report.config.watch_folders[0].strategies[0].metadata == {
        "signature": "sha256:abc",
        "license_hash": "xyz",
    }


def test_summary_counts_folders_and_strategies(tmp_path: Path):
    config = _write_config(tmp_path / "config.yaml", _base_config())
    report = ForgeConfigManager(config).audit()
    assert report.summary["监控目录数"] == 1
    assert report.summary["插件策略总数"] == 1


def test_internal_exception_exit_code(tmp_path: Path, monkeypatch):
    config = _write_config(tmp_path / "config.yaml", _base_config())
    manager = ForgeConfigManager(config)

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "load_raw", _boom)
    report = manager.audit()
    assert report.exit_code == EXIT_INTERNAL
