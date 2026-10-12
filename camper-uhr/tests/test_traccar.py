import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
import traccar_client as client


class TraccarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = patch.object(client, "DB_PATH", Path(self.temp.name) / "private.db")
        self.db.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.db.stop)
        self.payload = {"api_url": "https://traccar.example.org/api", "token": "test-secret-only", "device_id": 12}

    def test_new_installation_has_no_preconfigured_private_server(self):
        self.assertEqual(client.public_config(), {"api_url": "", "device_id": None, "token_saved": False})

    def test_urls(self):
        self.assertEqual(client.normalize_url("http://traccar.example.org:8082/"), "http://traccar.example.org:8082/api")
        self.assertEqual(client.normalize_url("https://example.org/traccar/api/"), "https://example.org/traccar/api")
        for bad in ["ftp://example.org", "http://u:p@host/api", "http://host/api?token=secret", "http://host/#x", "http://host:99999", "http://host/../api", "http://host/%2e/api", "http://host/\napi"]:
            with self.assertRaises(client.TraccarError):
                client.normalize_url(bad)

    def test_atomic_storage_no_secret_response_preserve_replace_clear(self):
        public = client.save(self.payload)
        self.assertTrue(public["token_saved"])
        self.assertNotIn("test-secret-only", json.dumps(public))
        client.save({"api_url": self.payload["api_url"], "token": "", "device_id": 13})
        self.assertEqual(client.load_private()["token"], "test-secret-only")
        client.save({"token": "replacement", "device_id": 13})
        self.assertEqual(client.load_private()["token"], "replacement")
        client.save({"clear_token": True})
        self.assertFalse(client.public_config()["token_saved"])

    def test_changed_url_never_receives_old_secret(self):
        client.save(self.payload)
        with patch.object(client, "fetch_json") as request:
            with self.assertRaises(client.TraccarError):
                client.test_connection({"api_url": "https://different.example/api"})
            request.assert_not_called()
        client.save({"api_url": "https://different.example/api"})
        self.assertFalse(client.public_config()["token_saved"])

    def test_bearer_probe_does_not_require_browser_session(self):
        def upstream(config, endpoint):
            if endpoint == "/session":
                raise client.TraccarError("Traccar antwortet mit HTTP 404.")
            if endpoint == "/devices":
                return [{"id": 12, "name": "Camper"}]
            if endpoint == "/positions?deviceId=12":
                return []
            self.fail("Unexpected endpoint")
        with patch.object(client, "fetch_json", side_effect=upstream) as request:
            result = client.test_connection(self.payload)
        self.assertTrue(result["ok"])
        self.assertFalse(result["permissions_verified"])
        self.assertEqual([call.args[1] for call in request.call_args_list], ["/devices", "/positions?deviceId=12"])

    def test_probe_units_privacy_and_does_not_save(self):
        position = {"deviceId": 12, "valid": True, "fixTime": datetime.now(timezone.utc).isoformat(), "speed": 10, "altitude": 430, "latitude": 1, "attributes": {"private": "hidden"}}
        responses = [[{"id": 12, "name": "Camper", "uniqueId": "private-tracker"}], [position]]
        with patch.object(client, "fetch_json", side_effect=responses):
            result = client.test_connection(self.payload)
        self.assertEqual(result["position"]["speed_kmh"], 18.5)
        self.assertFalse(result["position"]["stale"])
        self.assertNotIn("private-tracker", json.dumps(result))
        self.assertNotIn("latitude", json.dumps(result))
        self.assertFalse(client.public_config()["token_saved"])

    def test_old_position_and_missing_vehicle(self):
        with patch.object(client, "fetch_json", side_effect=[[{"id": 12, "name": "Camper"}], [{"deviceId": 12, "valid": True, "fixTime": "2020-01-01T00:00:00Z"}]]):
            self.assertTrue(client.test_connection(self.payload)["position"]["stale"])
        with patch.object(client, "fetch_json", side_effect=[[]]):
            with self.assertRaises(client.TraccarError):
                client.test_connection(self.payload)

    def test_safe_errors_and_header_only_auth(self):
        for status in [401, 403, 302, 500]:
            with patch.object(client, "build_opener") as factory:
                factory.return_value.open.side_effect = HTTPError("secret-url", status, "private error", {}, None)
                with self.assertRaises(client.TraccarError) as caught:
                    client.fetch_json(self.payload, "/devices")
                self.assertNotIn("secret", str(caught.exception))
                request = factory.return_value.open.call_args.args[0]
                self.assertNotIn("test-secret", request.full_url)
                self.assertEqual(request.get_header("Authorization"), "Bearer test-secret-only")
        self.assertIsNone(client.NoRedirect().redirect_request(None, None, 302, None, None, "http://elsewhere"))

    def test_invalid_token_does_not_echo(self):
        with self.assertRaises(client.TraccarError) as caught:
            client.save({"api_url": self.payload["api_url"], "token": "SECRET\r\nInjected: value"})
        self.assertNotIn("SECRET", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
