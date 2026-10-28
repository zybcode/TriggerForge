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

# Minimal CLI entrypoint for tests.

# Supports --help, --version, --config, --dry-run (schema validation)
# and --check (v1.2 configuration audit with exit codes 0/1/2/3).


from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml  # type: ignore

from triggerforge.core.looper import run_looper
from triggerforge.core.schema import TriggerForgeConfigSchema

VERSION = "1.2.0"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="triggerforge")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--config", type=str, help="Path to configuration YAML file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate config and exit"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the v1.2 configuration audit (exit codes 0/1/2/3)",
    )
    return parser.parse_args(argv)


def run_cli_logic(args) -> int:
    if getattr(args, "version", False):
        print(VERSION)
        return 0

    config_path = getattr(args, "config", None)
    if not config_path:
        raise FileNotFoundError("Missing required --config path")

    # v1.2：--check 接入配置审计引擎，退出码与 ForgeConfigManager 对齐
    if getattr(args, "check", False):
        from triggerforge.utils.config_manager import run_check

        return run_check(config_path)

    config_file = Path(config_path)
    if not config_file.exists():
        print(f"error: config file not found: {config_file}", file=sys.stderr)
        return 2

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        config_schema = TriggerForgeConfigSchema(**data)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if getattr(args, "dry_run", False):
        print("Dry run completed")
        return 0

    print("Starting TriggerForge Looper...")
    run_looper(config_schema.model_dump())
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    return run_cli_logic(args)


if __name__ == "__main__":
    raise SystemExit(main())
