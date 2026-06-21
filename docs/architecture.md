# Architecture

GestureCam Pro is organised as a set of small, single-responsibility packages
with a strict dependency direction: **pure logic at the bottom, hardware and UI
at the top**. The lower layers know nothing about cameras, MediaPipe or the GUI,
which is what makes them fast to test and easy to reason about.

## Layered overview

```
                +------------------------------------------+
   UI layer     |  gesturecam.ui (CustomTkinter)           |
                |  app · settings · calibration · gallery  |
                +-------------------+----------------------+
                                    | events (one-way)
                +-------------------v----------------------+
  Services      |  gesturecam.services                     |
                |  engine · capture_service · factory ·    |
                |  calibration · events (EventBus)         |
                +---+----------+----------+----------+------+
                    |          |          |          |
        +-----------v--+  +----v-----+ +--v-------+ +v---------+
  I/O   |  camera      |  |  video   | |  audio   | |  storage |
        |  (OpenCV)    |  | (OpenCV) | | (pyttsx3)| | (sqlite) |
        +-----------+--+  +----------+ +----------+ +----------+
                    |
        +-----------v------------------------------------------+
  Core  |  gestures · quality · face · models · config         |
        |  (pure: numpy / Pillow / stdlib only)                |
        +------------------------------------------------------+
                    |
        +-----------v------------------------------------------+
  Base  |  errors · paths · logging_setup                      |
        +------------------------------------------------------+
```

## Key design decisions

**Pure core, isolated hardware.** Gesture classification, temporal smoothing,
quality metrics, best-shot scoring and face-mesh maths are pure functions over
NumPy arrays. They contain no I/O, so they are unit-tested directly and run in
CI without a camera, a display or MediaPipe installed.

**Dependency inversion at the hardware boundary.** MediaPipe-backed detectors
sit behind the `HandDetector` and `FaceDetector` `Protocol`s; the camera, voice
and recorder are likewise concrete implementations the engine receives rather
than constructs. The `DependencyFactory` is the single place that builds the
heavy objects, so swapping in fakes for testing is trivial.

**Lazy heavy imports.** `cv2`, `mediapipe`, `customtkinter`, `pyttsx3` and
`rembg` are imported *inside* the classes that use them, never at module top
level. As a result `import gesturecam` (and the whole pure core) works with only
`numpy` and `pillow` present — which is exactly what the test suite and the
type-checked core rely on.

**Threading model.** Three threads cooperate:

* the **camera thread** continuously reads frames and always exposes only the
  latest one (no backlog);
* the **engine thread** runs the detect → classify → stabilise → dispatch loop
  and the countdown/burst state machines;
* the **UI thread** owns all widgets and drains the `EventBus` on a Tk timer.

Communication is one-directional and explicit: the engine *publishes* immutable
event objects and the UI *drains* them. The UI sends user actions back through a
small thread-safe command queue (`GestureEngine.request_action`). Widgets are
never touched off the UI thread.

**Temporal stability.** A single noisy frame never triggers an action. The
`GestureStabilizer` requires a gesture to dominate a sliding window for a
minimum number of frames, gates on confidence, and enforces a cooldown so a held
gesture fires exactly once.

## Data flow for a photo

1. Camera thread captures a frame.
2. Engine detects the face (framing guidance + quality inputs) and the hand.
3. The hand landmarks are classified into a `GestureResult`.
4. The stabiliser confirms a `PEACE` gesture and returns it once.
5. The mapped action (`PHOTO`) starts a countdown state machine.
6. On zero, `CaptureService` validates blur/eyes/smile, enhances, optionally
   removes the background, writes the image and records it in SQLite.
7. A `CaptureSaved` event reaches the UI, which shows a toast.
