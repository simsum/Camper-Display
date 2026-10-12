import os
import sys
import tempfile
import unittest
from pathlib import Path


class SettingsStoreTests(unittest.TestCase):
    def test_defaults_and_healthcheck(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["CAMPERDISPLAY_DATA_DIR"] = temp_dir
            sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
            try:
                import settings_store

                settings = settings_store.load_settings()
                self.assertEqual(settings.display_width, 1480)
                self.assertEqual(settings.display_height, 320)
                self.assertTrue(settings_store.healthcheck())
                stand_enabled = {item.id for item in settings.screens if item.stand_enabled}
                drive_enabled = {item.id for item in settings.screens if item.drive_enabled}
                self.assertEqual(stand_enabled, {"clock_flip", "calendar", "weather", "sun"})
                self.assertEqual(drive_enabled, {"clock_flip", "map"})
                self.assertEqual(settings.brightness_stand, 40)
                self.assertEqual(settings.brightness_drive, 100)
                self.assertEqual(settings.config_version, 8)
                self.assertEqual(settings.panel_opacity_percent, 52)
                self.assertEqual(settings.panel_blur_pixels, 0)
                self.assertEqual(settings.vacations, [])
            finally:
                sys.path.pop(0)

    def test_legacy_screen_settings_migrate_to_mode_profiles(self):
        sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
        try:
            import settings_store
            from models import Settings

            legacy = {
                "screens": [
                    {"id": "clock", "enabled": True},
                    {"id": "trip", "enabled": True},
                    {"id": "map", "enabled": True},
                    {"id": "weather", "enabled": True},
                    {"id": "sun", "enabled": True},
                ],
                "brightness": 10,
                "screen_interval_seconds": 15,
            }
            settings = Settings.model_validate(settings_store._migrate(legacy))
            self.assertEqual(
                [screen.id for screen in settings.screens],
            ["clock_flip", "clock_blue", "clock_blank", "clock_panorama", "clock_led", "clock_linear", "clock_marble", "journey", "calendar", "weather", "map", "sun"],
            )
            profiles = {screen.id: screen for screen in settings.screens}
            self.assertTrue(profiles["clock_flip"].drive_enabled)
            self.assertNotIn("trip", profiles)
            self.assertNotIn("news", profiles)
            self.assertTrue(profiles["map"].drive_enabled)
            self.assertFalse(profiles["map"].stand_enabled)
            self.assertEqual(settings.brightness_stand, 40)
            self.assertEqual(settings.brightness_drive, 100)
            self.assertEqual(settings.config_version, 8)
            self.assertEqual(settings.panel_opacity_percent, 52)
            self.assertEqual(settings.panel_blur_pixels, 0)
            self.assertEqual(settings.vacations, [])
        finally:
            sys.path.pop(0)

    def test_vacation_dates_are_validated(self):
        sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
        try:
            from pydantic import ValidationError
            from models import VacationConfig

            vacation = VacationConfig(
                name="Herbsttour",
                start_date="2026-10-03",
                end_date="2026-10-12",
                destination="Südtirol",
            )
            self.assertEqual(vacation.name, "Herbsttour")
            with self.assertRaises(ValidationError):
                VacationConfig(
                    name="Ungültig",
                    start_date="2026-10-12",
                    end_date="2026-10-03",
                )
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
