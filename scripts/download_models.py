#!/usr/bin/env python3
"""Pre-download the MediaPipe model assets used by GestureCam Pro.

Run this once (while online) to populate the local model cache so the app can
start fully offline afterwards:

    python scripts/download_models.py
"""

from __future__ import annotations

import sys

# Allow running directly from a checkout without installing the package.
sys.path.insert(0, ".")

from gesturecam.errors import MissingModelError  # noqa: E402
from gesturecam.models import ALL_MODELS, ensure_model  # noqa: E402


def main() -> int:
    failures = 0
    for spec in ALL_MODELS:
        print(f"Ensuring {spec.key} ({spec.description})")  # noqa: T201
        try:
            path = ensure_model(spec)
        except MissingModelError as exc:
            print(f"  ! {exc}", file=sys.stderr)  # noqa: T201
            failures += 1
            continue
        print(f"  -> {path}")  # noqa: T201
    if failures:
        print(f"{failures} model(s) could not be downloaded.", file=sys.stderr)  # noqa: T201
        return 1
    print("All models are ready.")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
