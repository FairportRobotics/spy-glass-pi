import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from spyglass.camera import VisionCamera
from spyglass.config import Settings


class BoxArray:
    def __init__(self, rows):
        self.rows = rows

    def __truediv__(self, divisor):
        return BoxArray([[value / divisor for value in row] for row in self.rows])

    def __iter__(self):
        return iter(self.rows)


class VisionCameraTests(unittest.TestCase):
    def test_capture_skips_jpeg_encoding_when_stream_has_no_viewers(self):
        vision = VisionCamera(Settings(), Path("models"), Path("models/labels.txt"))
        request = Mock()
        request.get_metadata.return_value = {}
        request.make_array.return_value = object()

        def capture_request():
            vision._stop_event.set()
            return request

        vision._camera = Mock()
        vision._camera.capture_request.side_effect = capture_request
        cv2 = Mock()

        with patch.dict(sys.modules, {"cv2": cv2}):
            vision._capture_loop()

        cv2.imencode.assert_not_called()
        self.assertIsNone(vision.latest_frame())

    def test_capture_encodes_jpeg_when_stream_has_a_viewer(self):
        vision = VisionCamera(Settings(), Path("models"), Path("models/labels.txt"))
        vision.set_stream_enabled(True)
        request = Mock()
        request.get_metadata.return_value = {}
        request.make_array.return_value = object()

        def capture_request():
            vision._stop_event.set()
            return request

        vision._camera = Mock()
        vision._camera.capture_request.side_effect = capture_request
        cv2 = Mock()
        cv2.imencode.return_value = (True, SimpleNamespace(tobytes=lambda: b"jpeg"))

        with patch.dict(sys.modules, {"cv2": cv2}):
            vision._capture_loop()

        cv2.imencode.assert_called_once()
        self.assertEqual(vision.latest_frame(), b"jpeg")

    def test_missing_normalization_metadata_scales_pixel_boxes(self):
        vision = VisionCamera(
            Settings(model="test.rpk", confidence=0.05),
            Path("models"),
            Path("models/labels.txt"),
        )
        vision._imx500 = Mock()
        vision._imx500.get_outputs.return_value = [
            [BoxArray([[448.0, 344.0, 640.0, 600.0]])],
            [[0.9]],
            [[0]],
        ]
        vision._imx500.get_input_size.return_value = (640, 640)
        vision._imx500.convert_inference_coords.return_value = (10, 20, 30, 40)
        vision._intrinsics = SimpleNamespace(
            bbox_normalization=None,
            bbox_order=None,
            labels=["target"],
        )

        with patch("spyglass.camera.logger.warning") as log_warning:
            vision._detect({})
            vision._detect({})

        expected_box = [0.7, 0.5375, 1.0, 0.9375]
        for call in vision._imx500.convert_inference_coords.call_args_list:
            for actual, expected in zip(call.args[0], expected_box):
                self.assertAlmostEqual(actual, expected)
        self.assertEqual(log_warning.call_count, 1)

    def test_explicitly_disabled_normalization_preserves_boxes(self):
        vision = VisionCamera(
            Settings(model="test.rpk", confidence=0.5),
            Path("models"),
            Path("models/labels.txt"),
        )
        vision._imx500 = Mock()
        vision._imx500.get_outputs.return_value = [
            [[[0.1, 0.2, 0.4, 0.5]]],
            [[0.9]],
            [[0]],
        ]
        vision._imx500.get_input_size.return_value = (640, 640)
        vision._imx500.convert_inference_coords.return_value = (10, 20, 30, 40)
        vision._intrinsics = SimpleNamespace(
            bbox_normalization=False,
            bbox_order="yx",
            labels=["target"],
        )

        vision._detect({})

        self.assertEqual(
            vision._imx500.convert_inference_coords.call_args.args[0],
            [0.1, 0.2, 0.4, 0.5],
        )

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
