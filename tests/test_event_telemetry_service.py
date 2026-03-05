import unittest

from anpr.event_telemetry.service import EventTelemetryService


class EventTelemetryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = EventTelemetryService(event_buffer_size=10)

    def test_subscribe_publish_and_poll(self) -> None:
        sub = self.service.subscribe()
        subscriber_id = sub["subscriber_id"]

        self.service.publish_event(channel_id="gate-1", plate="A123BC777", confidence=0.95)
        self.service.publish_event(channel_id="gate-1", plate="B321AC777", confidence=0.85)

        polled = self.service.poll_events(subscriber_id=subscriber_id, limit=10)
        self.assertEqual(len(polled["items"]), 2)
        self.assertEqual(polled["items"][0]["plate"], "A123BC777")

    def test_telemetry_and_alerts(self) -> None:
        self.service.update_channel_telemetry(
            channel_id="gate-2",
            fps=11,
            latency_ms=650,
            reconnects=4,
            timeouts=1,
            empty_frames=0,
        )

        alerts = self.service.alerts()["items"]
        kinds = {item["kind"] for item in alerts}
        self.assertIn("reconnect_warn", kinds)
        self.assertIn("latency_warn", kinds)

        health = self.service.health()
        self.assertEqual(health["channels_degraded"], 1)


if __name__ == "__main__":
    unittest.main()
