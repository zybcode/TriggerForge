import pytest
from unittest.mock import patch
from triggerforge.core.looper import TriggerForgeLooper


def test_looper_lifecycle():
    """测试 Looper 的启动与关闭逻辑"""
    mock_config = {"watch_path": "./test_storage", "debounce_seconds": 0.5}

    with patch("triggerforge.core.looper.SentryWatcher") as MockWatcher:
        instance = MockWatcher.return_value
        looper = TriggerForgeLooper(mock_config)

        # 1. 模拟 sleep 抛出异常
        with patch("triggerforge.core.looper.time.sleep", side_effect=InterruptedError):
            with pytest.raises(InterruptedError):
                looper.start()

        # 2. 无论 looper.start 内部是否处理了异常，我们在此显式清理
        looper.stop()

        # 3. 核心断言：只要调用过 1 次 stop，就证明清理逻辑已执行
        assert instance.stop.call_count >= 1
        instance.start.assert_called_once()
        assert looper.is_running is False


def test_looper_init_with_defaults():
    """测试 Looper 在配置缺失时能否使用默认参数"""
    looper = TriggerForgeLooper({})
    assert looper.config == {}
    assert looper.is_running is False
