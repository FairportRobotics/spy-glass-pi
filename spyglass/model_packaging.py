"""Package compiled IMX500 converter archives for camera deployment."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from werkzeug.utils import secure_filename


class ModelPackagingError(ValueError):
    """An uploaded archive could not be converted into a camera model."""


def package_packer_output(
    upload, model_dir: Path, requested_name: str | None = None
) -> str:
    """Run imx500-package on a compiled packerOut ZIP and install its RPK."""
    safe_filename = secure_filename(upload.filename or "")
    if not safe_filename or Path(safe_filename).suffix.lower() != ".zip":
        raise ModelPackagingError("Upload a compiled .zip file from the IMX500 converter.")

    model_stem = Path(safe_filename).stem
    if requested_name and requested_name.strip():
        model_stem = secure_filename(requested_name.strip())
        if model_stem.lower().endswith(".rpk"):
            model_stem = model_stem[:-4]
        if not model_stem or model_stem in {".", ".."}:
            raise ModelPackagingError("Enter a valid model name.")
        if len(model_stem) > 64:
            raise ModelPackagingError("Model names must be 64 characters or fewer.")

    model_name = f"{model_stem}.rpk"
    model_path = model_dir / model_name
    if model_path.exists():
        raise ModelPackagingError(f"A model named {model_name} is already installed.")

    packager = shutil.which("imx500-package")
    if not packager:
        raise ModelPackagingError(
            "The imx500-package tool is unavailable. Install the Raspberry Pi "
            "IMX500 tools before packaging models."
        )

    with tempfile.TemporaryDirectory(prefix="spy-glass-package-", dir=model_dir) as temp:
        work_dir = Path(temp)
        archive_path = work_dir / "packerOut.zip"
        output_dir = work_dir / "output"
        output_dir.mkdir()
        upload.save(archive_path)
        if archive_path.stat().st_size == 0:
            raise ModelPackagingError("The uploaded ZIP file is empty.")

        try:
            result = subprocess.run(
                [packager, "-i", str(archive_path), "-o", str(output_dir)],
                capture_output=True,
                check=False,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelPackagingError(
                "Model packaging timed out after 5 minutes."
            ) from exc
        except OSError as exc:
            raise ModelPackagingError(f"Could not run imx500-package: {exc}") from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if detail:
                detail = detail[-1000:]
                raise ModelPackagingError(f"Model packaging failed: {detail}")
            raise ModelPackagingError(
                f"Model packaging failed with exit code {result.returncode}."
            )

        packaged_model = output_dir / "network.rpk"
        if not packaged_model.is_file() or packaged_model.stat().st_size == 0:
            raise ModelPackagingError(
                "imx500-package did not create a non-empty output/network.rpk."
            )

        try:
            os.link(packaged_model, model_path)
        except FileExistsError as exc:
            raise ModelPackagingError(
                f"A model named {model_name} is already installed."
            ) from exc
        packaged_model.unlink()

    return model_name
