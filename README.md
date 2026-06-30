# GestureCam Pro

**Touchless camera control through real-time hand-gesture recognition.**

GestureCam Pro turns your webcam into a hands-free camera. Hold up a peace sign
to take a photo, a thumbs-up to fire a burst, a pinch to start recording all
without touching the keyboard. It runs **fully offline** (after a one-time model
download), validates framing, focus and expression before it keeps a shot, and
ships with a clean CustomTkinter interface.

> Built around a small, pure-logic core (gesture classification, quality
> scoring, framing analysis) that is independent of any camera, GUI or deep-
> learning runtime see [docs/architecture.md](docs/architecture.md).

---

## Features

* **Six gestures, smoothed over time.** Peace, Fist, Thumbs Up, Thumbs Down,
  Pinch and Open Palm, each scored continuously and confirmed across a sliding
  window so a single noisy frame never fires an action.
* **Configurable gesture → action mapping.** Photo, burst, video toggle,
  detection lock and exit remap any of them.
* **Countdown & burst.** Optional pre-photo countdown with voice; burst mode
  with an automatic **best-shot** selector.
* **Face-aware capture.** Live framing guidance ("move closer", "center your
  face") plus optional eyes-open and smile validation.
* **Quality gating & enhancement.** Rejects blurry frames; conservative
  auto-contrast / brightness / sharpening.
* **Optional background removal** via `rembg`.
* **Offline voice feedback** via `pyttsx3` (degrades silently if unavailable).
* **Gallery** with thumbnails, open-in-viewer, export and delete, backed by
  SQLite metadata.
* **Calibration wizard** that tunes detection to your hand.
* **Robust engineering:** typed throughout, dependency-injected, structured
  rotating logs, graceful error handling, non-blocking threaded capture.

## Requirements

* Python **3.11+**
* A webcam
* Core: `numpy`, `pillow`
* Full app: `opencv-python`, `mediapipe`, `customtkinter`, `pyttsx3`
* Optional: `rembg` + `onnxruntime` (background removal)

## Installation

```bash
git clone <repository-url> gesturecam-pro
cd gesturecam-pro

python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# Full application:
pip install -e ".[ai]"
# …or with background removal and dev tools:
pip install -e ".[ai,bg,dev]"
```

Pre-download the models (optional, enables first run while offline):

```bash
python scripts/download_models.py
```

## Usage

```bash
python main.py                 # or: gesturecam   (after install)
python main.py --no-voice      # disable speech
python main.py --log-level DEBUG
python main.py --config /path/to/config.json
```

Default gestures:

| Gesture | Action |
| --- | --- |
| ✌️ Peace | Take a photo |
| 👍 Thumbs Up | Burst capture (keeps the best) |
| 🤏 Pinch | Start / stop video |
| ✊ Fist | Lock / unlock detection |
| 👎 Thumbs Down | Exit |
| 🖐 Open Palm | — |

The toolbar mirrors these as buttons, and adds Gallery, Calibrate and Settings.

## Configuration

Settings live in a JSON file under your platform's config directory and can be
edited in-app. Full reference: [docs/configuration.md](docs/configuration.md).

## Development

```bash
make install-dev    # editable install with dev + ai extras
make format         # black
make lint           # ruff
make type           # mypy (pure-logic core)
make test           # pytest
make check          # lint + type + test
```

### Testing

The test suite exercises the **pure-logic layers** — gesture classification and
stabilisation, blur/brightness/quality scoring, best-shot selection, face
framing and mesh metrics, and config round-tripping. These run with only
`numpy` + `pillow` installed and need no camera, display or MediaPipe:

```bash
pytest
```

The hardware/GUI/MediaPipe-facing layers (camera, video, audio, detectors and
the CustomTkinter windows) are fully typed and decoupled behind protocols, but
require a real webcam, display and the `ai` extra to run; they are validated
manually rather than in CI.

## Packaging

```bash
make package        # PyInstaller -> dist/GestureCamPro/
```

See [GestureCamPro.spec](GestureCamPro.spec) for bundling details. Models are
downloaded at first run rather than bundled.

## Project layout

```
gesturecam/
  config/      typed config schema + JSON manager
  camera/      threaded capture, frame model, enumeration
  gestures/    landmarks, pure classifier, stabiliser, MediaPipe detector
  face/        framing analysis, mesh metrics, MediaPipe detector
  quality/     blur, brightness, best-shot scoring, enhancement
  video/       threaded MP4 recorder
  audio/       offline TTS (threaded, optional)
  storage/     SQLite capture database + models
  gallery/     gallery operations
  models/      model registry + downloader
  services/    engine, capture pipeline, calibration, events, factory
  ui/          CustomTkinter app, settings, calibration, gallery
docs/          architecture, configuration, troubleshooting
scripts/       download_models.py
tests/         pure-logic unit tests
```

## Troubleshooting

Common issues and fixes: [docs/troubleshooting.md](docs/troubleshooting.md).

## License

MIT — see [LICENSE](LICENSE).
# dashcam
