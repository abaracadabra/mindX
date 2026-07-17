/**
 * capture.js — accurate webcam → FAICE mapping.
 *
 * A single webcam frame is noisy: the landmarks jitter, the head is rarely
 * dead-on, and one bad frame skews everything. This accumulates frames over a
 * short window and folds them into ONE stable, pose-normalised face — the
 * person's actual geometry — then MEASURES how accurate that capture is, so the
 * FAICE it binds is honest about how well it matches the person.
 *
 * The pipeline:
 *   1. add(frame) each webcam frame (MediaPipe landmarks + transform matrix)
 *   2. aggregate() — pose-normalise every frame, weight by frontality, average
 *      per vertex (geometry.aggregate) → the stabilised face
 *   3. accuracy() — per-vertex spread across frames (jitter), mean frontality,
 *      and coverage → one 0..1 score. Low spread + frontal + enough frames =
 *      accurate. Not asserted — measured, the aivatar way.
 *   4. result() — { landmarks, faceprint, accuracy, frames } to BIND as the FAICE
 *
 * The captured landmarks live at the canonical MediaPipe topology, so the same
 * renderers, the 9-emotion expression system, and the mouth oscilloscope drive
 * the captured face exactly as they drive the neutral one — the avatar becomes
 * the person, and then expresses.
 *
 * © Professor Codephreak - rage.pythai.net
 */

import { aggregate, poseNormalize, frontality, proportions } from './geometry.js';
import { measureFaceprint } from './faceprint.js';

export class FaceCapture {
  /**
   * @param {{maxFrames?:number, minFrontality?:number}} [opts]
   *   maxFrames     — keep at most this many best frames (default 60)
   *   minFrontality — drop frames more turned than this (default 0.35)
   */
  constructor(opts = {}) {
    this.maxFrames = opts.maxFrames ?? 60;
    this.minFrontality = opts.minFrontality ?? 0.35;
    this.frames = [];
  }

  /** Feed one webcam frame: { landmarks:[{x,y,z}], matrix:number[16]|null }.
   *  Returns the running frame count (frames too turned to be useful are dropped). */
  add(frame) {
    if (!frame?.landmarks?.length) return this.frames.length;
    const f = frontality(frame.matrix);
    if (f < this.minFrontality) return this.frames.length; // too turned to trust
    this.frames.push({ landmarks: frame.landmarks, matrix: frame.matrix, frontality: f });
    // keep the most frontal maxFrames (a longer capture only improves the print)
    if (this.frames.length > this.maxFrames) {
      this.frames.sort((a, b) => b.frontality - a.frontality);
      this.frames.length = this.maxFrames;
    }
    return this.frames.length;
  }

  get count() { return this.frames.length; }
  reset() { this.frames = []; return this; }

  /** The stabilised, pose-normalised face (throws if nothing usable was captured). */
  aggregate() {
    return aggregate(this.frames);
  }

  /**
   * How accurate is this capture? Measures the three things that actually
   * determine it — not a guess:
   *   stability — mean per-vertex spread across pose-normalised frames (jitter);
   *               tight cluster ⇒ a confident geometry
   *   frontality — how face-on the frames were (a profile measures poorly)
   *   coverage  — enough frames to average the noise out
   * @returns {{score:number, stability:number, frontality:number, frames:number,
   *            perVertexSpread:number, verdict:string}}
   */
  accuracy() {
    const n = this.frames.length;
    if (!n) return { score: 0, stability: 0, frontality: 0, frames: 0, perVertexSpread: Infinity, verdict: 'no-capture' };

    // pose-normalise each frame into a common space, then measure per-vertex spread
    const normed = this.frames.map((f) => poseNormalize(f.landmarks, f.matrix));
    const V = normed[0].length;
    let spreadSum = 0;
    if (n >= 2) {
      for (let v = 0; v < V; v++) {
        let mx = 0, my = 0, mz = 0;
        for (const pts of normed) { mx += pts[v].x; my += pts[v].y; mz += pts[v].z; }
        mx /= n; my /= n; mz /= n;
        let s = 0;
        for (const pts of normed) s += (pts[v].x - mx) ** 2 + (pts[v].y - my) ** 2 + (pts[v].z - mz) ** 2;
        spreadSum += Math.sqrt(s / n);
      }
    }
    const perVertexSpread = n >= 2 ? spreadSum / V : 0;
    // map spread (in normalised face units) to a 0..1 stability: ~0 spread → 1,
    // 0.02 (2% of face size) → ~0.  Single frame gets a middling stability.
    const stability = n >= 2 ? Math.max(0, 1 - perVertexSpread / 0.02) : 0.5;
    const meanFrontality = this.frames.reduce((a, f) => a + f.frontality, 0) / n;
    const coverage = Math.min(1, n / 24); // ~24 good frames = full coverage

    const score = Math.max(0, Math.min(1, 0.5 * stability + 0.3 * meanFrontality + 0.2 * coverage));
    const verdict =
      score >= 0.85 ? 'accurate'
      : score >= 0.65 ? 'good'
      : score >= 0.4 ? 'rough'
      : 'insufficient';
    return { score, stability, frontality: meanFrontality, frames: n, perVertexSpread, verdict };
  }

  /**
   * The full result to bind as the FAICE: the stabilised face, its 18-dp
   * faceprint (with the measured accuracy folded into the print's precision),
   * and the accuracy report.
   * @returns {Promise<{landmarks:Array, faceprint:object, accuracy:object, frames:number}>}
   */
  async result() {
    const agg = this.aggregate();
    const acc = this.accuracy();
    // the capture accuracy IS the faceprint's confidence — a jittery capture
    // yields a lower-precision print, which grades to a lower tier in aivatar.
    const faceprint = await measureFaceprint(proportions(agg.landmarks), {
      confidence: acc.score,
      symmetry: 1,
      frontality: acc.frontality,
    });
    return { landmarks: agg.landmarks, faceprint, accuracy: acc, frames: this.frames.length };
  }
}

export default FaceCapture;
