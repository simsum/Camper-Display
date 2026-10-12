import os
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from fastapi import FastAPI
from fastapi.testclient import TestClient
import photo_share


class PhotoShareTests(unittest.TestCase):
    def setUp(self):
        application = FastAPI()
        application.include_router(photo_share.router)
        self.client = TestClient(application, base_url="http://127.0.0.1:8080")
        self.env = patch.dict(os.environ, {"CAMPERDISPLAY_PUBLIC_URL": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_loopback_cannot_produce_a_misleading_phone_qr(self):
        self.assertIsNone(self.client.get("/api/photos/share").json()["url"])
        self.assertEqual(self.client.get("/api/photos/qr.svg").status_code, 503)

    def test_configured_lan_origin_is_encoded_locally(self):
        os.environ["CAMPERDISPLAY_PUBLIC_URL"] = "http://camperdisplay.local:8080/"
        url = "http://camperdisplay.local:8080/photos"
        self.assertEqual(self.client.get("/api/photos/share").json(), {"url": url})
        with patch.object(photo_share.qrcode, "make", wraps=photo_share.qrcode.make) as make:
            response = self.client.get("/api/photos/qr.svg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(make.call_args.args[0], url)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(ElementTree.fromstring(response.content).tag, "{http://www.w3.org/2000/svg}svg")

    def test_remote_browser_origin_and_ipv6_are_supported(self):
        self.assertEqual(self.client.get("http://camper.local:8080/api/photos/share").json()["url"],
                         "http://camper.local:8080/photos")
        os.environ["CAMPERDISPLAY_PUBLIC_URL"] = "http://[2001:db8::1]:8080"
        self.assertEqual(self.client.get("/api/photos/share").json()["url"],
                         "http://[2001:db8::1]:8080/photos")

    def test_invalid_or_secret_bearing_origins_are_never_shared(self):
        for origin in ["http://localhost:8080", "http://127.0.0.1:8080", "http://[::1]",
                       "http://0.0.0.0:8080", "http://user:secret@camper.local", "file:///tmp",
                       "https://camper.local/?token=secret", "https://camper.local/#secret",
                       "https://camper.local/subpath", "http://camper.local:99999"]:
            with self.subTest(origin=origin):
                os.environ["CAMPERDISPLAY_PUBLIC_URL"] = origin
                self.assertIsNone(self.client.get("/api/photos/share").json()["url"])
