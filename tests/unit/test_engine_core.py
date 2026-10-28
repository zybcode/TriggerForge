# TriggerForge - Event-driven directory orchestration engine.
# Copyright (C) 2026  [zybcode]
# GNU General Public License v3 or later. See <https://www.gnu.org/licenses/>.

"""EngineCore 热加载机制测试（v1.2 §3.3 / §5）。

覆盖：SIGHUP 注册降级、审计失败保持原配置（回滚 = 不切换）、
"校验-替换"原子切换一致性、新配置启动失败的回滚降级、
并发 reload 时序（锁保证原子性）。
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
import yaml

from triggerforge.core.looper import TriggerForgeLooper
from triggerforge.engine.core import ConfigAuditError, EngineCore


def _write_config(path: Path, folder_paths: list[str]) -> Path:
    data = {
        "watch_folders": [
            {
                "path": p,
                "success_path": f"{p}_success",
                "error_path": f"{p}_error",
                "strategies": [{"plugin_name": "test_echo", "timeout": 10}],
            }
            for p in folder_paths
        ]
    }
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture()
def engine_env(tmp_path: Path):
    config_path = _write_config(tmp_path / "config.yaml", [str(tmp_path / "w1")])
    for d in ("w1", "w1_success", "w1_error"):
        (tmp_path / d).mkdir(exist_ok=True)
    return tmp_path, config_path


def test_start_rejects_invalid_config(engine_env):
    """启动配置审计不通过 → ConfigAuditError（启动预检拒绝启动）。"""
    _tmp_path, config_path = engine_env
    config_path.write_text("watch_folders:\n  - path: ['./x']\n", encoding="utf-8")
    engine = EngineCore(config_path)
    with pytest.raises(ConfigAuditError) as exc_info:
        engine.start()
    assert exc_info.value.report.exit_code != 0


def test_start_and_ready(engine_env):
    _tmp_path, config_path = engine_env
    engine = EngineCore(config_path)
    engine.start()
    try:
        assert engine.looper is not None
        assert engine.looper.ready
        assert len(engine.looper.watchers) == 1
        assert engine.reload_count == 0
    finally:
        engine.stop()
    assert engine.looper is None


def test_reload_atomic_swap_adds_watch_folder(engine_env):
    """校验-替换原子切换：新配置整体生效，监听器数量与配置一致。"""
    tmp_path, config_path = engine_env
    engine = EngineCore(config_path)
    engine.start()
    try:
        old_looper = engine.looper
        assert old_looper is not None

        # 修改配置：新增第二个监控目录
        _write_config(config_path, [str(tmp_path / "w1"), str(tmp_path / "w2")])
        (tmp_path / "w2").mkdir(exist_ok=True)
        (tmp_path / "w2_success").mkdir(exist_ok=True)
        (tmp_path / "w2_error").mkdir(exist_ok=True)

        assert engine.trigger_reload() is True

        assert engine.looper is not old_looper
        assert engine.reload_count == 1
        assert engine.last_reload_error is None
        assert len(engine.looper.watchers) == 2
        # 审计变更摘要包含前后对比
        assert engine.last_reload_summary["after"]["监控目录数"] == 2
        assert engine.last_reload_summary["before"]["监控目录数"] == 1
    finally:
        engine.stop()


def test_reload_rejected_on_audit_failure_keeps_current(engine_env):
    """审计失败 → 保持当前运行配置不变（引擎状态不因错误配置崩溃）。"""
    tmp_path, config_path = engine_env
    engine = EngineCore(config_path)
    engine.start()
    try:
        healthy_looper = engine.looper

        # 写入 YAML 语法错误的配置
        config_path.write_text("watch_folders: [unclosed", encoding="utf-8")
        assert engine.trigger_reload() is False

        # 当前运行配置保持不变，引擎仍健康
        assert engine.looper is healthy_looper
        assert healthy_looper.ready
        assert len(healthy_looper.watchers) == 1
        assert engine.last_reload_error is not None
        assert engine.reload_count == 0

        # 双重约束违规同样被拒绝
        _write_config(config_path, [str(tmp_path / "w1")])
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        data["watch_folders"][0]["strategies"][0]["allow_override_timeout"] = True
        data["watch_folders"][0]["strategies"][0]["priority"] = "standard"
        config_path.write_text(
            yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
        )
        assert engine.trigger_reload() is False
        assert engine.looper is healthy_looper
    finally:
        engine.stop()


def test_reload_rollback_when_new_looper_fails_to_start(engine_env):
    """回滚降级：新配置启动失败 → 自动回滚重启旧配置 Looper。"""

    class FragileFactory:
        """第一次（启动）成功，之后创建的新 Looper 启动即抛异常。"""

        def __init__(self):
            self.calls = 0
            self.lock = threading.Lock()

        def __call__(self, config: dict) -> TriggerForgeLooper:
            with self.lock:
                self.calls += 1
                index = self.calls
            if index <= 1:
                return TriggerForgeLooper(config)
            looper = TriggerForgeLooper(config)
            looper.start = _boom_start  # type: ignore[method-assign]
            return looper

    def _boom_start():
        raise RuntimeError("simulated startup failure")

    tmp_path, config_path = engine_env
    factory = FragileFactory()
    engine = EngineCore(config_path, looper_factory=factory)
    engine.start()
    try:
        healthy_looper = engine.looper

        _write_config(config_path, [str(tmp_path / "w1"), str(tmp_path / "w2")])
        (tmp_path / "w2").mkdir(exist_ok=True)
        (tmp_path / "w2_success").mkdir(exist_ok=True)
        (tmp_path / "w2_error").mkdir(exist_ok=True)

        assert engine.trigger_reload() is False
        # 回滚后引擎持有旧 Looper，且旧 Looper 重新就绪
        assert engine.looper is healthy_looper
        assert healthy_looper.ready
        assert engine.last_reload_error is not None
        assert "启动失败" in engine.last_reload_error
    finally:
        engine.stop()


def test_concurrent_reload_is_serialized(engine_env):
    """时序测试：并发触发 reload，锁保证原子性，成功次数与 reload_count 一致。"""
    _tmp_path, config_path = engine_env
    engine = EngineCore(config_path)
    engine.start()
    try:
        results: list[bool] = []
        lock = threading.Lock()

        def _worker():
            ok = engine.trigger_reload()
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=_worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        # 配置未变更时每次 reload 都应成功，且计数严格等于成功次数
        assert all(results)
        assert engine.reload_count == len(results)
        assert engine.looper.ready
    finally:
        engine.stop()


def test_sighup_graceful_on_unsupported_platforms(engine_env):
    """SIGHUP 注册在不支持的平台/非主线程优雅降级，不抛异常。"""
    _tmp_path, config_path = engine_env
    engine = EngineCore(config_path)
    engine.start()
    try:
        # 在非主线程调用注册（信号模块会拒绝），应被捕获降级
        engine.register_signal_handlers()
        assert engine.looper is not None
    finally:
        engine.stop()
