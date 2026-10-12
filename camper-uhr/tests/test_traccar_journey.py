import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/"backend"))
import traccar_journey as journey
import traccar_client as client
import traccar_route_data as routes
import traccar_motion as motion
from traccar_cache import JourneyCache
CONFIG={"token":"fake", "device_id":4,"api_url":"http://test/api"}


def outing():
    p=[(i*60,50,10+i*.001,10 if i not in (0,10) else 0,i*100) for i in range(11)]
    p.extend([(2400,50,10.01,0,1000),(4200,50,10.01,0,1000),(6000,50,10.01,0,1000)])
    p.extend([(6000+i*60,50,10.01-i*.001,10 if i<10 else 0,1000+i*100) for i in range(1,11)])
    p.extend([(10200,50,10,0,2000),(13800,50,10,0,2000)])
    return p


class MotionTests(unittest.TestCase):
    def test_roundtrip_and_sparse_90_min_pause(self):
        r=motion.analyze(outing())
        self.assertEqual(r["drive_seconds"],1200);self.assertEqual(r["pause_seconds"],5400)
        self.assertEqual(r["trip_count"],2);self.assertEqual(r["to"],6600)
        self.assertEqual(r["distance_km"],2);self.assertTrue(r["stops"][0]["estimated"])

    def test_unknown_gap_is_not_driving_or_pause(self):
        p=[(0,50,10,10,0),(60,50,10.001,10,100),(3660,51,11,10,200),(3720,51,11.001,10,300)]
        r=motion.analyze(p)
        self.assertEqual(r["unknown_seconds"],3600);self.assertEqual(r["drive_seconds"],120)
        self.assertEqual(r["pause_seconds"],0);self.assertEqual(len(r["segments"]),2)

    def test_no_movement_no_fictional_trip(self):
        self.assertTrue(motion.analyze([(0,50,10,0,0),(3600,50,10,0,0)])["empty"])

    def test_20k_points_preserves_endpoints_and_statistics(self):
        p=[(i,50,10+i*.00001,10,i) for i in range(20000)]
        r=motion.analyze(p);s=motion.simplify(r["segments"])
        self.assertLessEqual(sum(map(len,s)),1200)
        self.assertEqual(s[0][0],[50,10]);self.assertEqual(s[-1][-1],[50,10.19999])
        self.assertEqual(r["drive_seconds"],19999);self.assertEqual(r["distance_km"],20)

    def test_corner_preserved_and_invalid_points_filtered(self):
        self.assertEqual(motion.simplify([[[0,0],[0,.5],[0,1],[1,1]]],3),[[[0,0],[0,1],[1,1]]])
        self.assertEqual(motion.compact([{"valid":False},{"valid":True,"latitude":999,"longitude":0,"fixTime":"2026-01-01T00:00:00Z"}]),[])


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,11,12,tzinfo=timezone.utc)
        p=patch.object(client,"load_private",return_value=CONFIG);p.start();self.addCleanup(p.stop)
        p=patch.object(client,"fetch_json",return_value=[{"id":4,"name":"Camper"}]);p.start();self.addCleanup(p.stop)

    def test_last_window_24h_before_arrival_not_now(self):
        shift=datetime(2026,9,7,12,tzinfo=timezone.utc).timestamp()
        p=[(t+shift,*rest) for t,*rest in outing()]
        with patch.object(routes,"day",return_value=p),patch.object(routes,"window",return_value=p) as window:
            r=journey.journey({"mode":"last"},self.now)
        end=journey.moment(r["window_to"]);start=journey.moment(r["window_from"])
        self.assertEqual(end-start,timedelta(hours=24));self.assertEqual(end.timestamp(),shift+6600)
        self.assertEqual(r["trip_count"],2);self.assertEqual(r["pause_seconds"],5400)
        self.assertEqual(window.call_args.args[1:3],(start,end))

    def test_empty_search_bounded(self):
        with patch.object(routes,"day",return_value=[]) as day:
            self.assertTrue(journey.journey({"mode":"last"},self.now)["empty"])
            self.assertEqual(day.call_count,31)

    def test_period_validation(self):
        for p in [{"mode":"wrong"},{"mode":"vacation","from":"2026-09-11","to":"2026-09-12"},{"mode":"vacation","from":"2025-01-01T00:00:00Z","to":"2026-01-01T00:00:00Z"}]:
            with self.assertRaises(client.TraccarError):journey.validate_payload(p)


class CacheTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(client,"load_private",return_value=dict(CONFIG));self.mock=p.start();self.addCleanup(p.stop)
        self.time=0;self.calls=0
        def build(payload,config):
            self.calls+=1
            return {"mode":payload["mode"],"empty":False,"segments":[[[50,10]]],"loaded_at":str(self.calls)}
        self.cache=JourneyCache(build,lambda:self.time)

    def test_nonblocking_deduplicated_snapshot(self):
        for _ in range(20):self.assertEqual(self.cache.request({"mode":"last"})["state"],"loading")
        self.assertEqual(self.calls,0);self.assertEqual(len(self.cache.queue),1)
        self.cache.work_one();r=self.cache.request({"mode":"last"})
        self.assertTrue(r["ready"]);self.assertFalse(r["loading"]);self.assertEqual(self.calls,1)
        r["data"]["segments"].clear();self.assertTrue(self.cache.request({"mode":"last"})["data"]["segments"])

    def test_warm_switch_and_old_data_during_refresh(self):
        for mode in ("last","today"):
            self.cache.request({"mode":mode});self.cache.work_one()
        self.assertTrue(self.cache.request({"mode":"last"})["ready"]);self.assertEqual(self.calls,2)
        self.time=301;r=self.cache.request({"mode":"last"})
        self.assertTrue(r["ready"]);self.assertTrue(r["loading"]);self.assertEqual(r["data"]["loaded_at"],"1")

    def test_error_hides_old_result_and_backs_off(self):
        self.cache.request({"mode":"last"});self.cache.work_one();self.time=301
        def fail(*_,**__):raise client.TraccarError("Server nicht erreichbar")
        self.cache.builder=fail;self.cache.request({"mode":"last"});self.cache.work_one()
        self.assertFalse(self.cache.request({"mode":"last"})["ready"])
        self.assertFalse(self.cache.request({"mode":"last"})["loading"])
        self.time=362;self.assertTrue(self.cache.request({"mode":"last"})["loading"])

    def test_credential_change_discards_inflight_result(self):
        self.cache.request({"mode":"last"})
        def build(payload,config):
            self.mock.return_value={**CONFIG,"token":"replacement"}
            return {"private":"old-account"}
        self.cache.builder=build;self.cache.work_one();self.assertFalse(self.cache.entries)
        self.assertIsNone(self.cache.request({"mode":"last"})["data"])

    def test_bounded_selection_cache(self):
        for i in range(1,15):self.cache.request({"mode":"vacation","from":f"2026-09-{i:02}T00:00:00Z","to":f"2026-09-{i+1:02}T00:00:00Z"})
        self.assertLessEqual(len(self.cache.entries),8)
        self.assertLessEqual(len(self.cache.queue),8)


if __name__=="__main__":unittest.main()
