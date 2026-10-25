import unittest
from pathlib import Path
from unittest.mock import Mock

from spyglass.camera import VisionCamera
from spyglass.config import Settings


class VisionCameraTests(unittest.TestCase):
    def test_stop_closes_camera_after_stopping_capture(self):
        camera = Mock()
        vision = VisionCamera(Settings(), Path("models"), Path("models/labels.txt"))
        vision._camera = camera

        vision.stop()

        camera.stop.assert_called_once_with()
        camera.close.assert_called_once_with()
        self.assertIsNone(vision._camera)

    def test_stop_closes_camera_if_stopping_raises(self):
        camera = Mock()
        camera.stop.side_effect = RuntimeError("stop failed")
        vision = VisionCamera(Settings(), Path("models"), Path("models/labels.txt"))
        vision._camera = camera

        with self.assertRaisesRegex(RuntimeError, "stop failed"):
            vision.stop()

        camera.close.assert_called_once_with()
        self.assertIsNone(vision._camera)


if __name__ == "__main__":
    unittest.main()
