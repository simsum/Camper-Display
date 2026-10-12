"""Preload reports independently of the display; serve snapshots without network."""
from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import threading
import time
import traccar_client as client
import traccar_journey as journey
import traccar_route_data as routes

REFRESH_SECONDS=300
RETRY_SECONDS=60
MAX_ENTRIES=8


class JourneyCache:
    def __init__(self,builder=journey.journey,clock=time.monotonic):
        self.builder=builder;self.clock=clock
        self.lock=threading.RLock();self.wake=threading.Event();self.stop=threading.Event()
        self.entries=OrderedDict();self.queue=deque();self.identity=None;self.generation=0
        self.thread=None;self.next_prefetch=0

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():return self.stop
            self.stop.clear()
            self.thread=threading.Thread(target=self.run,name="traccar-preload",daemon=True)
            self.thread.start()
        return self.stop

    def identity_check(self,config):
        identity=routes.fingerprint(config)
        if identity!=self.identity:
            self.identity=identity;self.generation+=1
            self.entries.clear();self.queue.clear();routes.reset()

    def request(self,payload,config=None):
        force=isinstance(payload,dict) and payload.get("refresh") is True
        clean=journey.validate_payload(payload)
        config=config or client.load_private()
        key=(clean["mode"],clean.get("from"),clean.get("to"),datetime.now().date().isoformat() if clean["mode"]=="today" else None)
        with self.lock:
            self.identity_check(config)
            if not config["token"] or not config["device_id"]:
                return {"state":"unconfigured","ready":False,"loading":False,"data":None,"message":"Bitte zuerst Traccar-Zugang und Fahrzeug speichern."}
            entry=self.entries.get(key)
            if entry is None:
                while len(self.entries)>=MAX_ENTRIES:
                    self.entries.popitem(last=False)
                self.queue=deque(job for job in self.queue if self.entries.get(job[0]) is job[1])
                entry={"payload":clean,"data":None,"error":None,"loading":False,"checked":None,"version":0}
                self.entries[key]=entry
            self.entries.move_to_end(key)
            due=entry["checked"] is None or self.clock()-entry["checked"] >= (RETRY_SECONDS if entry["error"] else REFRESH_SECONDS)
            # Repeated clicks cannot hammer a server or start duplicate work.
            force=force and (entry["checked"] is None or self.clock()-entry["checked"]>=10)
            if (due or force) and not entry["loading"]:
                if force:routes.reset()
                entry["loading"]=True
                self.queue.append((key,entry,self.generation,dict(config)))
                self.wake.set()
            ready=entry["data"] is not None and entry["error"] is None
            return {"state":"ready" if ready else "error" if entry["error"] else "loading",
                    "ready":ready,"loading":entry["loading"],"version":entry["version"],
                    "data":deepcopy(entry["data"]) if ready else None,
                    "message":entry["error"] or ("Hintergrundaktualisierung läuft …" if entry["loading"] else "Daten vorbereitet.")}

    def work_one(self):
        with self.lock:
            if not self.queue:return False
            key,entry,generation,config=self.queue.popleft()
            if generation!=self.generation or self.entries.get(key) is not entry:return True
        data,error=None,None
        try:data=self.builder(entry["payload"],config=config)
        except client.TraccarError as exc:error=str(exc)
        except Exception:error="Fahrdaten konnten nicht vorbereitet werden."
        # Never publish an old account's in-flight result after credential change.
        try:current=client.load_private()
        except Exception:
            with self.lock:
                entry.update(loading=False,checked=self.clock(),error="Lokale Traccar-Einstellungen nicht lesbar.")
            return True
        with self.lock:
            self.identity_check(current)
            if generation!=self.generation or self.entries.get(key) is not entry:return True
            entry.update(loading=False,checked=self.clock(),error=error)
            if data is not None:entry["data"]=data;entry["version"]+=1
        return True

    def prefetch(self):
        config=client.load_private()
        self.request({"mode":"last"},config)
        self.request({"mode":"today"},config)
        now=datetime.now().astimezone()
        for item in journey.vacations():
            if item["start"]<=now.date().isoformat()<=item["end"]:
                start=datetime.fromisoformat(item["start"]).astimezone()
                end=(datetime.fromisoformat(item["end"])+timedelta(days=1)).astimezone()
                if end-start<=timedelta(days=93):
                    self.request({"mode":"vacation","from":journey.iso(start),"to":journey.iso(end)},config)
                break
        # Keep recently requested custom periods warm as well (bounded LRU).
        with self.lock:payloads=[dict(e["payload"]) for e in self.entries.values()]
        for payload in payloads:self.request(payload,config)

    def run(self):
        while not self.stop.is_set():
            if self.clock()>=self.next_prefetch:
                try:self.prefetch()
                except Exception:pass  # Never log secrets via exception repr.
                self.next_prefetch=self.clock()+30
            if not self.work_one():
                self.wake.wait(2);self.wake.clear()


service=JourneyCache()


def start_background_thread():
    return service.start()
