"""Downloading and caching of model assets.

:func:`ensure_model` returns the local path of a model, downloading it only if
it is missing. Downloads are written to a temporary file and atomically moved
into place so an interrupted download never leaves a corrupt cached file. When
offline and the model is absent, a :class:`MissingModelError` is raised with a
clear, actionable message.
"""

from __future__ import annotations

import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from ..errors import MissingModelError
from ..logging_setup import get_logger
from ..paths import ensure_dir
from .registry import ModelSpec

logger = get_logger(__name__)

_MIN_VALID_BYTES = 1024


def is_cached(spec: ModelSpec) -> bool:
    path = spec.local_path()
    return path.exists() and path.stat().st_size >= _MIN_VALID_BYTES


def ensure_model(spec: ModelSpec, *, allow_download: bool = True) -> Path:
    """Return the local path to ``spec``'s file, downloading if needed."""
    path = spec.local_path()
    if is_cached(spec):
        logger.debug("Model %s already cached at %s", spec.key, path)
        return path

    if not allow_download:
        raise MissingModelError(f"model {spec.key!r} is not downloaded and downloads are disabled")

    ensure_dir(path.parent)
    logger.info("Downloading model %s from %s", spec.key, spec.url)
    try:
        with (
            urllib.request.urlopen(spec.url, timeout=60) as response,  # noqa: S310
            tempfile.NamedTemporaryFile(delete=False, dir=path.parent, suffix=".part") as tmp,
        ):
            shutil.copyfileobj(response, tmp)
            tmp_path = Path(tmp.name)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise MissingModelError(
            f"failed to download model {spec.key!r}. Connect to the internet for the "
            f"one-time download, or place the file manually at {path}. ({exc})"
        ) from exc

    if tmp_path.stat().st_size < _MIN_VALID_BYTES:
        tmp_path.unlink(missing_ok=True)
        raise MissingModelError(f"downloaded model {spec.key!r} looks invalid (too small)")

    tmp_path.replace(path)
    logger.info("Model %s ready at %s", spec.key, path)
    return path
