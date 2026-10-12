import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

import display_scheduler


class DisplaySchedulerTests(unittest.TestCase):
    def test_power_on_restores_confirmed_left_rotation(self):
        with patch.object(display_scheduler.subprocess, "run") as run:
            run.return_value.returncode = 0
            display_scheduler._set_display_power(turn_on=True)

        run.assert_called_once_with(
            ["xrandr", "--output", "HDMI-1", "--rotate", "left", "--auto"],
            env={"DISPLAY": ":0"},
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertTrue(display_scheduler._state["display_on"])


if __name__ == "__main__":
    unittest.main()
