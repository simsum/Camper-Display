"""One lookup per qualified arrival. All network work stays off API threads."""
import math
import threading
import time
import uuid
from datetime import datetime

import arrival_provider
import display_scheduler
import gps_client
import geocode_client
import operating_state
import settings_store


class ArrivalEngine:
    def __init__(self):
        self.armed=False
        self.stopped_at=None

    def update(self,gps,operating,settings,now):
        speed=gps.get('speed_kmh')
        valid=(gps.get('connected') and isinstance(speed,(float,int)) and math.isfinite(speed)
               and speed>=0 and all(isinstance(gps.get(k),(float,int)) and math.isfinite(gps[k]) for k in ('latitude','longitude')))
        if not settings.arrival_enabled:
            self.armed=False;self.stopped_at=None;return False
        if not valid:
            self.stopped_at=None;return False
        if operating['mode']=='drive' and speed>=settings.drive_enter_speed_kmh:
            self.armed=True
        if speed>=settings.stand_enter_speed_kmh:
            self.stopped_at=None;return False
        if not self.armed:return False
        if self.stopped_at is None:self.stopped_at=now
        if operating['mode']=='stand' and now-self.stopped_at>=settings.arrival_wait_seconds:
            self.armed=False;self.stopped_at=None;return True
        return False


def blocked(settings,gps,operating,display):
    night=settings.display_schedule_enabled and display_scheduler._in_off_window(
        datetime.now(),settings.display_off_time,settings.display_on_time)
    valid=all(isinstance(gps.get(k),(float,int)) and math.isfinite(gps[k]) for k in ('speed_kmh','latitude','longitude'))
    return (not valid or night or not display['display_on'] or display.get('manual_off')
            or operating['mode']!='stand' or not gps.get('connected')
            or gps.get('speed_kmh') is None or gps['speed_kmh']>=settings.stand_enter_speed_kmh)


_lock=threading.Lock()
_state={'event_id':None,'expires_at':0,'data':{},'loading':False,'message':''}
_image=b''
_test_pending=None
_last_test=-1000.0


def get_status():
    with _lock:
        result={**_state,'data':dict(_state['data'])}
    settings=settings_store.load_settings()
    display=display_scheduler.get_status()
    result['suppressed']=(not display['display_on'] or display.get('manual_off',False)
        or operating_state.get_status()['mode']=='drive'
        or (settings.display_schedule_enabled and display_scheduler._in_off_window(
            datetime.now(),settings.display_off_time,settings.display_on_time)))
    return result


def image_for(event_id):
    with _lock:
        if event_id!=_state['event_id'] or not _image:return None
        return _image,_state['data'].get('image_mime','image/jpeg')


def request_test(place_name):
    global _test_pending,_last_test
    if not isinstance(place_name,str) or not 1 <= len(place_name.strip()) <= 120:
        raise ValueError('Bitte einen gültigen Ort für den Ankunftstest eingeben.')
    with _lock:
        now=time.monotonic()
        if _state['loading'] or _test_pending or now-_last_test<60:return False
        _test_pending=place_name.strip();_last_test=now
        _state.update(loading=True,message='Simulationsort wird geladen …')
        return True


def resolve_test_place(place_name):
    # Reuse the GPS simulation's geocoder, but never set a simulated GPS fix.
    coords=geocode_client.geocode(place_name)
    if coords is None:
        raise LookupError('Simulationsort nicht gefunden oder Ortsuche nicht erreichbar.')
    return coords


def _publish(data,duration,test=False):
    global _image
    event_id=uuid.uuid4().hex
    image=data.pop('_image',b'')
    with _lock:
        _image=image
        data['image_url']=f'/api/arrival/image/{event_id}' if image else ''
        data['test']=test
        _state.update(event_id=event_id,expires_at=time.time()+duration,data=data,loading=False,
                      message='Ankunftstest bereit' if test else 'Ankunft bereit')


def _run(stop):
    global _test_pending
    engine=ArrivalEngine()
    while not stop.is_set():
        settings=settings_store.load_settings();gps=gps_client.get_status();operating=operating_state.get_status()
        with _lock:
            test=_test_pending;_test_pending=None
        triggered=engine.update(gps,operating,settings,time.monotonic())
        if test or triggered:
            display=display_scheduler.get_status()
            # A deliberate test does not require GPS or a preceding drive; never wake a dark screen.
            suppressed=(settings.display_schedule_enabled and display_scheduler._in_off_window(datetime.now(),settings.display_off_time,settings.display_on_time)) or not display['display_on'] or operating['mode']=='drive'
            if (test and suppressed) or (not test and blocked(settings,gps,operating,display)):
                with _lock:_state.update(loading=False,message='Ankunft wegen Nachtmodus/Displayzustand übersprungen')
            else:
                with _lock:_state.update(loading=True,message='Ortsinformationen werden geladen …')
                try:
                    lat,lon=resolve_test_place(test) if test else (gps['latitude'],gps['longitude'])
                    data=arrival_provider.lookup(lat,lon,None if test else gps.get('altitude_m'))
                    if stop.is_set():return
                    fresh=settings_store.load_settings();current=gps_client.get_status();op=operating_state.get_status();ds=display_scheduler.get_status()
                    suppress_now=(fresh.display_schedule_enabled and display_scheduler._in_off_window(datetime.now(),fresh.display_off_time,fresh.display_on_time)) or not ds['display_on'] or op['mode']=='drive'
                    same_place=all(isinstance(current.get(k),(int,float)) for k in ('latitude','longitude')) and (
                        abs(current['latitude']-lat)+abs(current['longitude']-lon))<0.015
                    if (test and not suppress_now) or (not test and same_place and fresh.arrival_enabled and not blocked(fresh,current,op,ds)):
                        _publish(data,fresh.arrival_duration_seconds,bool(test))
                    else:
                        with _lock:_state.update(loading=False,message='Ankunft inzwischen übersprungen')
                except LookupError:
                    with _lock:_state.update(loading=False,message='Simulationsort nicht gefunden oder Ortsuche nicht erreichbar. Bitte Ort prüfen.')
                except Exception:
                    with _lock:_state.update(loading=False,message='Ankunftsdaten nicht verfügbar')
        stop.wait(1)


def start_background_thread():
    stop=threading.Event()
    threading.Thread(target=_run,args=(stop,),daemon=True).start()
    return stop
