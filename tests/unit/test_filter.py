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

import pytest
from pathlib import Path
from triggerforge.core.sentry.filter import EventFilter


def test_filter_allow_by_extension():
    f = EventFilter(allowed_extensions=[".txt"])
    assert f.should_process(Path("data.txt")) is True
    assert f.should_process(Path("image.png")) is False


def test_filter_deny_by_extension():
    f = EventFilter(denied_extensions=[".tmp", ".log"])
    assert f.should_process(Path("data.txt")) is True
    assert f.should_process(Path("temp.tmp")) is False
    assert f.should_process(Path("system.log")) is False


def test_filter_regex_pattern():
    f = EventFilter(regex_pattern=r"^prefix_.*\.xml$")
    assert f.should_process(Path("prefix_order.xml")) is True
    assert f.should_process(Path("order.xml")) is False


def test_filter_duplicate_detection():
    f = EventFilter(duplicate_cooldown_seconds=1.0)
    test_file = Path("job.txt")
    assert f.should_process(test_file) is True
    assert f.should_process(test_file) is False  # 冷却期内拦截


def test_filter_empty_rules_fallback():
    f = EventFilter()
    assert f.should_process(Path("anything.dat")) is True
