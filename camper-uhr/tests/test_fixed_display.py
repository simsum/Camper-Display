import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
from models import Settings
from pydantic import ValidationError
import settings_store

class FixedDisplayTests(unittest.TestCase):
    def test_defaults_and_old_client_geometry_are_fixed(self):
        for values in ({},{'display_width':1920,'display_height':1080},
                       {'display_width':None,'display_height':'invalid'}):
            settings=Settings.model_validate(values)
            self.assertEqual((settings.display_width,settings.display_height),(1480,320))
            with self.assertRaises(ValidationError):settings.display_width=999
    def test_migration_preserves_everything_else(self):
        old=Settings().model_dump(mode='json')
        old.update(display_width=800,display_height=600,brightness_stand=77)
        migrated=Settings.model_validate(settings_store._migrate(old)).model_dump(mode='json')
        expected={**old,'display_width':1480,'display_height':320}
        self.assertEqual(migrated,expected)
