import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import photo_store


JPEG = b"\xff\xd8\xff\xe0" + b"draft-photo"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (600).to_bytes(4, "big") + (800).to_bytes(4, "big") + b"draft-photo"
JPEG_WITH_SIZE = b"\xff\xd8\xff\xc0\x00\x11\x08\x01\x40\x05\xc8" + b"\x00" * 10


class PhotoStoreTests(unittest.TestCase):
    def test_add_list_resolve_and_delete(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(photo_store, "PHOTO_DIR", Path(directory)):
            first = photo_store.add_photo(JPEG, "image/jpeg", {"taken_at": 1_700_000_000, "place": "Bamberg · Deutschland"})
            second = photo_store.add_photo(PNG, "image/png")
            listed = photo_store.list_photos()
            self.assertEqual({item["id"] for item in listed}, {first["id"], second["id"]})
            stored_first = next(item for item in listed if item["id"] == first["id"])
            self.assertEqual((stored_first["taken_at"], stored_first["place"]), (1_700_000_000, "Bamberg · Deutschland"))
            self.assertTrue(photo_store.photo_path(first["id"]).is_file())
            self.assertEqual((second["width"], second["height"], second["aspect_ratio"]), (600, 800, 0.75))
            self.assertTrue((Path(directory) / f'{first["id"]}.json').is_file())
            self.assertIsNone(photo_store.photo_path("../settings.db"))
            self.assertTrue(photo_store.delete_photo(first["id"]))
            self.assertFalse((Path(directory) / f'{first["id"]}.json').exists())
            self.assertFalse(photo_store.delete_photo(first["id"]))

    def test_reads_jpeg_dimensions(self):
        self.assertEqual(photo_store._image_dimensions(JPEG_WITH_SIZE), (1480, 320))
        self.assertEqual(photo_store._dimension_fields(JPEG_WITH_SIZE)["aspect_ratio"], 4.625)

    def test_rejects_type_signature_and_size_mismatch(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(photo_store, "PHOTO_DIR", Path(directory)):
            for data, mime in [(JPEG, "image/gif"), (b"not-jpeg", "image/jpeg"), (b"", "image/png")]:
                with self.assertRaises(ValueError):
                    photo_store.add_photo(data, mime)
            with patch.object(photo_store, "MAX_FILE_BYTES", 4):
                with self.assertRaises(ValueError):
                    photo_store.add_photo(JPEG, "image/jpeg")


if __name__ == "__main__":
    unittest.main()
