# Troubleshooting

### The app starts but the preview stays black / "Camera unavailable"
* Another application may be holding the camera — close video-conferencing apps.
* Try a different `camera.index` in Settings (0, 1, 2…).
* On macOS, grant camera permission under *System Settings → Privacy & Security
  → Camera*.
* On Linux, ensure your user can access `/dev/video*` (often the `video` group).

### "model … is not downloaded" / download fails
The MediaPipe models are fetched once from Google's servers. If you are offline
on first run:

```
python scripts/download_models.py
```

while connected, or copy the `.task` files into the models directory shown in
the error message. After that the app runs fully offline.

### No voice feedback
Voice is optional. If `pyttsx3` (or a system speech engine) is missing, the app
logs a warning and runs silently. On Linux install `espeak`/`espeak-ng`; on
macOS/Windows the built-in engines are used automatically. You can also disable
voice with `--no-voice` or in Settings.

### Gestures don't trigger / trigger too easily
* Run the **Calibration** wizard — it tunes the confidence floor to your hand.
* Increase `recognition.min_consistent_frames` or `min_confidence` to make
  triggering stricter; decrease them to make it more sensitive.
* Ensure good, even lighting and keep the whole hand in frame.

### Photos are rejected as "too blurry" / "eyes closed"
Lower `quality.blur_threshold`, or turn off `quality.reject_blurry`. Disable
`face.validate_eyes` / `face.require_smile` if you don't want those checks.

### Background removal does nothing
It requires the optional extra:

```
pip install "gesturecam-pro[bg]"
```

If `rembg` is not installed the app keeps the original image and logs a warning.

### Logs
Rotating logs are written under the platform logs directory
(`gesturecam.log`). Start with `--log-level DEBUG` for verbose diagnostics.
