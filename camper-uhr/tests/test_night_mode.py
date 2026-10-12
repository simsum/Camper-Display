import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'backend'))
from models import Settings
import display_scheduler as display
import display_backlight
import settings_store


class NightTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings()
        self.operating = {'mode':'stand', 'manual_wake_active':False}
        self.original = dict(display._state)

    def tearDown(self):
        display._state.clear()
        display._state.update(self.original)

    def policy(self, hour, minute=0, **kwargs):
        return display.display_policy(self.settings, self.operating, datetime(2026,9,11,hour,minute), **kwargs)

    def test_overnight_boundaries_and_brightness(self):
        for h,m,night in [(22,29,False),(22,30,True),(23,59,True),(0,0,True),(6,59,True),(7,0,False)]:
            result=self.policy(h,m)
            self.assertEqual(result['night_clock_active'],night)
            self.assertTrue(result['display_on'])
            self.assertEqual(result['brightness_percent'],5 if night else 40)

    def test_day_window_equal_time_disabled_and_drive(self):
        self.settings.display_off_time='13:00';self.settings.display_on_time='15:00'
        self.assertTrue(self.policy(14)['night_clock_active'])
        self.assertFalse(self.policy(15)['night_clock_active'])
        self.settings.display_on_time='13:00'
        self.assertFalse(self.policy(13)['night_clock_active'])
        self.settings=Settings(display_schedule_enabled=False)
        self.assertFalse(self.policy(23)['night_clock_active'])
        self.settings=Settings();self.operating['mode']='drive'
        self.assertFalse(self.policy(23)['night_clock_active'])
        self.assertEqual(self.policy(23)['brightness_percent'],100)

    def test_off_normal_wake_and_manual_priority(self):
        self.settings.night_behavior='off'
        self.assertFalse(self.policy(23)['display_on'])
        self.operating['manual_wake_active']=True
        self.assertTrue(self.policy(23)['display_on'])
        self.settings.night_behavior='clock'
        self.assertFalse(self.policy(23)['night_clock_active'])
        self.assertEqual(self.policy(23)['brightness_percent'],40)
        self.operating['manual_wake_active']=False
        self.settings.night_behavior='normal'
        self.assertTrue(self.policy(23)['display_on'])
        for behavior in ['off','clock','normal']:
            self.settings.night_behavior=behavior
            for hour in [12,23]:
                result=self.policy(hour,manual_off=True)
                self.assertFalse(result['display_on'] or result['night_clock_active'])

    def test_touch_respects_manual_off_and_uses_thirty_seconds(self):
        with patch.object(display.settings_store,'load_settings',return_value=self.settings), \
             patch.object(display.operating_state,'get_status',return_value=self.operating), \
             patch.object(display.operating_state,'start_manual_wake') as wake, \
             patch.object(display,'datetime') as clock:
            clock.now.return_value=datetime(2026,9,11,23)
            display._state.update(display_on=True,manual_off=False)
            self.assertTrue(display.wake_from_touch());wake.assert_called_once_with(30)
            wake.reset_mock();display._state['manual_off']=True
            self.assertFalse(display.wake_from_touch());wake.assert_not_called()
            display._state['manual_off']=False;self.settings.touch_wake_enabled=False
            self.assertFalse(display.wake_from_touch());wake.assert_not_called()

    def test_power_failure_does_not_claim_success(self):
        display._state['display_on']=False
        with patch.object(display.subprocess,'run') as run:
            run.return_value.returncode=1
            with self.assertRaises(RuntimeError):display._set_display_power(True)
        self.assertFalse(display._state['display_on'])

    def test_validation_and_legacy_migration(self):
        for field,value in [('display_off_time','25:00'),('display_on_time','12:70'),('brightness_night',0),('night_color','blue')]:
            with self.assertRaises(ValueError):Settings(**{field:value})
        old={'config_version':7,'display_off_time':'22:00','display_on_time':'06:00'}
        migrated=settings_store._migrate(old)
        self.assertEqual(migrated['night_behavior'],'off')
        self.assertEqual(migrated['display_off_time'],'22:00')
        self.assertEqual(settings_store._migrate(migrated),migrated)
        updated=Settings.model_validate(migrated);updated.night_behavior='clock'
        self.assertEqual(settings_store._migrate(updated.model_dump())['night_behavior'],'clock')

    def test_backlight_opt_in_and_fallback(self):
        with patch.dict('os.environ',{},clear=True):
            self.assertFalse(display_backlight.apply(5))
        with patch.dict('os.environ',{'CAMPERDISPLAY_BACKLIGHT_DIR':'/tmp/not-a-device'}):
            self.assertFalse(display_backlight.apply(5))
        with patch.dict('os.environ',{'CAMPERDISPLAY_BACKLIGHT_DIR':'/sys/class/backlight/test'}), \
             patch.object(Path,'read_text',return_value='1000'),patch.object(Path,'write_text') as write:
            display_backlight.invalidate()
            self.assertTrue(display_backlight.apply(5));write.assert_called_once_with('50')
            self.assertTrue(display_backlight.apply(5));self.assertEqual(write.call_count,1)
            display_backlight.invalidate();write.side_effect=PermissionError()
            self.assertFalse(display_backlight.apply(10))
