import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))
import settings_store
from models import Settings

CLOCKS = {'clock_flip', 'clock_blue', 'clock_blank', 'clock_panorama', 'clock_led', 'clock_linear', 'clock_marble'}

class ClockModuleTests(unittest.TestCase):
    def test_existing_v7_adds_marble_disabled_without_reordering(self):
        old = Settings().model_dump(mode='json')
        old['screens'] = [s for s in reversed(old['screens']) if s['id'] != 'clock_marble']
        order = [s['id'] for s in old['screens']]
        result = settings_store._migrate(old)
        self.assertEqual([s['id'] for s in result['screens'][:-1]], order)
        added = result['screens'][-1]
        self.assertEqual(added['id'], 'clock_marble')
        self.assertFalse(added['stand_enabled'] or added['drive_enabled'])
        self.assertEqual(result, settings_store._migrate(result))

    def test_old_selected_clock_preserves_position_durations_and_modes(self):
        for theme in ('flip', 'blue', 'blank', 'classic'):
            old = {'config_version': 6, 'theme': theme, 'screens': [
                {'id': 'weather', 'stand_enabled': True},
                {'id': 'clock', 'stand_enabled': False, 'drive_enabled': True,
                 'stand_duration_seconds': 17, 'drive_duration_seconds': 43},
                {'id': 'map', 'drive_enabled': True}],
                'calendar_enabled': True, 'calendar_url': 'https://p01-caldav.icloud.com/published/2/example',
                'theme_background_colors': {'blue': '#123456'}}
            original = deepcopy(old)
            result = Settings.model_validate(settings_store._migrate(old))
            self.assertEqual(old, original)
            expected = 'clock_' + (theme if theme != 'classic' else 'flip')
            self.assertEqual([s.id for s in result.screens[:3]], ['weather', expected, 'map'])
            clocks = {s.id: s for s in result.screens if s.id in CLOCKS}
            self.assertEqual(set(clocks), CLOCKS)
            self.assertFalse(clocks[expected].stand_enabled)
            self.assertTrue(clocks[expected].drive_enabled)
            self.assertEqual(clocks[expected].stand_duration_seconds, 17)
            self.assertEqual(clocks[expected].drive_duration_seconds, 43)
            for key, config in clocks.items():
                if key != expected:
                    self.assertFalse(config.stand_enabled or config.drive_enabled)
            self.assertEqual(result.calendar_url, old['calendar_url'])
            self.assertEqual(result.theme_background_colors, old['theme_background_colors'])

    def test_migration_is_idempotent_and_explicit_modules_win(self):
        raw = {'theme': 'blue', 'screens': [{'id': 'clock'}, {'id': 'clock_blue', 'stand_enabled': False, 'drive_enabled': False}]}
        result = settings_store._migrate(raw)
        self.assertEqual(result, settings_store._migrate(result))
        blues = [s for s in result['screens'] if s['id'] == 'clock_blue']
        self.assertEqual(len(blues), 1)
        self.assertFalse(blues[0]['stand_enabled'])

    def test_migration_persists_and_all_seven_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(settings_store, 'DB_PATH', Path(directory) / 'test.db'):
            old = Settings().model_dump(mode='json')
            old['config_version'] = 6
            old['theme'] = 'blank'
            old['screens'] = [{'id':'clock','stand_enabled':False,'drive_enabled':False,'stand_duration_seconds':21,'drive_duration_seconds':33}]
            conn = settings_store._connect()
            conn.execute('INSERT INTO settings (id, data) VALUES (1, ?)', (json.dumps(old),))
            conn.close()
            loaded = settings_store.load_settings()
            conn = settings_store._connect()
            persisted = json.loads(conn.execute('SELECT data FROM settings').fetchone()[0])
            conn.close()
            self.assertEqual(persisted['config_version'], 8)
            self.assertNotIn('clock', [s['id'] for s in persisted['screens']])
            self.assertFalse(any(s.stand_enabled or s.drive_enabled for s in loaded.screens if s.id in CLOCKS))
            for index, screen in enumerate(loaded.screens):
                if screen.id in CLOCKS:
                    screen.stand_enabled = True
                    screen.drive_enabled = index % 2 == 0
                    screen.stand_duration_seconds = index + 10
                    screen.drive_duration_seconds = index + 30
            loaded.screens.reverse()
            settings_store.save_settings(loaded)
            self.assertEqual(settings_store.load_settings(), loaded)
