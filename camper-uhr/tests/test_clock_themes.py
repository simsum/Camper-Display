import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
from models import Settings
from settings_store import _migrate
from pydantic import ValidationError


class ClockThemeTests(unittest.TestCase):
    def test_only_three_themes_are_accepted(self):
        self.assertEqual(Settings().theme, "flip")
        for theme in ("flip", "blue", "blank"):
            self.assertEqual(Settings(theme=theme).theme, theme)
        for theme in ("classic", "blue2", "blue_pets", "css-drawn", "unknown"):
            with self.assertRaises(ValidationError):
                Settings(theme=theme)

    def test_retired_themes_migrate_without_losing_preferences(self):
        for theme in ("classic", "blue2", "blue_pets", "css-drawn"):
            settings = Settings.model_validate(_migrate({
                "config_version": 6, "theme": theme, "brightness_stand": 80,
                "theme_background_colors": {"blue": "#123456"},
                "vacations": [{"name": "Herbsttour", "start_date": "2026-10-01", "end_date": "2026-10-10"}],
            }))
            self.assertEqual(settings.theme, "flip")
            self.assertEqual(settings.brightness_stand, 80)
            self.assertEqual(settings.theme_background_colors["blue"], "#123456")
            self.assertEqual(settings.vacations[0].name, "Herbsttour")

    def test_kept_themes_do_not_change(self):
        for theme in ("flip", "blue", "blank"):
            self.assertEqual(Settings.model_validate(_migrate({"theme": theme})).theme, theme)
