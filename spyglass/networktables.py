"""Limelight-style NetworkTables output for detected targets."""

import json
import math
from dataclasses import asdict

from spyglass.targets import Target


def target_values(
    targets: list[Target],
    image_width: int,
    image_height: int,
    horizontal_fov: float,
    vertical_fov: float,
) -> dict[str, float | int | str]:
    """Convert the best target and all detections to Limelight-style values."""
    best = max(targets, key=lambda target: target.confidence, default=None)
    if best is None:
        tx = ty = ta = 0.0
        target_class = ""
        confidence = 0.0
    else:
        tx = math.degrees(
            math.atan(
                (best.center_x - image_width / 2)
                / (image_width / 2)
                * math.tan(math.radians(horizontal_fov / 2))
            )
        )
        ty = math.degrees(
            math.atan(
                (image_height / 2 - best.center_y)
                / (image_height / 2)
                * math.tan(math.radians(vertical_fov / 2))
            )
        )
        ta = 100.0 * best.width * best.height / (image_width * image_height)
        target_class = best.label
        confidence = best.confidence

    return {
        "tv": 1 if best else 0,
        "tx": tx,
        "ty": ty,
        "ta": ta,
        "target_count": len(targets),
        "target_class": target_class,
        "target_confidence": confidence,
        "targets": json.dumps([asdict(target) for target in targets]),
    }


class NetworkTablesPublisher:
    """Publish latest camera results to the robot's NetworkTables server."""

    def __init__(self, team_number: int, table_name: str = "limelight"):
        try:
            from ntcore import NetworkTableInstance
        except ImportError as exc:
            raise RuntimeError(
                "NetworkTables support is missing; install the requirements first."
            ) from exc

        self.instance = NetworkTableInstance.getDefault()
        self.instance.startClient4("spy-glass")
        self.instance.setServerTeam(team_number)
        self.table = self.instance.getTable(table_name)

    def publish(
        self,
        targets: list[Target],
        image_width: int,
        image_height: int,
        horizontal_fov: float,
        vertical_fov: float,
    ) -> None:
        """Update all target entries; no-target results clear stale values."""
        for name, value in target_values(
            targets, image_width, image_height, horizontal_fov, vertical_fov
        ).items():
            if isinstance(value, str):
                self.table.putString(name, value)
            elif isinstance(value, int):
                self.table.putNumber(name, value)
            else:
                self.table.putNumber(name, value)
        self.instance.flush()

    def close(self) -> None:
        self.instance.stopClient()

    @property
    def connected(self) -> bool:
        """Whether this client currently has a NetworkTables connection."""
        return self.instance.isConnected()
