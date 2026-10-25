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


def suppress_overlapping_targets(
    targets: list[Target], iou_threshold: float
) -> list[Target]:
    """Keep the highest-confidence box when same-class boxes overlap too much."""
    kept: list[Target] = []
    for candidate in sorted(targets, key=lambda target: target.confidence, reverse=True):
        overlaps = False
        for selected in kept:
            if candidate.label != selected.label:
                continue
            left = max(candidate.x, selected.x)
            top = max(candidate.y, selected.y)
            right = min(candidate.x + candidate.width, selected.x + selected.width)
            bottom = min(candidate.y + candidate.height, selected.y + selected.height)
            intersection = max(0.0, right - left) * max(0.0, bottom - top)
            union = (
                candidate.width * candidate.height
                + selected.width * selected.height
                - intersection
            )
            if union > 0 and intersection / union > iou_threshold:
                overlaps = True
                break
        if not overlaps:
            kept.append(candidate)
    return kept
