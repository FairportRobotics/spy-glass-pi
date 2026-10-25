"""Connect app settings to camera capture and NetworkTables."""

import logging
import threading
from pathlib import Path

from spyglass.camera import VisionCamera
from spyglass.config import Settings
from spyglass.networktables import NetworkTablesPublisher

logger = logging.getLogger(__name__)


class VisionRuntime:
    def __init__(self, model_dir: Path, labels_path: Path):
        self.model_dir = model_dir
        self.labels_path = labels_path
        self.camera: VisionCamera | None = None
        self.publisher: NetworkTablesPublisher | None = None
        self.error = ""
        self.settings = Settings()
        self._lock = threading.Lock()

    def apply_settings(self, settings: Settings) -> None:
        """Restart camera and publisher so changed settings take effect."""
        with self._lock:
            self.stop()
            try:
                self.settings = settings
                if settings.team_number:
                    self.publisher = NetworkTablesPublisher(settings.team_number)
                self.camera = VisionCamera(
                    settings,
                    self.model_dir,
                    self.labels_path,
                    on_targets=self._publish_targets,
                )
                self.camera.start()
                self.error = ""
            except Exception as exc:
                self.error = str(exc)
                logger.exception("Could not start the vision runtime")
                self.stop()
                raise

    def _publish_targets(self, targets) -> None:
        if not self.publisher or not self.camera:
            return
        settings = self.settings
        self.publisher.publish(
            targets,
            settings.camera_width,
            settings.camera_height,
            settings.horizontal_fov,
            settings.vertical_fov,
        )

    def stop(self) -> None:
        if self.camera:
            self.camera.stop()
            self.camera = None
        if self.publisher:
            self.publisher.close()
            self.publisher = None

    @property
    def targets(self):
        return self.camera.latest_targets() if self.camera else []

    @property
    def camera_error(self) -> str:
        return self.camera.error if self.camera else self.error
