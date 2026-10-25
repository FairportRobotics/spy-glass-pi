import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual(status.json["team_number"], 578)
        self.assertFalse(status.json["networktables_connected"])
        self.assertIn(b"NetworkTables:", page.data)
        self.assertIn(b"Advanced camera settings", page.data)
        self.assertIn(b"Output stream width (pixels)", page.data)

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

    def test_status_endpoint_reports_networktables_connection(self):
        class StubPublisher:
            connected = True

        self.app.extensions["spy_glass"]["runtime"].publisher = StubPublisher()

        status = self.client.get("/api/status")

        self.assertTrue(status.json["networktables_connected"])

    def test_stream_viewer_is_removed_when_response_closes(self):
        runtime = self.app.extensions["spy_glass"]["runtime"]

        class StubCamera:
            @staticmethod
            def set_stream_enabled(_enabled):
                pass

            @staticmethod
            def latest_frame():
                return b"jpeg"

        runtime.camera = StubCamera()
        response = self.client.get("/stream.mjpg", buffered=False)
        frames = iter(response.response)

        self.assertIn(b"jpeg", next(frames))
        self.assertEqual(runtime._stream_clients, 1)

        response.close()

        self.assertEqual(runtime._stream_clients, 0)

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

    @patch("spyglass.model_packaging.shutil.which", return_value="/usr/bin/imx500-package")
    @patch("spyglass.model_packaging.subprocess.run")
    def test_packages_compiled_zip_and_installs_model(self, run, _which):
        def create_packaged_output(command, **_kwargs):
            output_dir = Path(command[4])
            (output_dir / "network.rpk").write_bytes(b"rpk")
            return subprocess.CompletedProcess(command, 0, "", "")

        run.side_effect = create_packaged_output
        response = self.client.post(
            "/models/package",
            data={"model_zip": (io.BytesIO(b"zip archive"), "packerOut.zip")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue((self.models / "packerOut.rpk").is_file())
        self.assertIn(b"Installed packerOut.rpk", response.data)
        self.assertEqual(run.call_args.args[0][0], "/usr/bin/imx500-package")

    @patch("spyglass.model_packaging.shutil.which", return_value="/usr/bin/imx500-package")
    @patch("spyglass.model_packaging.subprocess.run")
    def test_custom_model_name_is_used_for_installed_package(self, run, _which):
        def create_packaged_output(command, **_kwargs):
            output_dir = Path(command[4])
            (output_dir / "network.rpk").write_bytes(b"rpk")
            return subprocess.CompletedProcess(command, 0, "", "")

        run.side_effect = create_packaged_output
        response = self.client.post(
            "/models/package",
            data={
                "model_name": "Team 578 reefscape",
                "model_zip": (io.BytesIO(b"zip archive"), "packerOut.zip"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue((self.models / "Team_578_reefscape.rpk").is_file())
        self.assertIn(b"Installed Team_578_reefscape.rpk", response.data)

    @patch("spyglass.model_packaging.shutil.which", return_value="/usr/bin/imx500-package")
    @patch("spyglass.model_packaging.subprocess.run")
    def test_rejects_non_zip_upload(self, run, _which):
        response = self.client.post(
            "/models/package",
            data={"model_zip": (io.BytesIO(b"not a zip"), "model.pt")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Upload a compiled .zip file", response.data)
        run.assert_not_called()

    @patch("spyglass.model_packaging.shutil.which", return_value=None)
    def test_reports_missing_packaging_tool(self, _which):
        response = self.client.post(
            "/models/package",
            data={"model_zip": (io.BytesIO(b"zip archive"), "packerOut.zip")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"imx500-package tool is unavailable", response.data)

    @patch("spyglass.model_packaging.shutil.which", return_value="/usr/bin/imx500-package")
    @patch("spyglass.model_packaging.subprocess.run")
    def test_reports_packaging_failure_without_installing_model(self, run, _which):
        run.return_value = subprocess.CompletedProcess(
            [], 1, "", "invalid packer archive"
        )
        response = self.client.post(
            "/models/package",
            data={"model_zip": (io.BytesIO(b"bad archive"), "packerOut.zip")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Model packaging failed: invalid packer archive", response.data)
        self.assertFalse((self.models / "packerOut.rpk").exists())

    @patch("spyglass.model_packaging.shutil.which", return_value="/usr/bin/imx500-package")
    @patch("spyglass.model_packaging.subprocess.run")
    def test_does_not_overwrite_existing_model(self, run, _which):
        (self.models / "packerOut.rpk").write_bytes(b"existing model")

        response = self.client.post(
            "/models/package",
            data={"model_zip": (io.BytesIO(b"zip archive"), "packerOut.zip")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A model named packerOut.rpk is already installed", response.data)
        self.assertEqual((self.models / "packerOut.rpk").read_bytes(), b"existing model")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
