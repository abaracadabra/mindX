# The scientific oscilloscope

A proper measurement instrument overlaid on the FACE — a triggered time-domain
trace, a colour-coded spectrum, accurate frequency measurement, zoom, and
forensic measures. The algorithms are the canonical open-source ones, chosen
after reviewing how real scopes and pitch trackers work; nothing is a heuristic
stand-in (`src/face_clone/oscilloscope.js`, pure + headless-tested).

## Frequency measurement — YIN

The fundamental is measured with **YIN** (de Cheveigné & Kawahara, 2002) — the
reference method behind aubio/librosa-class pitch tracking: the difference
function → cumulative-mean normalisation → absolute threshold → **parabolic
interpolation** for sub-sample (sub-Hz) accuracy. On a synthetic 200 Hz voice it
lands within **1 Hz**, and it reports a **clarity** (periodicity) score. On
noise or silence it returns `hz = 0` — it never invents a pitch.

The readout shows ƒ₀ in Hz, the nearest musical **note + cents** (A4 = 440), the
**period** in ms, and clarity.

## Colour-coded spectrum

A windowed magnitude spectrum (**Hann window → radix-2 FFT**) drawn so that each
column's **hue is its frequency** — low → red, high → violet, log-scaled across
the audible band (`freqColor`). Bar height is the perceptual (√) magnitude, and
the measured fundamental is marked with a bright line at its own colour. You read
the timbre at a glance: where the energy sits and how the harmonics stack.

## Triggering + zoom

- **Edge trigger** (`detectTrigger`) starts the trace at a rising zero-crossing
  — the way a real scope (sigrok/PulseView) freezes a repeating waveform so it
  stands still instead of scrolling. Toggle with **⎍ trig**.
- **Zoom** (the **＋ / －** buttons or the mouse wheel over the trace) tightens
  the time base from 1× to 32×, showing fewer samples across the width so you can
  inspect a single glottal period. A calibrated 10 × 8 division grid frames it.

## Spectrogram waterfall (🌊)

A scrolling **time–frequency** history under the spectrum (`src/face_clone/spectrogram.js`).
Each FFT frame becomes the top row and the history flows **downward** — a
waterfall. The spatial axis is frequency, and the **colour axis is intensity in
dB** on a perceptual **inferno** colormap (the de-facto spectrogram standard) —
so the harmonics of speech draw bright rails you can watch move with pitch, and
formants show as steady bands.

**Interaction:** hover the waterfall to read the **frequency** (from x), the
**time-ago** (from y, using the measured row interval), and the **intensity in
dB** at that point — read from the `Spectrogram` model's stored history, with a
cyan guide mirrored onto the spectrum above. **Click to freeze** the image for
inspection (click again to resume). A frequency axis (0 · 2k · 4k · 6k · 8k Hz)
labels it.

- dB scaling (`dbNorm` / `magnitudesToDb`) against a smoothed running reference
  (a gentle AGC), so quiet and loud passages both read;
- rendered by scrolling the canvas one row and painting the newest spectrum on
  top — cheap and smooth;
- `inferno` / `magma` perceptual colormaps, and a `Spectrogram` rolling frame
  buffer for the model (freeze/export), all pure + tested.

Toggle with **🌊 waterfall**.

## Accuracy — a quant-finance toolset (`finmeasure.js`)

A voice signal is a time series, and quantitative finance has the sharpest tools
anywhere for measuring a noisy series *with a stated uncertainty*. Those exact
tools sharpen the scope's numbers:

- **Kalman filter** — each clear per-frame YIN reading is folded into a Kalman
  filter (the standard state estimator in quant), giving a **stabilised ƒ₀** with
  its own variance. The smoothed track is provably tighter than the raw estimates.
- **Confidence interval** — the readout shows **ƒ₀ ± 95% CI** (Hz), computed from
  the recent window's standard error. That ± is the accuracy, stated honestly.
- **Jitter / shimmer** — EWMA volatility (RiskMetrics σ) of the pitch track *is*
  voice **jitter**; of the amplitude track *is* **shimmer** — real
  forensic/clinical voice measures, here derived from the finance volatility math.
- **z-score / outliers** — a spliced-in frame reads as a statistical outlier.
- Every accuracy number is carried at **conventional EVM 18-decimal precision**
  (`toFixed18Str`, signed + carry-safe — the same fixed-point scale as the
  faceprint/voiceprint), so it can travel on-chain or into a voiceprint.

All of it is pure and proven headless (Kalman converges + reduces variance, the
CI shrinks like 1/√n and brackets the truth, jitter/shimmer are 0 on a steady
track, moments match known series, 18-dp strings carry exactly 18 digits).

## The sci-fi HUD substrate (◈) — shared with voicey

A **◈ HUD** toggle themes the whole measurement panel as a sci-fi instrument
(cyan telemetry, glow, uppercase mono) and mounts a live HUD strip. That HUD is
**`scifi_substrate.js`** — a shared, dependency-free substrate **evolved from the
DeltaVerse participant field** (`dapp/deltaverse.js` — the drifting "stars are
people") and fused with instrument chrome (corner brackets, a reticle, a grid, a
sweep). The same module is vendored into **voaice** (`voaice/src/scifi_substrate.js`),
so faicey and voicey share one visual language across the constellation. The
layout geometry + the drifting field are pure and tested; the canvas draw is the
browser layer.

## Forensic measures (🔬)

Computed **in-browser** (so they work standalone, without the voaice peer):

- **spectral centroid** (Hz) — the brightness first moment;
- **spectral rolloff** (Hz) — where 85 % of the energy sits below;
- **HNR** (dB) — harmonic-to-noise ratio from the normalised autocorrelation
  peak (Boersma 1993, as in Praat), with a voiced / mixed / noise reading;
- **Vpp / Vrms / ZCR** — peak-to-peak, RMS, zero-crossing rate.

When the voaice peer is present the demo still measures the full 18-dp SoundWave
voiceprint through it (`/api/voice/measure`); this scope is the always-available
scientific layer on top.

## Verification

```
node src/face_clone/oscilloscope.test.js    # 12 tests
node src/face_clone/spectrogram.test.js     # 8 tests (waterfall)
node src/face_clone/finmeasure.test.js      # 14 tests (accuracy + 18-dp)
node src/face_clone/scifi_substrate.test.js # 4 tests (shared HUD substrate)
```

- the FFT peaks at exactly the right bin; YIN measures 200/110/440 Hz within a
  hair and returns 0 on noise; the trigger finds the rising crossing; Vpp ≈ 2 and
  Vrms ≈ 0.707 for a unit sine; centroid rises with brightness and rolloff sits
  above the fundamental; HNR is high for a clean tone and drops with noise; notes
  and the frequency-colour map are correct.

The canvas draw is browser-only; every number it displays is proven headless
against signals with known answers.
