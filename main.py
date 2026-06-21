#!/usr/bin/env python3
"""Convenience launcher: ``python main.py`` runs the application.

The real entry point lives in :func:`gesturecam.app.main`; this thin wrapper
exists so the project can be started without installing it first.
"""

from __future__ import annotations

from gesturecam.app import main

if __name__ == "__main__":
    raise SystemExit(main())
