"""Headless Picamera2 capture and optional IMX500 object detection."""

import logging
import threading
import time
from pathlib import Path

from spyglass.config import Settings
from spyglass.targets import Target

logger = logging.getLogger(__name__)


class VisionCamera:
    def __init__(
        self,
        settings: Settings,
        model_dir: Path,
        labels_path: Path,
        on_targets=None,
    ):
        self.settings = settings
        self.model_dir = model_dir
        self.labels_path = labels_path
        self.on_targets = on_targets
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._frame = None
        self._targets: list[Target] = []
        self._error = ""
        self._camera = None
        self._imx500 = None
        self._intrinsics = None

    def start(self) -> None:
        """Open the camera and start processing frames in the background."""
        from picamera2 import Picamera2

        if self.settings.model:
            from picamera2.devices import IMX500

            self._imx500 = IMX500(str(self.model_dir / self.settings.model))
            self._intrinsics = self._imx500.network_intrinsics
            if self._intrinsics is None:
                from picamera2.devices.imx500 import NetworkIntrinsics

                self._intrinsics = NetworkIntrinsics()
                self._intrinsics.task = "object detection"
            if self._intrinsics.task != "object detection":
                raise RuntimeError("The selected IMX500 model is not an object detector.")
            if self._intrinsics.labels is None:
                self._intrinsics.labels = self.labels_path.read_text(
                    encoding="utf-8"
                ).splitlines()
            self._intrinsics.update_with_defaults()
            self._camera = Picamera2(self._imx500.camera_num)
        else:
            self._camera = Picamera2()

        config = self._camera.create_video_configuration(
            main={
                "size": (self.settings.camera_width, self.settings.camera_height),
                "format": "RGB888",
            },
            controls={"FrameRate": self.settings.camera_fps},
            buffer_count=6,
        )
        self._camera.configure(config)
        self._camera.start()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop, name="spy-glass-camera", daemon=True
        )
        self._thread.start()

    def _capture_loop(self) -> None:
        try:
            import cv2

            while not self._stop_event.is_set():
                request = self._camera.capture_request()
                try:
                    metadata = request.get_metadata()
                    frame = request.make_array("main")
                finally:
                    request.release()

                targets = self._detect(metadata) if self._imx500 else []
                for target in targets:
                    left, top = int(target.x), int(target.y)
                    right = int(target.x + target.width)
                    bottom = int(target.y + target.height)
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        f"{target.label} {target.confidence:.2f}",
                        (left, max(18, top - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                    )
                success, encoded = cv2.imencode(".jpg", frame)
                if not success:
                    raise RuntimeError("Could not encode the camera frame as JPEG.")
                with self._lock:
                    self._frame = encoded.tobytes()
                    self._targets = targets
                if self.on_targets:
                    self.on_targets(targets)
        except Exception as exc:
            logger.exception("Camera processing stopped unexpectedly")
            with self._lock:
                self._error = str(exc)

    def _detect(self, metadata: dict) -> list[Target]:
        outputs = self._imx500.get_outputs(metadata, add_batch=True)
        if outputs is None:
            return []
        boxes, scores, classes = outputs[0][0], outputs[1][0], outputs[2][0]
        _, input_height = self._imx500.get_input_size()
        if self._intrinsics.bbox_normalization:
            boxes = boxes / input_height
        if self._intrinsics.bbox_order == "xy":
            boxes = boxes[:, [1, 0, 3, 2]]

        by_label: dict[str, list[Target]] = {}
        for box, score, class_id in zip(boxes, scores, classes):
            if float(score) < self.settings.confidence:
                continue
            coords = self._imx500.convert_inference_coords(box, metadata, self._camera)
            label_index = int(class_id)
            labels = self._intrinsics.labels
            if label_index < 0 or label_index >= len(labels):
                logger.warning("Ignoring detection with unknown class index %s", label_index)
                continue
            x, y, width, height = coords
            by_label.setdefault(labels[label_index], []).append(
                Target(
                    labels[label_index],
                    float(score),
                    float(x),
                    float(y),
                    float(width),
                    float(height),
                )
            )

        from spyglass.targets import suppress_overlapping_targets

        return suppress_overlapping_targets(
            [target for candidates in by_label.values() for target in candidates],
            self.settings.iou,
        )

    def latest_frame(self) -> bytes | None:
        with self._lock:
            return self._frame

    def latest_targets(self) -> list[Target]:
        with self._lock:
            return list(self._targets)

    @property
    def error(self) -> str:
        with self._lock:
            return self._error

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        if self._camera:
            self._camera.stop()
            self._camera = None
        self._thread = None
