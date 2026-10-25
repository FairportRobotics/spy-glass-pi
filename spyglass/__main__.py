"""Start Spy Glass on a headless Raspberry Pi."""

import logging
import os

from spyglass.web import create_app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = create_app()
    runtime = app.extensions["spy_glass"]["runtime"]
    settings = app.extensions["spy_glass"]["settings"]
    try:
        runtime.apply_settings(settings)
    except Exception:
        logging.getLogger(__name__).exception(
            "Camera could not start; the settings page will remain available."
        )

    app.run(
        host=os.environ.get("SPYGLASS_HOST", "0.0.0.0"),
        port=int(os.environ.get("SPYGLASS_PORT", "5000")),
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
