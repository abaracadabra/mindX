/**
 * measure.js — the measurements that decide a persona's tier.
 *
 * Nothing here trusts a claim. Each function takes real artifacts (landmark
 * sets, audio samples) and returns a number the grader can act on. If a
 * measurement cannot be taken, it is `undefined` — NOT a flattering default.
 * `undefined` fails a gate, which is exactly right: unmeasured ≠ passed.
 *
 * © Professor Codephreak - rage.pythai.net
 */

/**
 * Geometric fidelity: RMSE between the cloned landmark set and the source
 * landmarks, in normalised face units (scale-invariant: both sets are centred
 * and divided by their own inter-ocular distance first).
 * @param {Array<{x:number,y:number,z:number}>} cloned
 * @param {Array<{x:number,y:number,z:number}>} source
 */
export function faceRmse(cloned, source) {
  if (!cloned?.length || !source?.length || cloned.length !== source.length) return undefined;
  const norm = (lms) => {
    const cx = lms.reduce((a, p) => a + p.x, 0) / lms.length;
    const cy = lms.reduce((a, p) => a + p.y, 0) / lms.length;
    const cz = lms.reduce((a, p) => a + (p.z || 0), 0) / lms.length;
    // scale by mean radial distance (a stable proxy for face size)
    let r = 0;
    for (const p of lms) r += Math.hypot(p.x - cx, p.y - cy, (p.z || 0) - cz);
    r = r / lms.length || 1;
    return lms.map((p) => ({ x: (p.x - cx) / r, y: (p.y - cy) / r, z: ((p.z || 0) - cz) / r }));
  };
  const a = norm(cloned);
  const b = norm(source);
  let acc = 0;
  for (let i = 0; i < a.length; i++) {
    acc += (a[i].x - b[i].x) ** 2 + (a[i].y - b[i].y) ** 2 + (a[i].z - b[i].z) ** 2;
  }
  return Math.sqrt(acc / a.length);
}

/**
 * Spectral distance between two clips — mean absolute difference of their
 * log-magnitude spectra (0 = identical, higher = further apart). Complements
 * voiceprint similarity: similarity compares six aggregate features, this
 * compares the whole spectral envelope.
 * @param {{samples:Float32Array,sampleRate:number}} a
 * @param {{samples:Float32Array,sampleRate:number}} b
 * @param {{fft:Function, hann:Function, magnitudeSpectrum:Function}} dsp voaice/fft
 */
export function spectralDistance(a, b, dsp) {
  if (!a?.samples?.length || !b?.samples?.length || !dsp) return undefined;
  const N = 2048;
  const avgSpec = (clip) => {
    const spec = new Float64Array(N / 2);
    let n = 0;
    for (let s = 0; s + N <= clip.samples.length; s += N) {
      const frame = clip.samples.subarray(s, s + N);
      const mag = dsp.magnitudeSpectrum(dsp.hann ? dsp.hann(Float32Array.from(frame)) : frame);
      for (let i = 0; i < spec.length && i < mag.length; i++) spec[i] += mag[i];
      n++;
    }
    if (!n) return null;
    for (let i = 0; i < spec.length; i++) spec[i] = Math.log10(1 + spec[i] / n);
    return spec;
  };
  const sa = avgSpec(a);
  const sb = avgSpec(b);
  if (!sa || !sb) return undefined;
  // normalise each to unit mean so loudness differences don't masquerade as timbre
  const m = (s) => s.reduce((x, y) => x + y, 0) / s.length || 1;
  const ma = m(sa);
  const mb = m(sb);
  let d = 0;
  for (let i = 0; i < sa.length; i++) d += Math.abs(sa[i] / ma - sb[i] / mb);
  return d / sa.length;
}

/** Seconds of usable (voiced) reference audio. */
export function referenceSeconds(clip, voicedRatioFn) {
  if (!clip?.samples?.length) return undefined;
  const total = clip.samples.length / clip.sampleRate;
  if (typeof voicedRatioFn !== 'function') return total;
  try {
    return total * voicedRatioFn(clip.samples, clip.sampleRate);
  } catch {
    return total;
  }
}

/**
 * Assemble the full measurement set the grader consumes. Every input is
 * optional; whatever cannot be measured stays `undefined` and fails its gate.
 */
export function measureAll({
  clonedLandmarks,
  sourceLandmarks,
  faceFrames,
  referenceClip,
  clonedClip,
  forensic, // voaice Forensic instance
  dsp, // voaice fft exports
  voicedRatioFn,
} = {}) {
  const out = {};
  if (faceFrames !== undefined) out.faceFrames = faceFrames;
  const rmse = faceRmse(clonedLandmarks, sourceLandmarks);
  if (rmse !== undefined) out.faceRmse = rmse;

  if (forensic && referenceClip?.samples?.length) {
    const refPrint = forensic.voiceprint(referenceClip.samples);
    out.voicePrecision = refPrint.precision;
    out.referenceSeconds = referenceSeconds(referenceClip, voicedRatioFn);
    if (typeof voicedRatioFn === 'function') {
      try {
        out.voicedRatio = voicedRatioFn(referenceClip.samples, referenceClip.sampleRate);
      } catch { /* unmeasured */ }
    }
    if (clonedClip?.samples?.length) {
      const clonePrint = forensic.voiceprint(clonedClip.samples);
      out.voiceSimilarity = forensic.constructor.compare(refPrint, clonePrint).similarity;
      const sd = spectralDistance(referenceClip, clonedClip, dsp);
      if (sd !== undefined) out.spectralDistance = sd;
      out.integrityClean = forensic.integrity(clonedClip.samples).verdict === 'clean';
    }
  }
  return out;
}

export default measureAll;
