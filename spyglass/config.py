"""Loading, validating, and saving the coprocessor settings."""

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Settings:
    team_number: int = 0
    model: str = ""
    confidence: float = 0.55
    iou: float = 0.65
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 30
    horizontal_fov: float = 62.2
    vertical_fov: float = 48.8


class SettingsError(ValueError):
    """A setting is missing, invalid, or refers to an unavailable model."""


def list_models(model_dir: Path) -> list[str]:
    """Return installed IMX500 model packages in stable, displayable order."""
    return sorted(path.name for path in model_dir.glob("*.rpk") if path.is_file())


def validate_settings(
    settings: Settings, model_dir: Path, check_model: bool = True
) -> Settings:
    """Validate values before the settings are used by the app."""
    for name in ("team_number", "camera_width", "camera_height", "camera_fps"):
        if type(getattr(settings, name)) is not int:
            raise SettingsError(f"{name.replace('_', ' ').capitalize()} must be a whole number.")
    for name in ("confidence", "iou", "horizontal_fov", "vertical_fov"):
        value = getattr(settings, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise SettingsError(f"{name.replace('_', ' ').capitalize()} must be a finite number.")
    if not isinstance(settings.model, str):
        raise SettingsError("Model must be a file name.")
    if settings.model and (
        Path(settings.model).name != settings.model
        or not settings.model.endswith(".rpk")
    ):
        raise SettingsError("Model must be the name of an .rpk file.")
    if not 0 <= settings.team_number <= 99999:
        raise SettingsError("FRC team number must be between 0 and 99999.")
    if not 0.0 <= settings.confidence <= 1.0:
        raise SettingsError("Confidence must be between 0 and 1.")
    if not 0.0 <= settings.iou <= 1.0:
        raise SettingsError("IoU must be between 0 and 1.")
    if not 1 <= settings.camera_width <= 1920 or not 1 <= settings.camera_height <= 1080:
        raise SettingsError("Camera width must be 1–1920 and height 1–1080.")
    if not 1 <= settings.camera_fps <= 120:
        raise SettingsError("Camera FPS must be between 1 and 120.")
    if not 1.0 <= settings.horizontal_fov < 180.0:
        raise SettingsError("Horizontal field of view must be between 1 and 180 degrees.")
    if not 1.0 <= settings.vertical_fov < 180.0:
        raise SettingsError("Vertical field of view must be between 1 and 180 degrees.")
    if check_model and settings.model and settings.model not in list_models(model_dir):
        raise SettingsError("Select an installed .rpk model.")
    return settings


def load_settings(path: Path, model_dir: Path) -> Settings:
    """Load settings, creating defaults when no settings file exists yet."""
    if not path.exists():
        return Settings()
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(saved, dict):
            raise SettingsError("Settings file must contain a JSON object.")
        settings = Settings(**saved)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SettingsError(f"Could not read settings file: {exc}") from exc
    return validate_settings(settings, model_dir, check_model=False)


def save_settings(path: Path, model_dir: Path, settings: Settings) -> None:
    """Validate and persist settings as readable JSON."""
    validate_settings(settings, model_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
