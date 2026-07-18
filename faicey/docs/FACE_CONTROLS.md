# The face is the control surface

Each sense organ drives the hardware it represents — the interface *is* the face.

| feature | drives | because |
|---------|--------|---------|
| 👁 **eye** | the **camera** (webcam on/off) | the eye is a camera — and a camera has an eye |
| 👂 **ear** | the **microphone** input — and it **pulses like a speaker showing a live frequency response** | the ear hears |
| 👄 **mouth** | the **output audio** (volume / mute) — and it **shows the voice as a waveform** | the mouth speaks |
| 👃 **nose** | **networking diagnostics** (latency, jitter, connection) | the nose smells the network |
| 🩸 right **nostril** | **blockchain scan** — the connected wallet's balance (18-dp), nonce, chain | one nostril sniffs the chain |
| 🔎 left **nostril** | **RAGE search** — the knowledge index at rage.pythai.net | the other sniffs knowledge |
| 🧠 left **forehead** | **analytical** reasoning + math tools | left brain |
| 🧠 right **forehead** | **creativity** + expression tools | right brain |
| 👁 **third eye** | the **deep diagnostic matrix** — *a semi-hidden easter egg, not always there* | it sees everything |

Click a feature to open its tool panel. The tools themselves are the tested cores
in `nose_tools.js` (ping stats, JSON-RPC payloads, wei→ETH at 18-dp, address
validation, search ranking). The blockchain scan is **read-only through the
user's own wallet**; RAGE search proxies the public index and falls back to a link.

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

## Audio-reactive overlays (mouth + ears)

The face is also a live instrument for the sound flowing through it:

- **the mouth shows the voice as a waveform** — a filled, glowing oscilloscope
  clipped to the lip contour, emphasised while the avatar speaks
  (`drawMouthScope` / `drawMouthScopeAt`);
- **the ears pulse like speakers, each showing a frequency response** — the
  spectrum binned into 12 log-spaced bands, drawn as colour-coded radial bars
  fanning from the ear (low→red, high→violet), longest where that band is loud
  (`drawEarBandsAt`, fed by the same FFT as the scope).

Both render in **every mode**. In the 2D modes they use the renderer's fit
transform; in **webgl** they are projected through the 3D camera
([WEBGL_RENDER.md](./WEBGL_RENDER.md)) so they track the mouth and ears as the
head turns.

## Morph modes + age

The face morphs on a sliding scale (`morph.js`, `mech.js`):

- **human ↔ cyborgi** — one side becomes a **polished, reflective chrome
  endoskeleton** rendered in high detail: layered chrome plates with diagonal
  metal gradients, bevel edges and dark seams, rivets with specular dots,
  **hydraulic pistons** at the jaw hinge, exposed segmented metal teeth, a
  detailed **red optical sensor** (chrome housing, iris rings, a hot core, a lens
  flare and a red bloom), cool/warm environment-reflection rims, and specular
  streaks. A generic cyborg — no specific copyrighted character — driven
  procedurally by the landmarks and ramped over a soft centre seam.
- **archetypes** — **vampire** (fangs, pallor), **elf** (pointed ears),
  **dragon** (horns, scale ridge, gold eyes), **pleiadian** (large luminous eyes,
  an ethereal halo) — stylised, generic, landmark-tracked, at the slider's intensity.
- **age** — a slider from child → elder (procedural aging lines above ~55%),
  recorded in the `.persona` (`age: { value, band, years }`).
- **image upload** — drop in a photo and MediaPipe detects its landmarks (IMAGE
  mode) to become the morph basis (geometry + texture); it degrades to texture on
  the neutral geometry if no face is found.

None of the archetypes reproduce a specific copyrighted character — they render
the well-worn tropes procedurally from the mesh.

## Verification

```
node src/face_clone/face_controls.test.js   # 11 tests
node src/face_clone/nose_tools.test.js      # 8 tests (nose · nostrils)
node src/face_clone/mech.test.js            # 5 tests (human↔machine ramp)
node src/face_clone/morph.test.js           # 6 tests (modes · age)
```

- eyes map to the camera, ears to the mic, the mouth to output; a click in empty
  space hits nothing; overlapping features resolve to the nearest centre;
- the range finder is exact against the pinhole model (`D = f·S/s`), inverse in
  IPD pixels, reads ~1 m at the calibrated IPD, and is `null` without the iris.

The canvas draw + the hardware toggles are the browser layer; the hit-testing and
the range-finding geometry are proven headless.
