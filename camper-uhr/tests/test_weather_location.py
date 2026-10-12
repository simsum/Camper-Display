import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))
import weather_location as location


class LocationTests(unittest.TestCase):
    def test_town_and_country_without_street(self):
        with patch.object(location, 'get_json', return_value={'address': {'town': 'Bamberg', 'country': 'Deutschland', 'road': 'Private Straße'}}) as request:
            self.assertEqual(location.resolve(49.9, 10.9), 'Bamberg · Deutschland')
        self.assertEqual(request.call_args.kwargs['lat'], 49.9)
        self.assertEqual(request.call_args.kwargs['zoom'], 10)

    def test_nonblocking_dedup_and_coordinate_binding(self):
        cache = location.LocationNames()
        entered, release = threading.Event(), threading.Event()
        def resolve(*args):
            entered.set()
            release.wait(2)
            return 'Ort A'
        with patch.object(location, 'resolve', side_effect=resolve) as call:
            self.assertIsNone(cache.get(1, 2))
            self.assertTrue(entered.wait(1))
            self.assertIsNone(cache.get(1, 2))
            self.assertIsNone(cache.get(3, 4))
            self.assertEqual(call.call_count, 1)
            release.set()
            # Join this one worker without depending on timing sleeps.
            for thread in threading.enumerate():
                if thread is not threading.current_thread() and thread.name.endswith('(_fetch)'):
                    thread.join(2)
            self.assertEqual(cache.get(1, 2), 'Ort A')
            self.assertNotIn((3, 4), cache.cache)

    def test_negative_cache_and_bounded_memory(self):
        cache = location.LocationNames()
        with patch.object(location, 'resolve', side_effect=OSError('offline')) as call:
            cache._fetch((1, 2))
            self.assertIsNone(cache.get(1, 2))
            self.assertEqual(call.call_count, 1)
            for i in range(20): cache._fetch((i, i))
        self.assertLessEqual(len(cache.cache), 8)


if __name__ == '__main__': unittest.main()
