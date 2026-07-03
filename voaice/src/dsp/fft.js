/**
 * fft.js — in-house radix-2 Cooley–Tukey FFT and spectral helpers.
 *
 * Zero external dependencies. This is the DSP floor for voaice's spectrometer and
 * frequency manipulation, so an isolated build needs nothing but Node to analyse
 * audio. (meyda/audiomotion remain OPTIONAL accelerators, never required.)
 */

/** Next power of two >= n. */
export function nextPow2(n) {
  let p = 1;
  while (p < n) p <<= 1;
  return p;
}

/**
 * In-place iterative radix-2 FFT.
 * @param {Float64Array|number[]} re real part (length must be a power of two)
 * @param {Float64Array|number[]} im imaginary part (same length; zero-filled for real input)
 */
export function fft(re, im) {
  const n = re.length;
  if (n <= 1) return;
  if ((n & (n - 1)) !== 0) throw new Error(`fft: length ${n} is not a power of two`);

  // bit-reversal permutation
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }

  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wRe = Math.cos(ang);
    const wIm = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let curRe = 1;
      let curIm = 0;
      for (let k = 0; k < len / 2; k++) {
        const aRe = re[i + k];
        const aIm = im[i + k];
        const bRe = re[i + k + len / 2] * curRe - im[i + k + len / 2] * curIm;
        const bIm = re[i + k + len / 2] * curIm + im[i + k + len / 2] * curRe;
        re[i + k] = aRe + bRe;
        im[i + k] = aIm + bIm;
        re[i + k + len / 2] = aRe - bRe;
        im[i + k + len / 2] = aIm - bIm;
        const nextRe = curRe * wRe - curIm * wIm;
        curIm = curRe * wIm + curIm * wRe;
        curRe = nextRe;
      }
    }
  }
}

/** Hann window in place (reduces spectral leakage). */
export function hann(samples) {
  const n = samples.length;
  for (let i = 0; i < n; i++) {
    samples[i] *= 0.5 * (1 - Math.cos((2 * Math.PI * i) / (n - 1)));
  }
  return samples;
}

/**
 * Magnitude spectrum of a real signal.
 * @param {number[]|Float32Array} signal time-domain samples
 * @param {{window?: boolean}} [opts]
 * @returns {Float64Array} magnitudes for bins 0..N/2 (N = next pow2)
 */
export function magnitudeSpectrum(signal, opts = {}) {
  const n = nextPow2(signal.length);
  const re = new Float64Array(n);
  const im = new Float64Array(n);
  for (let i = 0; i < signal.length; i++) re[i] = signal[i];
  if (opts.window !== false) hann(re);
  fft(re, im);
  const half = n >> 1;
  const mag = new Float64Array(half);
  for (let i = 0; i < half; i++) mag[i] = Math.hypot(re[i], im[i]) / half;
  return mag;
}

/** Convert an FFT bin index to its centre frequency in Hz. */
export function binToHz(bin, sampleRate, fftSize) {
  return (bin * sampleRate) / fftSize;
}
