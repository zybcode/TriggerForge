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
from unittest.mock import patch
from triggerforge.main import main
import pytest


def test_main_exit_on_error():
    with patch("triggerforge.cli.run_cli_logic", side_effect=Exception("Critical")):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
