"""Pytest configuration.

Ensures the project root is importable so ``import gesturecam`` works regardless
of the directory pytest adds to ``sys.path`` under its default import mode.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
