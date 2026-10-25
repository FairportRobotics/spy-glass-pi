"""Flask web interface for configuration and camera debugging."""

import os
import secrets
import time
from pathlib import Path

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for

from spyglass.config import (
    Settings,
    SettingsError,
    list_models,
    load_settings,
    save_settings,
)
from spyglass.model_packaging import ModelPackagingError, package_packer_output
from spyglass.runtime import VisionRuntime


def create_app(
    settings_path: Path | None = None,
    model_dir: Path | None = None,
    labels_path: Path | None = None,
) -> Flask:
    root = Path(__file__).resolve().parent.parent
    model_dir = model_dir or root / "models"
    labels_path = labels_path or model_dir / "labels.txt"
    settings_path = settings_path or Path(
        os.environ.get("SPYGLASS_SETTINGS", str(root / "settings.json"))
    )
    model_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024
    settings = load_settings(settings_path, model_dir)
    runtime = VisionRuntime(model_dir, labels_path)
    runtime.settings = settings
    app.extensions["spy_glass"] = {
        "settings_path": settings_path,
        "model_dir": model_dir,
        "settings": settings,
        "runtime": runtime,
    }

    @app.get("/")
    def index():
        state = app.extensions["spy_glass"]
        return render_template(
            "index.html",
            settings=state["settings"],
            models=list_models(model_dir),
            targets=runtime.targets,
            camera_error=runtime.camera_error,
            networktables_connected=runtime.networktables_connected,
        )

    @app.post("/settings")
    def update_settings():
        state = app.extensions["spy_glass"]
        try:
            settings = Settings(
                team_number=int(request.form["team_number"]),
                model=request.form.get("model", ""),
                confidence=float(request.form["confidence"]),
                iou=float(request.form["iou"]),
                camera_width=int(request.form["camera_width"]),
                camera_height=int(request.form["camera_height"]),
                camera_fps=int(request.form["camera_fps"]),
                horizontal_fov=float(request.form["horizontal_fov"]),
                vertical_fov=float(request.form["vertical_fov"]),
            )
            save_settings(settings_path, model_dir, settings)
        except (KeyError, ValueError, SettingsError) as exc:
            flash(f"Settings were not saved: {exc}", "error")
            return redirect(url_for("index"))

        state["settings"] = settings
        try:
            runtime.apply_settings(settings)
            flash("Settings saved and applied.", "success")
        except Exception as exc:
            flash(f"Settings saved, but the camera/runtime could not start: {exc}", "error")
        return redirect(url_for("index"))

    @app.post("/models/package")
    def package_model():
        upload = request.files.get("model_zip")
        if upload is None:
            flash("Choose a compiled IMX500 .zip archive to package.", "error")
            return redirect(url_for("index"))
        try:
            model_name = package_packer_output(
                upload, model_dir, request.form.get("model_name")
            )
        except ModelPackagingError as exc:
            flash(f"Model was not installed: {exc}", "error")
        else:
            flash(
                f"Installed {model_name}. Select it above and save to use it.",
                "success",
            )
        return redirect(url_for("index"))

    @app.errorhandler(413)
    def upload_too_large(_error):
        flash("Model ZIP uploads must be no larger than 128 MiB.", "error")
        return redirect(url_for("index"))

    @app.get("/stream.mjpg")
    def stream():
        def frames():
            while True:
                camera = runtime.camera
                frame = camera.latest_frame() if camera else None
                if frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                time.sleep(0.08)

        return Response(
            frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/status")
    def status():
        return jsonify(
            {
                "team_number": app.extensions["spy_glass"]["settings"].team_number,
                "model": app.extensions["spy_glass"]["settings"].model,
                "camera_error": runtime.camera_error,
                "networktables_connected": runtime.networktables_connected,
                "targets": [target.__dict__ for target in runtime.targets],
            }
        )

    return app
