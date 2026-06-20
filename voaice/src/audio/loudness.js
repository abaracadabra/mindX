/**
 * loudness.js — ITU-R BS.1770-4 loudness (LUFS) measurement + normalisation.
 *
 * A dependency-free port of the pyloudnorm approach: K-weight the signal (a high-shelf
 * "head" filter + a high-pass RLB filter), measure mean-square energy over 400 ms blocks with
 * 75% overlap, apply the absolute (-70 LUFS) and relative (-10 LU) gates, and integrate.
 * `normalizeToLufs` then shifts a clip to a target integrated loudness — used to bring TTS
 * output and reference clips to a consistent level (consistent input makes cloning steadier).
 *
 * The K-weighting biquads use the canonical coefficients designed at 48 kHz (as pyloudnorm
 * ships them); applied at other sample rates this is a well-accepted approximation, and for
 * *relative* normalisation (measure → shift to target) the small absolute bias cancels.
 *
 *   import { integratedLoudness, normalizeToLufs } from 'voaice/wav'  // re-exported via index
 */

// Stage 1: high-shelf "pre" filter (BS.1770 head). 48 kHz design.
const PRE_B = [1.53512485958697, -2.69169618940638, 1.19839281085285];
const PRE_A = [1.0, -1.69065929318241, 0.73248077421585];
// Stage 2: RLB high-pass. 48 kHz design.
const HP_B = [1.0, -2.0, 1.0];
const HP_A = [1.0, -1.99004745483398, 0.99007225036621];

/** Direct-form-I biquad over a Float array (a[0] assumed 1). */
function biquad(x, b, a) {
  const y = new Float64Array(x.length);
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) {
    const xi = x[i];
    const yi = b[0] * xi + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2;
    y[i] = yi;
    x2 = x1; x1 = xi;
    y2 = y1; y1 = yi;
  }
  return y;
}

/** K-weight a mono signal (the two BS.1770 stages in series). */
export function kWeight(samples) {
  return biquad(biquad(samples, PRE_B, PRE_A), HP_B, HP_A);
}

/**
 * Integrated loudness in LUFS for a mono signal, with BS.1770-4 gating.
 * @param {Float32Array|number[]} samples
 * @param {number} sampleRate
 * @returns {number} integrated loudness (LUFS); -Infinity for silence
 */
export function integratedLoudness(samples, sampleRate) {
  if (!samples.length) return -Infinity;
  const k = kWeight(samples);
  const blockLen = Math.round(0.4 * sampleRate); // 400 ms gating block
  const step = Math.round(blockLen / 4); // 75% overlap
  if (k.length < blockLen) return -Infinity;

  // per-block mean square + provisional block loudness
  const ms = [];
  for (let start = 0; start + blockLen <= k.length; start += step) {
    let sum = 0;
    for (let i = start; i < start + blockLen; i++) sum += k[i] * k[i];
    ms.push(sum / blockLen);
  }
  if (!ms.length) return -Infinity;

  // BS.1770 loudness of a mean square: -0.691 + 10*log10(ms)
  const loud = (m) => (m > 0 ? -0.691 + 10 * Math.log10(m) : -Infinity);

  // absolute gate at -70 LUFS
  const absKept = ms.filter((m) => loud(m) > -70);
  if (!absKept.length) return -Infinity;

  // relative gate: mean of abs-gated blocks minus 10 LU
  const meanMs = absKept.reduce((a, b) => a + b, 0) / absKept.length;
  const relThresh = loud(meanMs) - 10;
  const relKept = absKept.filter((m) => loud(m) > relThresh);
  const kept = relKept.length ? relKept : absKept;

  const finalMs = kept.reduce((a, b) => a + b, 0) / kept.length;
  return loud(finalMs);
}

/** Peak absolute sample value. */
export function peak(samples) {
  let p = 0;
  for (let i = 0; i < samples.length; i++) {
    const a = Math.abs(samples[i]);
    if (a > p) p = a;
  }
  return p;
}

/**
 * Normalise a clip to a target integrated loudness (LUFS), with peak protection so the gain
 * never clips. Returns a new Float32Array; silent input is returned unchanged.
 * @param {Float32Array|number[]} samples
 * @param {number} sampleRate
 * @param {number} [targetLufs=-23] EBU R128 broadcast default; -16 for podcast/loud
 * @param {number} [maxPeak=0.97]
 * @returns {Float32Array}
 */
export function normalizeToLufs(samples, sampleRate, targetLufs = -23, maxPeak = 0.97) {
  const current = integratedLoudness(samples, sampleRate);
  const out = Float32Array.from(samples);
  if (!isFinite(current)) return out; // silence / too short to gate
  let gain = Math.pow(10, (targetLufs - current) / 20);
  const pk = peak(samples);
  if (pk * gain > maxPeak) gain = maxPeak / Math.max(pk, 1e-9);
  for (let i = 0; i < out.length; i++) out[i] *= gain;
  return out;
}
