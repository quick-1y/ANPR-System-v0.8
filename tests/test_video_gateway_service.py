import unittest

from anpr.video_gateway.service import VideoGatewayService


class VideoGatewayServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = VideoGatewayService()

    def test_stream_lifecycle_and_profiles(self) -> None:
        created = self.service.create_stream("cam-1", "rtsp://camera/1", "medium")
        self.assertEqual(created["selected_profile"], "medium")

        focused = self.service.pick_profile_for_tile("cam-1", "focused")
        self.assertEqual(focused["selected_profile"], "high")

        bg = self.service.pick_profile_for_tile("cam-1", "background")
        self.assertEqual(bg["selected_profile"], "low")

    def test_sessions_and_metrics(self) -> None:
        self.service.create_stream("cam-2", "rtsp://camera/2")
        webrtc = self.service.open_session("cam-2", transport="webrtc")
        hls = self.service.open_session("cam-2", transport="hls", profile="low")

        self.assertIn("webrtc://gateway/cam-2", webrtc["url"])
        self.assertIn("/hls/cam-2/low/index.m3u8", hls["url"])

        metrics = self.service.metrics()
        self.assertEqual(metrics["sessions_total"], 2)
        self.assertEqual(metrics["sessions_webrtc"], 1)
        self.assertEqual(metrics["sessions_hls"], 1)


if __name__ == "__main__":
    unittest.main()
