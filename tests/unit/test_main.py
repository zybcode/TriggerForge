from unittest.mock import patch
from triggerforge.main import main
import pytest

def test_main_exit_on_error():
    with patch("triggerforge.cli.run_cli_logic", side_effect=Exception("Critical")):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1