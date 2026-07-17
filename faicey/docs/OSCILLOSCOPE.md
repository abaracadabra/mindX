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

- dB scaling (`dbNorm` / `magnitudesToDb`) against a smoothed running reference
  (a gentle AGC), so quiet and loud passages both read;
- rendered by scrolling the canvas one row and painting the newest spectrum on
  top — cheap and smooth;
- `inferno` / `magma` perceptual colormaps, and a `Spectrogram` rolling frame
  buffer for the model (freeze/export), all pure + tested.

Toggle with **🌊 waterfall**.

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
```

- the FFT peaks at exactly the right bin; YIN measures 200/110/440 Hz within a
  hair and returns 0 on noise; the trigger finds the rising crossing; Vpp ≈ 2 and
  Vrms ≈ 0.707 for a unit sine; centroid rises with brightness and rolloff sits
  above the fundamental; HNR is high for a clean tone and drops with noise; notes
  and the frequency-colour map are correct.

The canvas draw is browser-only; every number it displays is proven headless
against signals with known answers.
