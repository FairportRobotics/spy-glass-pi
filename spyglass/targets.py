"""Simple data object shared by the camera, web interface, and NT publisher."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    label: str
    confidence: float
    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2
