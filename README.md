# Spy Glass

Spy Glass is a vision coprocessor for an FRC robot. It runs on a Raspberry Pi
with the Raspberry Pi AI Camera, detects objects with an IMX500 model, shares
target measurements over NetworkTables 4, and provides a small web page for
configuration and camera debugging.

The software is intended to be readable and maintainable by students who are
new to Python. The camera and IMX500 do the image processing; the Pi does not
download or convert PyTorch models.

## What you need

- Raspberry Pi 5 with Raspberry Pi OS **Trixie** (64-bit recommended).
- Raspberry Pi AI Camera connected and enabled.
- A preconverted, camera-compatible `.rpk` IMX500 object-detection model.
- The robot and Pi on a network where the Pi can reach the robot's
  NetworkTables server.

The `.pt` models hosted by the team are not directly usable by this program.
Convert models on a separate computer with a compatible IMX500 conversion
toolchain, then copy the resulting `.rpk` file to the Pi. Model conversion is
outside this application and is never run on the Pi.

## Install on a headless Pi

Connect to the Pi over SSH, clone the repository, and install the OS and Python
dependencies:

```sh
sudo git clone https://github.com/FairportRobotics/spy-glass-pi.git /opt/spy-glass
sudo chown -R "$USER":"$USER" /opt/spy-glass
cd /opt/spy-glass
make install
```

The install target uses Raspberry Pi OS packages for Picamera2, OpenCV, and
IMX500 support. It creates a virtual environment that can still access those
OS camera libraries, then installs Flask and the RobotPy NT4 client there.
This avoids installing packages into the OS-managed Python environment.

Reboot if prompted by the IMX500 package installation:

```sh
sudo reboot
```

Copy an `.rpk` model and the matching `labels.txt` to the Pi's `models/`
folder. The labels file contains one class name per line; the line number is
the class ID used by the model.

Start Spy Glass manually for the first test:

```sh
make run
```

The manual run stores settings in the checkout's ignored `settings.json`. The
systemd service instead stores them in `/var/lib/spy-glass/settings.json`.

From a computer on the same trusted network, open
`http://<raspberry-pi-address>:5000`. Enter the FRC team number, choose the
installed model, check camera settings and confidence/IoU thresholds, then
press **Save and apply**. Team number `0` disables NetworkTables until a team
is configured.

The web page is intentionally unauthenticated for simple use on a private
robotics network. Do not expose port 5000 to the public internet or an
untrusted network.

## Run automatically at boot

The repository includes a systemd service file. From the repository root, run
the Make target to create a dedicated system account, make it the owner of the
checkout, prepare the settings folder, and enable the service:

```sh
sudo make install-service
```

The target assumes the checkout and its virtual environment are at
`/opt/spy-glass`. Copy `.rpk` models into `/opt/spy-glass/models/` and make
sure the `spyglass` account can read them.

Useful service commands:

```sh
sudo systemctl status spy-glass
sudo journalctl -u spy-glass -f
sudo systemctl restart spy-glass
```

## NetworkTables outputs

Spy Glass is an NT4 client. Set the team number in the web page; the app uses
the standard team-based server address. Results are published in the
`/limelight` table:

| Key | Type | Meaning |
| --- | --- | --- |
| `tv` | number | `1` when a target exists, otherwise `0` |
| `tx` | number | Horizontal angle from image center, in degrees |
| `ty` | number | Vertical angle from image center, in degrees |
| `ta` | number | Best target's image area as a percent of the frame |
| `target_count` | number | Number of detections after confidence and IoU filtering |
| `target_class` | string | Class name of the highest-confidence target |
| `target_confidence` | number | Confidence of that target, from 0 to 1 |
| `targets` | string | JSON array of all targets with class, confidence, and pixel bounding box |

The first four keys follow Limelight naming and basic semantics; this is not a
complete Limelight protocol implementation. The best target is the one with
the highest confidence. A target box is `{label, confidence, x, y, width,
height}` in camera pixels, measured from the top-left of the frame.

`tx` and `ty` are calculated from the target-box center and the configured
horizontal/vertical camera field of view. The web page provides FOV settings;
the defaults are starting estimates, not a calibration guarantee. Measure the
camera's actual FOV and verify the sign/angle against a known target before
using `tx`/`ty` for robot alignment. Spy Glass does not currently estimate
robot or target pose.

## Project layout

- `spyglass/config.py` — settings defaults, validation, model discovery, and
  JSON persistence.
- `spyglass/camera.py` — Picamera2 capture, IMX500 detections, NMS, and stream
  frames.
- `spyglass/targets.py` — shared target format and class-aware IoU filtering.
- `spyglass/networktables.py` — Limelight-style values and NT4 publishing.
- `spyglass/runtime.py` — starts/stops the camera and NetworkTables publisher.
- `spyglass/web.py` and `spyglass/templates/index.html` — Flask routes and the
  configuration page.
- `spyglass/__main__.py` — command-line entry point used by the service.
- `models/` — locally installed `.rpk` files (not tracked by Git).
- `models/labels.txt` — class names for the model currently used by the team.
- `tests/` — unit tests that run without a Raspberry Pi or robot.

To run the unit tests after installation:

```sh
make test
```

## Troubleshooting

- **Camera/runtime error on the web page:** check the camera cable and run
  `sudo journalctl -u spy-glass -f`. Confirm `make install` completed and the
  Pi was rebooted after installing IMX500 support.
- **No model appears in the selector:** check that a compatible `.rpk` file is
  in the `models/` folder. PyTorch `.pt` files and conversion zip files are
  not selectable.
- **No detections:** check that the selected model is an object detector, that
  `models/labels.txt` uses the model's class order, and that the confidence
  threshold is not too high.
- **No robot connection:** verify the team number and that the robot's NT4
  server is reachable from the Pi. A team number of `0` intentionally turns
  off the client.
- **`tx`/`ty` seem inaccurate:** calibrate horizontal and vertical FOV and
  check that camera resolution and model inference are configured as expected.
