import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
import arrival_provider as provider
import arrival_service as service
from models import Settings, ArrivalTestRequest


class ArrivalTests(unittest.TestCase):
    def setUp(self):
        self.settings=Settings(arrival_wait_seconds=300,display_schedule_enabled=False)
        self.gps={'connected':True,'speed_kmh':0,'latitude':45.76639,'longitude':10.493771}
        self.op={'mode':'stand'}

    def test_requires_drive_then_continuous_stop_once(self):
        e=service.ArrivalEngine()
        self.assertFalse(e.update(self.gps,self.op,self.settings,1000))
        self.gps['speed_kmh']=50;self.op['mode']='drive'
        e.update(self.gps,self.op,self.settings,1100)
        self.gps['speed_kmh']=0;self.op['mode']='stand'
        self.assertFalse(e.update(self.gps,self.op,self.settings,1200))
        self.assertFalse(e.update(self.gps,self.op,self.settings,1499))
        self.assertTrue(e.update(self.gps,self.op,self.settings,1500))
        self.assertFalse(e.update(self.gps,self.op,self.settings,1900))

    def test_gps_gap_movement_and_disable_reset_wait(self):
        e=service.ArrivalEngine();e.armed=True
        e.update(self.gps,self.op,self.settings,0)
        self.gps['connected']=False;e.update(self.gps,self.op,self.settings,299)
        self.gps['connected']=True;self.assertFalse(e.update(self.gps,self.op,self.settings,500))
        self.gps['speed_kmh']=5;e.update(self.gps,self.op,self.settings,799)
        self.gps['speed_kmh']=0;self.assertFalse(e.update(self.gps,self.op,self.settings,900))
        self.settings.arrival_enabled=False;e.update(self.gps,self.op,self.settings,1500)
        self.assertFalse(e.armed)

    def test_display_and_night_priority(self):
        self.assertFalse(service.blocked(self.settings,self.gps,self.op,{'display_on':True}))
        self.assertTrue(service.blocked(self.settings,self.gps,self.op,{'display_on':False}))
        self.settings.display_schedule_enabled=True
        with patch.object(service.display_scheduler,'_in_off_window',return_value=True):
            self.assertTrue(service.blocked(self.settings,self.gps,self.op,{'display_on':True}))

    def test_validation_and_no_arbitrary_urls(self):
        for key,value in [('arrival_wait_seconds',0),('arrival_wait_seconds',3601),('arrival_duration_seconds',181)]:
            with self.assertRaises(ValueError):Settings(**{key:value})
        for url in ['http://de.wikipedia.org/x','https://127.0.0.1/','https://de.wikipedia.org.evil.test/','https://user:pass@de.wikipedia.org/x']:
            self.assertFalse(provider.safe_url(url))
        self.assertTrue(provider.safe_url('https://thumb.wikimedia.org/example.jpg'))
        self.assertEqual(provider.clean('<b>A</b> &amp; B'),'A & B')

    def test_offline_is_partial_not_exception(self):
        with patch.object(provider,'get_json',side_effect=OSError()):
            data=provider.lookup(45.7,10.4,412)
        self.assertEqual(data['altitude_m'],412)
        self.assertEqual(data['place'],'Eurem Standort')
        self.assertNotIn('_image',data)
        self.assertIsNone(data['sunset'])

    def test_mismatched_wikidata_cannot_show_wrong_article(self):
        place={'name':'Anfo','extratags':{'wikidata':'Q103420'}}
        entity={'entities':{'Q103420':{'sitelinks':{'dewiki':{'title':'Anfo'}}}}}
        page={'query':{'pages':{'1':{'extract':'WRONG','pageprops':{'wikibase_item':'Q999'}}}}}
        with patch.object(provider,'get_json',side_effect=[place,entity,page,{}]):
            result=provider.lookup(45.7,10.4)
        self.assertEqual(result['extract'],'')
        self.assertEqual(result['wiki_url'],'')

    def test_image_requires_known_license_and_real_raster(self):
        for filename in ['map.svg','Anfo-Stemma.png','Flag.jpg']:
            self.assertEqual(provider.photo(filename),{})
        info={'thumburl':'https://thumb.wikimedia.org/x.jpg','thumbwidth':1280,'thumbheight':800,
              'descriptionurl':'https://commons.wikimedia.org/wiki/File:X.jpg',
              'extmetadata':{'LicenseShortName':{'value':'CC BY-SA 4.0'},'Artist':{'value':'<b>Author</b>'},
                             'LicenseUrl':{'value':'https://creativecommons.org/licenses/by-sa/4.0/'}}}
        payload={'query':{'pages':{'1':{'imageinfo':[info]}}}}
        with patch.object(provider,'get_json',return_value=payload),patch.object(provider,'read_url',return_value=b'\xff\xd8\xffok'):
            self.assertIn('Author',provider.photo('Ort.jpg')['image_credit'])
            info['extmetadata']['LicenseShortName']['value']='All rights reserved'
            self.assertEqual(provider.photo('Ort.jpg'),{})

    def test_request_throttle_and_image_id(self):
        with patch.object(service,'_state',{'loading':False,'data':{},'event_id':'test'}),patch.object(service,'_test_pending',False),patch.object(service,'_last_test',-1000),patch.object(service,'_image',b'abc'):
            self.assertTrue(service.request_test(' Bamberg '));self.assertFalse(service.request_test('Anfo'))
            self.assertEqual(service._test_pending,'Bamberg')
            self.assertIsNone(service.image_for('wrong'))
            self.assertEqual(service.image_for('test')[0],b'abc')

    def test_seconds_migration_and_exact_threshold(self):
        import settings_store
        old={'arrival_wait_minutes':5,'brightness_stand':77}
        migrated=Settings.model_validate(settings_store._migrate(old))
        self.assertEqual(migrated.arrival_wait_seconds,300)
        self.assertEqual(migrated.brightness_stand,77)
        self.assertNotIn('arrival_wait_minutes',migrated.model_dump())
        self.assertEqual(old['arrival_wait_minutes'],5)
        self.assertEqual(Settings(arrival_wait_minutes=5,arrival_wait_seconds=37).arrival_wait_seconds,37)
        self.settings.arrival_wait_seconds=37
        engine=service.ArrivalEngine();engine.armed=True
        self.assertFalse(engine.update(self.gps,self.op,self.settings,10))
        self.assertFalse(engine.update(self.gps,self.op,self.settings,46))
        self.assertTrue(engine.update(self.gps,self.op,self.settings,47))

    def test_test_place_validation(self):
        self.assertEqual(ArrivalTestRequest(place_name=' Bamberg ').place_name,'Bamberg')
        for value in ('', '   ', 'x'*121):
            with self.assertRaises(ValueError):ArrivalTestRequest(place_name=value)
            with self.assertRaises(ValueError):service.request_test(value)

    def test_worker_resolves_entered_city_without_mutating_gps(self):
        from contextlib import ExitStack
        class Stop:
            done=False
            def is_set(self):return self.done
            def wait(self,_):self.done=True
        for coords in ((49.9,10.9),None):
            state={'event_id':None,'expires_at':0,'data':{},'loading':True,'message':''}
            with ExitStack() as stack:
                for name,value in (('_state',state),('_test_pending','Bamberg'),('_image',b'')):
                    stack.enter_context(patch.object(service,name,value))
                stack.enter_context(patch.object(service.settings_store,'load_settings',return_value=self.settings))
                stack.enter_context(patch.object(service.gps_client,'get_status',return_value=self.gps))
                stack.enter_context(patch.object(service.operating_state,'get_status',return_value=self.op))
                stack.enter_context(patch.object(service.display_scheduler,'get_status',return_value={'display_on':True}))
                geocode=stack.enter_context(patch.object(service.geocode_client,'geocode',return_value=coords))
                lookup=stack.enter_context(patch.object(service.arrival_provider,'lookup',return_value={'place':'Bamberg'}))
                mutate=stack.enter_context(patch.object(service.gps_client,'set_simulated_fix'))
                service._run(Stop())
                geocode.assert_called_once_with('Bamberg');mutate.assert_not_called()
                self.assertFalse(state['loading'])
                if coords:
                    lookup.assert_called_once_with(*coords,None)
                    self.assertIs(state['data']['test'],True)
                    self.assertEqual(state['message'],'Ankunftstest bereit')
                else:
                    lookup.assert_not_called()
                    self.assertIsNone(state['event_id'])
                    self.assertIn('nicht gefunden',state['message'])
