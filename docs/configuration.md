# Configuration

All settings live in a single JSON file. Its location follows platform
conventions (resolved by `gesturecam.paths`):

| Platform | Path |
| --- | --- |
| Linux   | `~/.config/GestureCamPro/config.json` (honours `$XDG_CONFIG_HOME`) |
| macOS   | `~/Library/Application Support/GestureCamPro/config.json` |
| Windows | `%APPDATA%\GestureCamPro\config.json` |

The file is created with sensible defaults on first run. You can edit it
directly or change everything from the in-app **Settings** window. Unknown or
missing keys fall back to defaults, and every value is validated on load — an
out-of-range value raises a clear error rather than misbehaving silently.

## Sections

### `camera`
| Key | Default | Meaning |
| --- | --- | --- |
| `index` | `0` | OpenCV device index. |
| `width` / `height` | `1280` / `720` | Requested capture resolution. |
| `fps` | `30` | Target frame rate. |
| `mirror` | `true` | Mirror the preview (selfie-style). |

### `recognition`
| Key | Default | Meaning |
| --- | --- | --- |
| `max_hands` | `2` | Maximum hands to track. |
| `min_detection_confidence` | `0.5` | MediaPipe detection threshold. |
| `min_tracking_confidence` | `0.5` | MediaPipe tracking threshold. |
| `window_size` | `8` | Frames in the smoothing window. |
| `min_consistent_frames` | `5` | Frames a gesture must dominate to trigger. |
| `min_confidence` | `0.6` | Minimum classifier confidence to count a frame. |
| `cooldown_seconds` | `1.5` | Minimum gap between triggers. |

### `gestures`
Maps each gesture to an action. Defaults:

| Gesture | Action |
| --- | --- |
| Peace | Take photo |
| Thumbs Up | Burst capture |
| Pinch | Start/stop video |
| Fist | Lock/unlock detection |
| Thumbs Down | Exit |
| Open Palm | (none) |

Valid actions: `none`, `photo`, `burst`, `video_toggle`, `lock_detection`,
`exit`.

### `countdown` / `burst`
`countdown.enabled` + `countdown.seconds` control the pre-photo timer.
`burst.count` and `burst.delay_ms` control burst length and spacing.

### `face`
Framing and validation: `require_face`, `allow_multiple_faces`,
`min_face_area_ratio`, `max_face_area_ratio`, `center_tolerance`,
`require_smile`, `validate_eyes`, `ear_threshold`, `smile_threshold`.

### `quality` / `enhancement` / `background`
`quality.reject_blurry` + `quality.blur_threshold` reject soft shots.
`enhancement.*` applies conservative auto-contrast/brightness/sharpening.
`background.enabled` removes the background (requires the `bg` extra).

### `best_shot`
Weights used to pick the best frame of a burst (`sharpness`, `brightness`,
`face`, `smile`, `eyes`) plus `sharpness_reference` and `keep_best_only`.

### `audio`
`voice_enabled`, `rate`, `volume`, optional `voice_id`.

### `storage`
`save_folder` (defaults to `~/Pictures/GestureCamPro`), `image_format`
(`jpg`/`png`), `jpeg_quality`.

### Top-level
`theme` (`system`/`light`/`dark`), `language`, `log_level`.
