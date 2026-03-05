import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from anpr.data_layer.service import DataLayerService


class DataLayerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        base = Path(self.tmp_dir.name)
        self.db_path = str(base / "anpr.db")
        self.media_root = str(base / "media")
        self.service = DataLayerService(db_path=self.db_path, media_root=self.media_root)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_retention_and_export(self) -> None:
        old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        self.service.insert_demo_event("gate-1", "A123BC777", timestamp=old_ts)
        self.service.insert_demo_event("gate-1", "B456CE777")

        retention = self.service.retention_delete_older_than_days(5)
        self.assertEqual(retention["deleted_events"], 1)

        json_path = Path(self.tmp_dir.name) / "exports" / "events.json"
        csv_path = Path(self.tmp_dir.name) / "exports" / "events.csv"
        self.service.export_events_json(str(json_path), limit=10)
        self.service.export_events_csv(str(csv_path), limit=10)

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(payload), 1)
        self.assertTrue(csv_path.exists())

    def test_media_cleanup(self) -> None:
        media = Path(self.media_root)
        media.mkdir(parents=True, exist_ok=True)
        empty = media / "empty.jpg"
        non_empty = media / "ok.jpg"
        empty.write_bytes(b"")
        non_empty.write_bytes(b"x")

        result = self.service.media_rotation_cleanup()
        self.assertEqual(result["removed_files"], 1)
        self.assertFalse(empty.exists())
        self.assertTrue(non_empty.exists())


if __name__ == "__main__":
    unittest.main()
