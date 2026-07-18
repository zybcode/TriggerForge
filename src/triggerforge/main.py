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

"""
TriggerForge main entrypoint exposed as triggerforge.main.
"""

from __future__ import annotations

import sys
import logging

from triggerforge.cli import parse_args, run_cli_logic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def main(argv=None):
    """TriggerForge 主入口。"""
    try:
        if argv is None and "pytest" in sys.argv[0]:
            argv = []
        args = parse_args(argv)
        return run_cli_logic(args)
    except KeyboardInterrupt:
        logging.info("TriggerForge received exit signal. Shutting down...")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Critical error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    raise SystemExit(main())
