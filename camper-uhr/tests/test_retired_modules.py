import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))
from models import Settings
import settings_store

class RetiredModuleTests(unittest.TestCase):
    def test_migration_preserves_survivors_and_rejects_old_form_entries(self):
        raw = Settings().model_dump(mode='json')
        kept = list(reversed(raw['screens']))
        raw['screens'] = [dict(id='news', stand_enabled=True), *kept, dict(id='trip', drive_enabled=True)]
        migrated = settings_store._migrate(raw)
        self.assertEqual(migrated['screens'], kept)
        self.assertEqual(migrated, settings_store._migrate(migrated))
        self.assertEqual(Settings.model_validate(raw).model_dump(mode='json')['screens'], kept)
        self.assertEqual(raw['screens'][0]['id'], 'news')  # Caller input remains intact.
