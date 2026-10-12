import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

import weather_client


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "current": {
                "temperature_2m": 17.4,
                "apparent_temperature": 16.1,
                "precipitation": 0.0,
                "weather_code": 2,
                "wind_speed_10m": 18.2,
            },
            "daily": {
                "time": ["2026-09-10", "2026-09-11", "2026-09-12", "2026-09-13"],
                "weather_code": [2, 1, 0, 61],
                "temperature_2m_max": [17.0, 19.0, 22.0, 18.0],
                "temperature_2m_min": [9.0, 10.0, 11.0, 9.0],
                "precipitation_probability_max": [35.0, 20.0, 10.0, 60.0],
                "precipitation_sum": [2.4, 0.8, 0.0, 6.7],
                "sunrise": ["2026-09-10T06:40"] * 4,
                "sunset": ["2026-09-10T19:35"] * 4,
                "daylight_duration": [46500.0] * 4,
                "moonrise": ["2026-09-10T05:41"] * 4,
                "moonset": ["2026-09-10T19:13"] * 4,
                "moon_phase": [0.974] * 4,
            },
        }


class WeatherClientTests(unittest.TestCase):
    def setUp(self):
        weather_client._cache = {"expires_at": 0.0, "data": None}
        location = patch.object(weather_client.weather_location.names, 'get', return_value='Bamberg · Deutschland')
        location.start()
        self.addCleanup(location.stop)

    def test_current_conditions_and_four_day_rainfall(self):
        with patch.object(weather_client.httpx, "get", return_value=FakeResponse()) as get:
            result = weather_client.get_weather(49.9, 10.9, True)

        self.assertTrue(result["available"])
        self.assertEqual(result["apparent_temperature"], 16.1)
        self.assertEqual(result["wind_speed"], 18.2)
        self.assertEqual(len(result["forecast"]), 4)
        self.assertEqual(result["forecast"][0]["date"], "2026-09-10")
        self.assertEqual(result["forecast"][0]["precipitation_sum"], 2.4)
        self.assertEqual(result["forecast"][3]["precipitation_sum"], 6.7)
        self.assertEqual(result["daylight_duration_seconds"], 46500.0)
        self.assertEqual(result["moonrise"], "2026-09-10T05:41")
        self.assertEqual(result["moonset"], "2026-09-10T19:13")
        self.assertEqual(result["moon_phase_fraction"], 0.974)
        params = get.call_args.kwargs["params"]
        self.assertIn("apparent_temperature", params["current"])
        self.assertIn("precipitation_sum", params["daily"])
        self.assertIn("moonrise", params["daily"])
        self.assertIn("moonset", params["daily"])
        self.assertIn("moon_phase", params["daily"])
        self.assertEqual(weather_client._CACHE_SECONDS, 7200)

    def test_cached_location_stays_with_weather_not_new_gps(self):
        with patch.object(weather_client.httpx, 'get', return_value=FakeResponse()) as get:
            first = weather_client.get_weather(49.9, 10.9, True)
            cached = weather_client.get_weather(48.1, 11.5, True)
        self.assertEqual(get.call_count, 1)
        self.assertEqual((cached['latitude'], cached['longitude']), (49.9, 10.9))
        self.assertEqual(cached['location_name'], first['location_name'])
        self.assertNotIn('location_name', weather_client._cache['data'])

    def test_location_failure_does_not_hide_weather(self):
        with patch.object(weather_client.httpx, 'get', return_value=FakeResponse()), patch.object(weather_client.weather_location.names, 'get', return_value=None):
            result = weather_client.get_weather(49.9, 10.9, True)
        self.assertTrue(result['available'])
        self.assertIsNone(result['location_name'])
        self.assertEqual(result['latitude'], 49.9)


if __name__ == "__main__":
    unittest.main()
