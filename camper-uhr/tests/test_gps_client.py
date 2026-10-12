import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

import gps_client


class GpsClientAltitudeTests(unittest.TestCase):
    def setUp(self):
        gps_client.clear_simulated_fix()
        gps_client._motion_filter.reset()
        self.clock = 0
        with gps_client._lock:
            gps_client._real_latest.update(
                connected=False,
                latitude=None,
                longitude=None,
                speed_kmh=None,
                altitude_m=None,
                altitude_reference=None,
            )

    def status(self):
        route = {
            "start_lat": None,
            "start_lon": None,
            "dest_name": None,
            "dest_lat": None,
            "dest_lon": None,
        }
        with (
            patch.object(gps_client.settings_store, "load_trip", return_value=(0.0, None, None)),
            patch.object(gps_client.settings_store, "load_trip_route", return_value=route),
        ):
            return gps_client.get_status()

    def process(self, report):
        with patch.object(gps_client, "_record_trail_point"):
            for _ in range(5):
                self.clock += 1
                with patch.object(gps_client.time, "monotonic", return_value=self.clock):
                    gps_client._process_line(json.dumps(report).encode("utf-8"))

    def test_msl_altitude_has_priority_and_speed_is_converted(self):
        self.process(
            {
                "class": "TPV",
                "mode": 3,
                "lat": 49.9,
                "lon": 10.9,
                "speed": 10.0,
                "altMSL": 321.4,
                "altHAE": 369.2,
            }
        )
        status = self.status()
        self.assertAlmostEqual(status["speed_kmh"], 36.0)
        self.assertEqual(status["altitude_m"], 321.4)
        self.assertEqual(status["altitude_reference"], "msl")

    def test_hae_is_used_when_msl_is_unavailable(self):
        self.process(
            {
                "class": "TPV",
                "mode": 3,
                "lat": 49.9,
                "lon": 10.9,
                "altHAE": 369.2,
            }
        )
        status = self.status()
        self.assertEqual(status["altitude_m"], 369.2)
        self.assertEqual(status["altitude_reference"], "hae")

    def test_two_dimensional_fix_clears_old_altitude(self):
        self.process(
            {"class": "TPV", "mode": 3, "lat": 49.9, "lon": 10.9, "altMSL": 321.4}
        )
        self.process(
            {"class": "TPV", "mode": 2, "lat": 49.9, "lon": 10.9, "altMSL": 999.0}
        )
        status = self.status()
        self.assertIsNone(status["altitude_m"])
        self.assertIsNone(status["altitude_reference"])

    def test_simulation_exposes_altitude_and_restores_real_fix(self):
        with patch.object(gps_client, "_record_trail_point"):
            gps_client._handle_fix(49.9, 10.9, 1.0, 300.0, "msl")
            gps_client.set_simulated_fix(48.1, 11.5, 80.0, 540.0)
        self.assertEqual(self.status()["altitude_m"], 540.0)
        self.assertTrue(self.status()["simulation_active"])

        gps_client.clear_simulated_fix()
        self.assertEqual(self.status()["altitude_m"], 300.0)
        self.assertFalse(self.status()["simulation_active"])

    def test_course_validation_and_loss_of_fix(self):
        report = {"class": "TPV", "mode": 3, "lat": 49.9, "lon": 10.9, "speed": 10, "track": 90}
        self.process(report)
        self.assertEqual(self.status()["heading_deg"], 90)
        for course in [None, -1, 360, float('nan'), float('inf')]:
            self.process({**report, "track": course})
            self.assertIsNone(self.status()["heading_deg"])
        self.process({**report, "speed": 0})
        self.assertIsNone(self.status()["heading_deg"])
        self.process(report)
        self.process({"class": "TPV", "mode": 1})
        self.assertFalse(self.status()["connected"])
        self.assertIsNone(self.status()["heading_deg"])

    def test_simulated_course_validation_and_real_restore(self):
        from models import SimulatedPosition, GpsStatus
        with patch.object(gps_client, "_record_trail_point"):
            for now in range(5):
                with patch.object(gps_client.time, "monotonic", return_value=now):
                    gps_client._handle_fix(49.9, 10.9, 10, 300, "msl", 270)
            gps_client.set_simulated_fix(49.9, 10.9, 30, 300, 90)
        self.assertEqual(GpsStatus(**self.status()).heading_deg, 90)
        gps_client.clear_simulated_fix()
        self.assertEqual(self.status()["heading_deg"], 270)
        for course in [-1, 360, float('nan')]:
            with self.assertRaises(ValueError):
                SimulatedPosition(heading_deg=course)

    def test_simulation_api_forwards_course_and_rejects_invalid_values(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        with patch.object(gps_client, "set_simulated_fix") as simulate:
            response = client.post('/api/debug/simulate-position', json={
                'latitude': 49.9, 'longitude': 10.9, 'speed_kmh': 30,
                'altitude_m': 240, 'heading_deg': 90,
            })
            self.assertEqual(response.status_code, 200)
            simulate.assert_called_once_with(49.9, 10.9, 30, 240, 90)
            response = client.post('/api/debug/simulate-position', json={'heading_deg': 360})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(simulate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
