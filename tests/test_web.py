import tempfile
import unittest
from pathlib import Path

from spyglass.targets import Target

try:
    from flask import Flask
    from spyglass.web import create_app
except ImportError:
    Flask = None
    create_app = None


@unittest.skipIf(Flask is None, "Flask is installed from requirements.txt")
class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.models = root / "models"
        self.models.mkdir()
        (self.models / "robots.rpk").touch()
        self.settings_path = root / "settings.json"
        self.app = create_app(
            settings_path=self.settings_path,
            model_dir=self.models,
            labels_path=self.models / "labels.txt",
        )
        self.app.extensions["spy_glass"]["runtime"].apply_settings = lambda settings: None
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_home_page_and_status_endpoint(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"robots.rpk", page.data)
        self.assertIn(b"refreshDetections", page.data)
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json["team_number"], 0)

    def test_status_endpoint_returns_latest_targets(self):
        class StubCamera:
            error = ""

            @staticmethod
            def latest_targets():
                return [Target("robot", 0.9, 10, 20, 30, 40)]

        self.app.extensions["spy_glass"]["runtime"].camera = StubCamera()

        status = self.client.get("/api/status")

        self.assertEqual(status.json["targets"], [{
            "label": "robot",
            "confidence": 0.9,
            "x": 10,
            "y": 20,
            "width": 30,
            "height": 40,
        }])

    def test_saves_valid_settings(self):
        response = self.client.post(
            "/settings",
            data={
                "team_number": "578",
                "model": "robots.rpk",
                "confidence": "0.7",
                "iou": "0.5",
                "camera_width": "640",
                "camera_height": "480",
                "camera_fps": "30",
                "horizontal_fov": "62.2",
                "vertical_fov": "48.8",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.settings_path.exists())
        self.assertEqual(self.client.get("/api/status").json["team_number"], 578)

    def test_rejects_invalid_settings_without_saving(self):
        response = self.client.post("/settings", data={"team_number": "bad"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.settings_path.exists())


if __name__ == "__main__":
    unittest.main()
