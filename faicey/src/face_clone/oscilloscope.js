/**
 * oscilloscope.js — a scientific overlay oscilloscope: accurate frequency
 * measurement, a colour-coded spectrum, edge triggering, zoom, and forensic
 * measures. Pure DSP, headless-testable; the canvas draw lives in the demo.
 *
 * The algorithms are the canonical open-source ones, not approximations:
 *   • frequency      — YIN (de Cheveigné & Kawahara, 2002): the difference
 *                      function → cumulative-mean normalisation → absolute
 *                      threshold → PARABOLIC interpolation for sub-sample Hz.
 *                      The reference method behind aubio/librosa-class pitch.
 *   • spectrum       — radix-2 Cooley–Tukey FFT over a Hann-windowed frame.
 *   • trigger        — rising/falling edge at a level with holdoff, the way a
 *                      real scope (sigrok/PulseView) stabilises the trace.
 *   • HNR            — harmonic-to-noise ratio from the normalised
 *                      autocorrelation peak (Boersma 1993, as in Praat).
 *
 * Nothing is invented: an unmeasurable frequency returns hz=0 with clarity 0,
 * never a fabricated pitch.
 *
 * © Professor Codephreak - rage.pythai.net
 */

// ── FFT (radix-2, in place) ─────────────────────────────────────────────────
export function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { const tr = re[i]; re[i] = re[j]; re[j] = tr; const ti = im[i]; im[i] = im[j]; im[j] = ti; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = i + k + len / 2;
        const vr = re[b] * cr - im[b] * ci, vi = re[b] * ci + im[b] * cr;
        re[b] = re[a] - vr; im[b] = im[a] - vi; re[a] += vr; im[a] += vi;
        const ncr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

export const floorPow2 = (n) => { let p = 1; while (p * 2 <= n) p *= 2; return p; };
export function hann(n) { const w = new Float32Array(n); for (let i = 0; i < n; i++) w[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1)); return w; }

/**
 * Windowed magnitude spectrum.
 * @returns {{freqs:Float32Array, mags:Float32Array, binHz:number}} bins 0..N/2
 */
export function spectrum(samples, sampleRate, fftSize) {
  const N = fftSize ? Math.min(floorPow2(fftSize), floorPow2(samples.length)) : floorPow2(samples.length);
  if (N < 2) return { freqs: new Float32Array(0), mags: new Float32Array(0), binHz: 0 };
  const w = hann(N);
  const re = new Float32Array(N), im = new Float32Array(N);
  for (let i = 0; i < N; i++) re[i] = (samples[i] || 0) * w[i];
  fft(re, im);
  const half = N / 2;
  const mags = new Float32Array(half), freqs = new Float32Array(half);
  const binHz = sampleRate / N;
  for (let i = 0; i < half; i++) { mags[i] = Math.hypot(re[i], im[i]) / half; freqs[i] = i * binHz; }
  return { freqs, mags, binHz };
}

/**
 * YIN fundamental-frequency estimator.
 * @returns {{hz:number, clarity:number, tau:number}} hz=0 when no pitch is found
 */
export function yinPitch(samples, sampleRate, opts = {}) {
  const threshold = opts.threshold ?? 0.1;
  const n = samples.length, tauMax = Math.floor(n / 2);
  if (tauMax < 2) return { hz: 0, clarity: 0, tau: 0 };
  const d = new Float32Array(tauMax);
  for (let tau = 1; tau < tauMax; tau++) {
    let sum = 0;
    for (let i = 0; i < tauMax; i++) { const diff = samples[i] - samples[i + tau]; sum += diff * diff; }
    d[tau] = sum;
  }
  const cmnd = new Float32Array(tauMax); cmnd[0] = 1;
  let running = 0;
  for (let tau = 1; tau < tauMax; tau++) { running += d[tau]; cmnd[tau] = running ? d[tau] * tau / running : 1; }
  let tau = -1;
  for (let t = 2; t < tauMax; t++) {
    if (cmnd[t] < threshold) { while (t + 1 < tauMax && cmnd[t + 1] < cmnd[t]) t++; tau = t; break; }
  }
  if (tau === -1) { let min = Infinity; for (let t = 2; t < tauMax; t++) if (cmnd[t] < min) { min = cmnd[t]; tau = t; } }
  if (tau <= 0) return { hz: 0, clarity: 0, tau: 0 };
  // parabolic interpolation for sub-sample tau
  let bt = tau;
  if (tau > 1 && tau < tauMax - 1) {
    const s0 = cmnd[tau - 1], s1 = cmnd[tau], s2 = cmnd[tau + 1];
    const denom = 2 * (2 * s1 - s2 - s0);
    if (denom !== 0) bt = tau + (s2 - s0) / denom;
  }
  return { hz: bt > 0 ? sampleRate / bt : 0, clarity: Math.max(0, Math.min(1, 1 - cmnd[tau])), tau: bt };
}

/**
 * Rising/falling-edge trigger index — the sample to start the trace at so the
 * waveform stands still (a real scope's stability). Returns 0 if no edge.
 */
export function detectTrigger(samples, opts = {}) {
  const level = opts.level ?? 0, edge = opts.edge ?? 'rising', holdoff = opts.holdoff ?? 0;
  const rising = edge !== 'falling';
  for (let i = Math.max(1, holdoff); i < samples.length; i++) {
    const a = samples[i - 1], b = samples[i];
    if (rising ? (a < level && b >= level) : (a > level && b <= level)) return i;
  }
  return 0;
}

// ── forensic measures (standalone, so it works without the voaice peer) ─────
export function rms(s) { let x = 0; for (let i = 0; i < s.length; i++) x += s[i] * s[i]; return Math.sqrt(x / s.length); }
export function peakToPeak(s) { let mn = Infinity, mx = -Infinity; for (let i = 0; i < s.length; i++) { if (s[i] < mn) mn = s[i]; if (s[i] > mx) mx = s[i]; } return mx - mn; }
export function zeroCrossingRate(s) { let z = 0; for (let i = 1; i < s.length; i++) if ((s[i - 1] < 0) !== (s[i] < 0)) z++; return z / s.length; }

/** Spectral centroid (Hz) — the "brightness" first moment of the spectrum. */
export function spectralCentroid(mags, freqs) {
  let num = 0, den = 0;
  for (let i = 0; i < mags.length; i++) { num += freqs[i] * mags[i]; den += mags[i]; }
  return den ? num / den : 0;
}
/** Spectral rolloff (Hz) — the frequency below which `pct` of energy sits. */
export function spectralRolloff(mags, freqs, pct = 0.85) {
  let total = 0; for (let i = 0; i < mags.length; i++) total += mags[i];
  const cut = total * pct; let run = 0;
  for (let i = 0; i < mags.length; i++) { run += mags[i]; if (run >= cut) return freqs[i]; }
  return freqs.length ? freqs[freqs.length - 1] : 0;
}
/** Harmonic-to-noise ratio (dB) from the normalised autocorrelation peak (Praat/Boersma). */
export function harmonicToNoiseRatio(samples, sampleRate, opts = {}) {
  const fmin = opts.fmin ?? 70, fmax = opts.fmax ?? 500;
  const minLag = Math.floor(sampleRate / fmax), maxLag = Math.floor(sampleRate / fmin);
  let r0 = 0; for (let i = 0; i < samples.length; i++) r0 += samples[i] * samples[i];
  if (r0 <= 0) return -Infinity;
  let best = 0;
  for (let lag = minLag; lag <= maxLag && lag < samples.length; lag++) {
    let r = 0; for (let i = 0; i + lag < samples.length; i++) r += samples[i] * samples[i + lag];
    const norm = r / r0; if (norm > best) best = norm;
  }
  best = Math.max(0, Math.min(0.9999, best));
  return best <= 0 ? -Infinity : 10 * Math.log10(best / (1 - best));
}

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
/** Nearest musical note + cents error (A4=440). */
export function freqToNote(hz) {
  if (!(hz > 0)) return { name: '—', octave: 0, cents: 0 };
  const midi = 69 + 12 * Math.log2(hz / 440);
  const round = Math.round(midi);
  const cents = Math.round((midi - round) * 100);
  return { name: NOTE_NAMES[((round % 12) + 12) % 12], octave: Math.floor(round / 12) - 1, cents };
}

/**
 * Map a frequency to a hue for the colour-coded spectrum — log-scaled across
 * the band so low→red, high→violet, spanning the audible range.
 */
export function freqColor(hz, fmin = 60, fmax = 12000) {
  if (!(hz > 0)) return 0;
  const t = Math.max(0, Math.min(1, Math.log2(hz / fmin) / Math.log2(fmax / fmin)));
  return Math.round(t * 300); // 0 (red) → 300 (violet)
}

/** The full measurement set the readout shows. */
export function measurements(samples, sampleRate) {
  const pitch = yinPitch(samples, sampleRate);
  const { mags, freqs } = spectrum(samples, sampleRate);
  return {
    f0: pitch.hz,
    clarity: pitch.clarity,
    period: pitch.hz > 0 ? 1000 / pitch.hz : 0, // ms
    vpp: peakToPeak(samples),
    vrms: rms(samples),
    zcr: zeroCrossingRate(samples),
    centroid: spectralCentroid(mags, freqs),
    rolloff: spectralRolloff(mags, freqs),
    hnr: harmonicToNoiseRatio(samples, sampleRate),
    note: freqToNote(pitch.hz),
  };
}

export default measurements;
