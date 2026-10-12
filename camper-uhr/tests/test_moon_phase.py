import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

import moon_phase


class MoonPhaseTests(unittest.TestCase):
    def test_new_moon(self):
        result = moon_phase.phase_from_fraction(0.0)
        self.assertEqual(result["phase_name"], "Neumond")
        self.assertEqual(result["illumination_pct"], 0.0)

    def test_full_moon(self):
        result = moon_phase.phase_from_fraction(0.5)
        self.assertEqual(result["phase_name"], "Vollmond")
        self.assertEqual(result["illumination_pct"], 100.0)

    def test_fraction_wraps_at_one(self):
        self.assertEqual(
            moon_phase.phase_from_fraction(1.0)["phase_name"],
            moon_phase.phase_from_fraction(0.0)["phase_name"],
        )


if __name__ == "__main__":
    unittest.main()
