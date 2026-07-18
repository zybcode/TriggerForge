"""
TriggerForge - Event-driven directory orchestration engine.
Copyright (C) 2026  [zybcode]

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import subprocess
import sys
import re
import pytest
from pathlib import Path


def test_cli_version_flag():
    """验证版本格式是否符合语义化版本规范。"""
    result = subprocess.run(
        [sys.executable, "-m", "triggerforge.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert re.search(r"\d+\.\d+\.\d+", result.stdout) is not None


def test_cli_dry_run(integration_env: dict):
    """验证干跑模式。"""
    config_path = integration_env["config"]
    config_path.write_text("watch_folders: []")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "triggerforge.cli",
            "--config",
            str(config_path),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Dry run" in result.stdout


def test_cli_invalid_config():
    """验证格式错误时的退出状态码。"""
    result = subprocess.run(
        [sys.executable, "-m", "triggerforge.cli", "--config", "non_existent.yaml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "error" in result.stderr.lower()
