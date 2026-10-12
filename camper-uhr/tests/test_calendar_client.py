import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


def feed(events):
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Camper Uhr Tests//DE\r\nX-WR-TIMEZONE:Europe/Berlin\r\n"
            + events.replace("\n", "\r\n") + "\r\nEND:VCALENDAR\r\n").encode()


SINGLE = """BEGIN:VEVENT
UID:holiday-1
DTSTART;VALUE=DATE:20261003
DTEND;VALUE=DATE:20261013
SUMMARY:Herbsttour
LOCATION:Südtirol
END:VEVENT"""


class CalendarTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
        self.addCleanup(sys.path.pop, 0)
        import calendar_client
        from models import Settings
        self.client = calendar_client
        self.Settings = Settings
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = patch.object(calendar_client.settings_store, "DB_PATH", Path(self.temp.name) / "test.db")
        self.db.start()
        self.addCleanup(self.db.stop)
        calendar_client._source = ""
        calendar_client._state = {}
        self.settings = Settings(calendar_enabled=True, calendar_url="webcal://p01-caldav.icloud.com/published/2/test-token")
        calendar_client.settings_store.save_settings(self.settings)

    def parse(self, events):
        return self.client.parse_calendar(feed(events), date(2026, 9, 11))

    def test_all_day_end_is_inclusive_in_vacation_and_text_is_preserved(self):
        trip, = self.parse(SINGLE)
        self.assertEqual(trip["start_date"], "2026-10-03")
        self.assertEqual(trip["end_date"], "2026-10-12")
        self.assertEqual(trip["destination"], "Südtirol")
        self.assertEqual(trip["id"], self.parse(SINGLE)[0]["id"])

    def test_one_day_and_year_boundary(self):
        event = SINGLE.replace("20261003", "20261231").replace("20261013", "20270103")
        self.assertEqual(self.parse(event)[0]["end_date"], "2027-01-02")
        self.assertEqual(self.parse(SINGLE.replace("DTEND;VALUE=DATE:20261013\n", ""))[0]["end_date"], "2026-10-03")

    def test_utc_and_dst_and_midnight_end(self):
        event = SINGLE.replace("DTSTART;VALUE=DATE:20261003", "DTSTART:20261024T220000Z").replace("DTEND;VALUE=DATE:20261013", "DTEND:20261025T230000Z")
        trip, = self.parse(event)
        self.assertEqual((trip["start_date"], trip["end_date"]), ("2026-10-25", "2026-10-25"))

    def test_recurrence_exclusions_and_moved_occurrence(self):
        event = SINGLE.replace("END:VEVENT", "RRULE:FREQ=YEARLY;COUNT=3\nEXDATE;VALUE=DATE:20271003\nEND:VEVENT")
        moved = SINGLE.replace("DTSTART;VALUE=DATE:20261003", "RECURRENCE-ID;VALUE=DATE:20281003\nDTSTART;VALUE=DATE:20281005").replace("20261013", "20281015").replace("Herbsttour", "Verschoben")
        trips = self.parse(event + "\n" + moved)
        self.assertEqual([trip["start_date"] for trip in trips], ["2026-10-03", "2028-10-05"])
        self.assertEqual(trips[-1]["name"], "Verschoben")

    def test_cancelled_and_empty_calendar(self):
        self.assertEqual(self.parse(SINGLE.replace("END:VEVENT", "STATUS:CANCELLED\nEND:VEVENT")), [])
        self.assertEqual(self.parse(""), [])

    def test_folded_and_escaped_location(self):
        event = SINGLE.replace("SUMMARY:Herbsttour", "SUMMARY:Unsere lange\n  Herbsttour").replace("LOCATION:Südtirol", "LOCATION:Bozen\\, Südtirol\\nItalien")
        trip, = self.parse(event)
        self.assertEqual(trip["name"], "Unsere lange Herbsttour")
        self.assertEqual(trip["destination"], "Bozen, Südtirol Italien")

    def test_invalid_calendar_is_not_a_successful_empty_import(self):
        with self.assertRaises(Exception):
            self.client.parse_calendar(b"<html>Server error</html>")
        with self.assertRaises(Exception):
            self.parse(SINGLE.replace("DTSTART;VALUE=DATE:20261003\n", ""))

    def test_link_validation(self):
        self.assertTrue(self.settings.calendar_url.startswith("https://"))
        for url in ["https://127.0.0.1/published/test", "http://p01-caldav.icloud.com/published/test", "https://p01-caldav.icloud.com.evil.test/published/test", "https://user:password@p01-caldav.icloud.com/published/test", "https://p01-caldav.icloud.com:22/published/test", "https://p01-caldav.icloud.com/private/test"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.Settings(calendar_url=url)

    def test_updates_deletions_cache_restart_and_offline(self):
        with patch.object(self.client, "download_calendar", return_value=feed(SINGLE)):
            self.client.sync_calendar(self.settings)
        state = self.client.get_status(self.settings)
        self.assertEqual(state["state"], "ready")
        self.assertEqual(len(state["vacations"]), 1)
        self.assertNotIn("test-token", str(state))
        self.client._source = ""  # Simulate process restart and recover the stored feed.
        self.client._state = {}
        with patch.object(self.client, "download_calendar", side_effect=RuntimeError("test-token")):
            self.client.sync_calendar(self.settings)
        state = self.client.get_status(self.settings)
        self.assertTrue(state["stale"])
        self.assertEqual(len(state["vacations"]), 1)
        self.assertNotIn("test-token", str(state))
        with patch.object(self.client, "download_calendar", return_value=feed(SINGLE.replace("Herbsttour", "Umbenannt"))):
            self.client.sync_calendar(self.settings)
        self.assertEqual(self.client.get_status(self.settings)["vacations"][0]["name"], "Umbenannt")
        with patch.object(self.client, "download_calendar", return_value=feed("")):
            self.client.sync_calendar(self.settings)
        self.assertEqual(self.client.get_status(self.settings)["vacations"], [])

    def test_disable_and_source_change_hide_old_imports(self):
        with patch.object(self.client, "download_calendar", return_value=feed(SINGLE)):
            self.client.sync_calendar(self.settings)
        self.settings.calendar_enabled = False
        self.assertEqual(self.client.get_status(self.settings)["vacations"], [])
        self.settings.calendar_enabled = True
        self.settings.calendar_url += "-other"
        self.assertEqual(self.client.get_status(self.settings)["vacations"], [])

    def test_changed_source_during_download_discards_result(self):
        def download(_):
            self.client.settings_store.save_settings(self.Settings())
            return feed(SINGLE)
        with patch.object(self.client, "download_calendar", side_effect=download):
            self.client.sync_calendar(self.settings)
        self.assertEqual(self.client.get_status()["vacations"], [])
        self.assertIsNone(self.client.settings_store.load_calendar_cache(self.client.source_key(self.settings.calendar_url)))


if __name__ == "__main__":
    unittest.main()
