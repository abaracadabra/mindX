# The face is the control surface

Each sense organ drives the hardware it represents — the interface *is* the face.

| feature | drives | because |
|---------|--------|---------|
| 👁 **eye** | the **camera** (webcam on/off) | the eye is a camera — and a camera has an eye |
| 👂 **ear** | the **microphone** input | the ear hears |
| 👄 **mouth** | the **output audio** (volume / mute) | the mouth speaks |

Click a feature on the live face and it toggles its hardware. Hit-testing
(`src/face_clone/face_controls.js`) maps a canvas click to the feature under it —
feature discs built from the landmark groups in the renderer's own fit transform,
nearest-hit wins — and `CONTROL_MAP` names the wiring. Pure geometry, tested.

## The eye is a camera

Over each iris the demo draws a **lens aperture** — a lens ring and six aperture
blades — that glows cyan and shows a red recording dot while the webcam is live.
The eye doesn't just *represent* the camera; it renders as one.

### Range finder

Because the eye is a camera, the camera can range-find. `distance.js` turns the
measured **inter-pupillary distance** into a distance to the subject with a
pinhole model:

```
D = f · S / s      f = focal length (px)   S = real IPD (~63 mm)   s = IPD (px)
```

Adult IPD is a tight biometric constant, which makes it a dependable ruler (the
same trick face-tracking AR uses). `focalFromFov` derives `f` from the frame
width and the webcam's field of view; `rangeFind` reads the iris landmarks
(468 / 473) and returns the distance in cm — a live **⟠ N cm** readout on the
stage. It returns `null` when the iris landmarks aren't present: it never guesses
a distance.

## Output audio (the mouth)

Clicking the mouth opens a small output panel — a **volume** slider and **mute** —
that drives a Web Audio gain node on the avatar's speech, so the mouth literally
governs what comes out.

## Verification

```
node src/face_clone/face_controls.test.js   # 8 tests
```

- eyes map to the camera, ears to the mic, the mouth to output; a click in empty
  space hits nothing; overlapping features resolve to the nearest centre;
- the range finder is exact against the pinhole model (`D = f·S/s`), inverse in
  IPD pixels, reads ~1 m at the calibrated IPD, and is `null` without the iris.

The canvas draw + the hardware toggles are the browser layer; the hit-testing and
the range-finding geometry are proven headless.
