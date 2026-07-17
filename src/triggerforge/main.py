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
