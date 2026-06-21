"""Application bootstrap and command-line entry point.

Parses arguments, configures logging, loads (or creates) the configuration,
applies any CLI overrides and launches the UI. All start-up failures are caught
here and reported clearly rather than dumping a traceback at the user.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import APP_NAME, __version__
from .config.manager import ConfigManager
from .errors import GestureCamError
from .logging_setup import configure_logging, get_logger

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gesturecam", description=f"{APP_NAME}: touchless camera control."
    )
    parser.add_argument("--config", type=Path, default=None, help="Path to a config JSON file.")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice feedback.")
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override the log level.",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Program entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)

    manager = ConfigManager(args.config)
    try:
        config = manager.load_or_create()
    except GestureCamError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)  # noqa: T201 - pre-logging failure
        return 2

    if args.log_level:
        config.log_level = args.log_level
    configure_logging(config.log_level)
    logger.info("Starting %s %s", APP_NAME, __version__)

    if args.no_voice:
        config.audio.voice_enabled = False

    try:
        from .ui.app import GestureCamApp
    except ImportError as exc:
        logger.error("UI dependencies are not installed: %s", exc)
        print(  # noqa: T201
            "The graphical interface requires extra packages. Install them with:\n"
            "    pip install 'gesturecam-pro[ai]'",
            file=sys.stderr,
        )
        return 3

    try:
        app = GestureCamApp(config, manager)
        app.mainloop()
    except GestureCamError as exc:
        logger.exception("Fatal application error")
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        return 1
    except KeyboardInterrupt:  # pragma: no cover - interactive
        logger.info("Interrupted by user")
        return 0

    logger.info("Goodbye")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
