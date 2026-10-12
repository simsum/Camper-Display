import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))
from gps_client import MotionFilter


class MotionFilterTests(unittest.TestCase):
    def test_stationary_noise_and_single_spikes(self):
        f = MotionFilter()
        for t, speed in enumerate([0, .5, 2, 1, 18, .5, 1, 0, 9, 1, 0, 2]):
            self.assertEqual(f.update(speed, t * 25, t), (0, None))

    def test_start_stop_and_isolated_driving_spike(self):
        f = MotionFilter()
        for t in range(5): speed, heading = f.update(36, 90, t)
        self.assertAlmostEqual(speed, 36)
        self.assertAlmostEqual(heading, 90)
        speed, heading = f.update(140, 270, 5)
        self.assertAlmostEqual(speed, 36)
        self.assertAlmostEqual(heading, 90)
        for t in range(6, 11): speed, heading = f.update(0, 270, t)
        self.assertEqual((speed, heading), (0, None))

    def test_heading_wrap_and_genuine_turn(self):
        f = MotionFilter()
        for t in range(7): f.update(40, 359, t)
        for t in range(7, 12): speed, heading = f.update(40, 1, t)
        self.assertTrue(heading < 5 or heading > 355)
        for t in range(12, 20): speed, heading = f.update(40, 90, t)
        self.assertLess(abs(heading - 90), 2)

    def test_stale_invalid_and_slow_course(self):
        f = MotionFilter()
        for t in range(7): f.update(30, 90, t)
        self.assertEqual(f.update(None, 90, 7), (None, None))
        self.assertEqual(f.update(30, 270, 8), (0, None))
        for t in range(9, 15): f.update(30, 90, t)
        self.assertEqual(f.update(30, 270, 30), (0, None))
        for t in range(31, 37): f.update(30, 90, t)
        for t in range(37, 43): speed, heading = f.update(3, 270, t)
        self.assertAlmostEqual(heading, 90)

    def test_confirmation_is_time_based(self):
        f = MotionFilter()
        for n in range(100):
            self.assertEqual(f.update(20, 90, n / 100), (0, None))


if __name__ == '__main__': unittest.main()
