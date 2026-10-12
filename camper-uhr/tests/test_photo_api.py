import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import photo_api
import photo_frame_service
import photo_store


class PhotoApiTests(unittest.TestCase):
    def test_same_origin_upload_list_file_and_delete(self):
        application = FastAPI()
        application.include_router(photo_api.router)
        with tempfile.TemporaryDirectory() as directory, patch.object(photo_store, "PHOTO_DIR", Path(directory)):
            client = TestClient(application)
            headers = {"Origin": "http://testserver", "Content-Type": "image/jpeg",
                       "X-Photo-Taken-At": "1700000000", "X-Photo-Latitude": "49.89", "X-Photo-Longitude": "10.89"}
            with patch.object(photo_api.weather_location, "resolve", return_value="Bamberg · Deutschland") as resolve:
                uploaded = client.post("/api/photos/upload", content=b"\xff\xd8\xff\xe0photo", headers=headers)
            self.assertEqual(uploaded.status_code, 201)
            self.assertEqual((uploaded.json()["taken_at"], uploaded.json()["place"]), (1700000000, "Bamberg · Deutschland"))
            resolve.assert_called_once_with(49.89, 10.89)
            photo_id = uploaded.json()["id"]
            self.assertEqual(client.get("/api/photos").json()["count"], 1)
            with patch.object(photo_api.settings_store, "load_settings", return_value=SimpleNamespace(photo_frame_manual_seconds=120)):
                shown = client.post("/api/photos/show", json={}, headers={"Origin": "http://testserver"})
            self.assertEqual(shown.status_code, 200)
            self.assertTrue(client.get("/api/photos/status").json()["active"])
            hidden = client.post("/api/photos/hide", json={}, headers={"Origin": "http://testserver"})
            self.assertEqual(hidden.json(), {"active": False, "remaining_seconds": 0})
            image = client.get(f"/api/photos/file/{photo_id}")
            self.assertEqual((image.status_code, image.headers["content-type"]), (200, "image/jpeg"))
            deleted = client.post(
                "/api/photos/delete",
                json={"id": photo_id},
                headers={"Origin": "http://testserver"},
            )
            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(client.get("/api/photos").json()["count"], 0)

    def test_cross_origin_upload_is_rejected(self):
        application = FastAPI()
        application.include_router(photo_api.router)
        with tempfile.TemporaryDirectory() as directory, patch.object(photo_store, "PHOTO_DIR", Path(directory)):
            response = TestClient(application).post(
                "/api/photos/upload",
                content=b"\xff\xd8\xff\xe0photo",
                headers={"Origin": "http://other", "Content-Type": "image/jpeg"},
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(photo_store.list_photos(), [])


if __name__ == "__main__":
    unittest.main()
