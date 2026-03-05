import unittest

from anpr.web_ui.server import build_runtime_config


class WebUIServiceTests(unittest.TestCase):
    def test_build_runtime_config_normalizes_trailing_slashes(self) -> None:
        config = build_runtime_config(
            core_base_url="http://127.0.0.1:8080/api/v1/",
            video_base_url="http://127.0.0.1:8090/api/v1///",
            events_base_url="http://127.0.0.1:8100/api/v1/",
        )

        self.assertEqual(config["core_base_url"], "http://127.0.0.1:8080/api/v1")
        self.assertEqual(config["video_base_url"], "http://127.0.0.1:8090/api/v1")
        self.assertEqual(config["events_base_url"], "http://127.0.0.1:8100/api/v1")


if __name__ == "__main__":
    unittest.main()
