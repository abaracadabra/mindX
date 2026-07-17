# Hardware — cameras, microphones, and facial recognition

The `/face` demo drives the FACE from live hardware. This is how it recognises
devices and runs facial recognition, and how it fails honestly when it can't.

## Device recognition

Every camera and microphone is enumerated (`navigator.mediaDevices.enumerateDevices`)
into two selectors, with a live count — *"2 cameras · 1 mic recognised"*.

- Device **labels** are hidden by the browser until the first `getUserMedia`
  grant, so the count appears immediately and names fill in after you allow
  access once. The demo re-enumerates right after the grant.
- The list **re-scans on `devicechange`** — plug in a USB webcam or headset and it
  appears without a reload.
- Selecting a device passes `deviceId: { exact }` to `getUserMedia`; **changing
  the selection while live** stops the current stream and restarts on the new
  device. The active track's real label is shown ("live: FaceTime HD Camera").

## Facial recognition

MediaPipe's **478-landmark** Face Landmarker, vendored and served locally (no CDN):

- `static/vendor/mediapipe/face_landmarker.task` (~3.6 MB) + the WASM fileset
  under `static/vendor/mediapipe/wasm/`, resolved through the page's import map
  (`@mediapipe/tasks-vision` → the vendored `vision_bundle.mjs`).
- The recogniser is **built once and reused** (previously it was rebuilt on every
  camera toggle) and is **warmed at startup**, so the first capture is instant.
- A status line reports its real state: *warming up → loading the model → ready
  (MediaPipe 478-landmark tracker)*, or *unavailable* with the reason.
- A **live tracking indicator** shows whether a face is currently detected —
  green *"● face tracked · 478 landmarks"* or amber *"○ no face — centre in
  frame"*. `detectForVideo` is guarded on the video having a real frame, and a
  persistent tracking error is surfaced rather than swallowed.

The landmarks feed the whole pipeline: live reenactment, `◉ capture my face →
FAICE` (aggregation + accuracy scoring), and the render ladder
(wireframe → surface → photoreal → neural).

## When it can't run

Honest, specific failure — never a silent dead control:

| condition | what the UI says |
|-----------|------------------|
| no media API in the browser | "this browser has no media devices API" |
| not HTTPS / localhost | "camera needs HTTPS or localhost (not a secure context)" |
| permission refused | "permission denied (allow access in the browser)" |
| device in use elsewhere | "the device is in use by another app" |
| selected device gone | "the selected device is unavailable" |
| recogniser fails to load | falls back to the neutral face, with the reason |

`getUserMedia` requires a **secure context** — served over HTTPS or from
`localhost`. On a plain-HTTP LAN address the browser blocks camera/mic access;
the demo detects this up front and says so.

## Verification

The serving path is verified live — `/face`, the face-clone modules, the
MediaPipe bundle, the model, and the WASM all return `200`. Device enumeration
and detection themselves need a real browser + camera; the load path they depend
on is confirmed.
