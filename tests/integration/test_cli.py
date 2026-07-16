import subprocess
import sys
import re
import pytest
from pathlib import Path

def test_cli_version_flag():
    """验证版本格式是否符合语义化版本规范。"""
    result = subprocess.run([sys.executable, "-m", "triggerforge.cli", "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert re.search(r'\d+\.\d+\.\d+', result.stdout) is not None

def test_cli_dry_run(integration_env: dict):
    """验证干跑模式。"""
    config_path = integration_env["config"]
    config_path.write_text("watch_folders: []")
    
    result = subprocess.run(
        [sys.executable, "-m", "triggerforge.cli", "--config", str(config_path), "--dry-run"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Dry run" in result.stdout

def test_cli_invalid_config():
    """验证格式错误时的退出状态码。"""
    result = subprocess.run(
        [sys.executable, "-m", "triggerforge.cli", "--config", "non_existent.yaml"],
        capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "error" in result.stderr.lower()