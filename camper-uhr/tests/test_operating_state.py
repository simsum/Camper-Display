import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from models import Settings
from operating_state import StateEngine


class OperatingStateTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings()
        self.engine = StateEngine()

    def test_drive_and_stand_hysteresis(self):
        self.engine.update(True, 8.0, self.settings, 0)
        self.engine.update(True, 8.0, self.settings, 9)
        self.assertEqual(self.engine.snapshot(9)["mode"], "stand")
        self.engine.update(True, 8.0, self.settings, 10)
        self.assertEqual(self.engine.snapshot(10)["mode"], "drive")

        self.engine.update(True, 2.0, self.settings, 20)
        self.engine.update(True, 2.0, self.settings, 199)
        self.assertEqual(self.engine.snapshot(199)["mode"], "drive")
        self.engine.update(True, 2.0, self.settings, 200)
        self.assertEqual(self.engine.snapshot(200)["mode"], "stand")

    def test_gps_loss_holds_drive_for_five_minutes(self):
        self.engine.update(True, 20.0, self.settings, 0)
        self.engine.update(True, 20.0, self.settings, 10)
        self.engine.update(False, None, self.settings, 20)
        self.engine.update(False, None, self.settings, 319)
        self.assertEqual(self.engine.snapshot(319)["mode"], "drive")
        self.engine.update(False, None, self.settings, 320)
        self.assertEqual(self.engine.snapshot(320)["mode"], "stand")

    def test_force_mode_and_manual_wake(self):
        self.engine.set_forced_mode("drive")
        self.assertEqual(self.engine.snapshot(0)["mode"], "drive")
        self.engine.set_forced_mode(None)
        self.assertEqual(self.engine.snapshot(0)["mode"], "stand")

        self.engine.start_manual_wake(120, 5)
        self.assertEqual(self.engine.snapshot(6)["manual_wake_remaining_seconds"], 119)
        self.assertFalse(self.engine.snapshot(125)["manual_wake_active"])


if __name__ == "__main__":
    unittest.main()
