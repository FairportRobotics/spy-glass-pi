import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from spyglass.config import Settings
from spyglass.runtime import VisionRuntime


class VisionRuntimeStreamTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.runtime = VisionRuntime(root / "models", root / "labels.txt")

    def tearDown(self):
        self.runtime.stop()
        self.temp_dir.cleanup()

    def test_stream_encoding_stays_enabled_until_last_viewer_disconnects(self):
        camera = Mock()
        self.runtime.camera = camera

        self.runtime.stream_client_connected()
        self.runtime.stream_client_connected()
        self.runtime.stream_client_disconnected()

        camera.set_stream_enabled.assert_any_call(True)
        camera.set_stream_enabled.assert_called_once_with(True)

        self.runtime.stream_client_disconnected()
        camera.set_stream_enabled.assert_called_with(False)

    @patch("spyglass.runtime.VisionCamera")
    def test_new_camera_inherits_active_stream_viewers(self, camera_class):
        self.runtime.stream_client_connected()

        self.runtime.apply_settings(Settings(team_number=0))

        camera_class.return_value.set_stream_enabled.assert_called_once_with(True)
        camera_class.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
