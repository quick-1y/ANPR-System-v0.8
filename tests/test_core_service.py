import unittest

from anpr.core.service import ANPRCoreService


class ANPRCoreServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ANPRCoreService()

    def test_create_update_and_lifecycle(self) -> None:
        created = self.service.create_channel(
            {
                "id": "gate-1",
                "name": "Въезд",
                "source": "rtsp://cam1",
            }
        )
        self.assertEqual(created["status"], "stopped")

        self.service.start_channel("gate-1")
        running = self.service.get_channel("gate-1")
        self.assertIsNotNone(running)
        assert running is not None
        self.assertEqual(running["status"], "running")

        self.service.update_roi("gate-1", {"enabled": True, "points": [{"x": 1, "y": 2}]})
        self.service.update_filters("gate-1", {"size_filter_enabled": True})
        self.service.update_lists("gate-1", {"allow": ["A123BC777"]})

        updated = self.service.get_channel("gate-1")
        assert updated is not None
        self.assertTrue(updated["roi"]["enabled"])
        self.assertTrue(updated["filters"]["size_filter_enabled"])
        self.assertEqual(updated["lists"]["allow"], ["A123BC777"])

    def test_metrics(self) -> None:
        self.service.create_channel({"id": "gate-2", "name": "Выезд", "source": "rtsp://cam2"})
        self.service.queue_job("gate-2")
        self.service.complete_job("gate-2", ok=True)
        self.service.queue_job("gate-2")
        self.service.complete_job("gate-2", ok=False)

        metrics = self.service.metrics()
        self.assertEqual(metrics["jobs_processed"], 1)
        self.assertEqual(metrics["jobs_failed"], 1)


if __name__ == "__main__":
    unittest.main()
