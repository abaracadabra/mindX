/**
 * face_clone_engine.js — clone a FACE from a single image, perspective images, or a video clip.
 *
 * The visual sibling of voaice's NeuralVoiceEngine: where voaice clones a VOICE from a reference
 * clip and yields a forensic 18-dp voiceprint, this clones a FACE from reference image(s)/video and
 * yields a forensic 18-dp FACEPRINT plus cloned facial proportions that drive the faicey wireframe.
 *
 * Detection is pluggable so the engine is testable in Node: pass image/video elements and it uses
 * the lazy MediaPipe client; OR pass pre-detected frames `{ landmarks, matrix?, confidence? }` and
 * it skips detection entirely. Either way it pose-normalises, aggregates multi/video frames,
 * derives proportions, and measures the faceprint.
 *
 *   const eng = await new FaceCloneEngine().init();
 *   const profile = await eng.cloneFromImage(imgEl);              // single
 *   const profile = await eng.cloneFromPerspectives([f, l, r]);   // multi-angle
 *   const profile = await eng.cloneFromVideo(videoEl);            // clip (samples frames)
 *   // profile.proportions → wireframe clone; profile.faceprint → registerable identity
 */

import { proportions, aggregate, symmetry, frontality, poseNormalize } from './geometry.js';
import { measureFaceprint, toRegisterArgs, faceprintDistance, FACEPRINT_MEASURES } from './faceprint.js';
import { FaceLandmarkerClient } from './landmarks.js';

export class FaceCloneEngine {
  /** @param {{ landmarker?:FaceLandmarkerClient, videoSampleFps?:number, maxVideoFrames?:number }} [opts] */
  constructor(opts = {}) {
    this.landmarker = opts.landmarker || new FaceLandmarkerClient(opts);
    this.videoSampleFps = opts.videoSampleFps || 4;   // sample 4 frames/sec of video
    this.maxVideoFrames = opts.maxVideoFrames || 24;
    this.capability = { mediapipe: false };
    this._clones = new Map(); // faceprint hash -> FaceProfile (in-process store)
  }

  /** Probe the landmark detector. Never throws. */
  async init() {
    try {
      this.capability.mediapipe = await this.landmarker.available();
    } catch {
      this.capability.mediapipe = false;
    }
    return this;
  }

  /** A frame is either already-detected `{landmarks,...}` or an image to run through MediaPipe. */
  async _toFrame(input) {
    if (input && Array.isArray(input.landmarks)) return input; // pre-detected (test/Node path)
    const frame = await this.landmarker.detect(input);
    if (!frame) throw new Error('face_clone: no face detected in the supplied image');
    return frame;
  }

  /** Build a FaceProfile from one or more frames (aggregated). */
  async _profile(frames, source) {
    const agg = aggregate(frames);
    const lms = agg.landmarks;
    const props = proportions(lms);
    const sym = symmetry(lms);
    const conf = frames.reduce((a, f) => a + (f.confidence ?? 1), 0) / frames.length;
    const faceprint = await measureFaceprint(props, { confidence: conf, symmetry: sym, frontality: agg.meanFrontality });
    const profile = {
      source,
      frames: agg.frames,
      frontalIndex: agg.frontalIndex,
      proportions: props,
      landmarks: lms,                 // pose-normalised, aggregated (drives the wireframe clone)
      quality: { symmetry: sym, confidence: conf, frontality: agg.meanFrontality },
      faceprint,
      faceprintId: faceprint.hash.slice(0, 18),
      registerArgs: toRegisterArgs(faceprint),
    };
    this._clones.set(faceprint.hash, profile);
    return profile;
  }

  /** Clone from a SINGLE image (or a single pre-detected frame). */
  async cloneFromImage(input) {
    const frame = await this._toFrame(input);
    return this._profile([frame], 'single-image');
  }

  /** Clone from MULTIPLE perspective images (different angles → better 3D + denoised). */
  async cloneFromPerspectives(inputs) {
    if (!Array.isArray(inputs) || !inputs.length) throw new Error('face_clone: need an array of images');
    const frames = [];
    for (const input of inputs) {
      try { frames.push(await this._toFrame(input)); } catch { /* skip undetected angles */ }
    }
    if (!frames.length) throw new Error('face_clone: no face detected in any perspective image');
    return this._profile(frames, `perspectives(${frames.length})`);
  }

  /**
   * Clone from a VIDEO clip. Accepts an HTMLVideoElement (samples frames via the VIDEO-mode
   * landmarker) or an array of pre-detected frames (test/Node path).
   */
  async cloneFromVideo(input) {
    let frames;
    if (Array.isArray(input)) {
      frames = input;
    } else {
      frames = await this._sampleVideo(input);
    }
    const valid = frames.filter(Boolean);
    if (!valid.length) throw new Error('face_clone: no face detected in the video');
    // Recognition: keep only frames that are the SAME person (consistent geometry), dropping
    // outlier frames (a different face, or a bad detection) so the clone is of one recognized person.
    const { kept, dropped } = this._recognizeConsistent(valid);
    const profile = await this._profile(kept, `video(${kept.length}/${valid.length}f)`);
    profile.recognition = { person: 'consistent', recognizedFrames: kept.length, droppedFrames: dropped };
    return profile;
  }

  /**
   * Filter frames to one consistent identity: compute each frame's faceprint ratio vector, take the
   * per-dimension median, and keep frames within `threshold` L2 of it. Drops a different person / bad
   * detections. Pure geometry — the faceprint IS the recognition token.
   */
  _recognizeConsistent(frames, threshold = 0.18) {
    if (frames.length < 3) return { kept: frames, dropped: 0 };
    const vecs = frames.map((f) => FACEPRINT_MEASURES.map((k) => Number(proportions(f.landmarks)[k]) || 0));
    const median = FACEPRINT_MEASURES.map((_, d) => {
      const col = vecs.map((v) => v[d]).sort((a, b) => a - b);
      return col[col.length >> 1];
    });
    const dist = (v) => Math.sqrt(v.reduce((s, x, i) => s + (x - median[i]) ** 2, 0));
    const kept = frames.filter((_, i) => dist(vecs[i]) <= threshold);
    return { kept: kept.length ? kept : frames, dropped: frames.length - (kept.length || frames.length) };
  }

  /** Sample a video element at videoSampleFps, detecting each frame (browser path). */
  async _sampleVideo(video) {
    const duration = video.duration || 0;
    const step = 1 / this.videoSampleFps;
    const frames = [];
    for (let t = 0; t < duration && frames.length < this.maxVideoFrames; t += step) {
      await seek(video, t);
      const f = await this.landmarker.detectVideoFrame(video, Math.round(t * 1000));
      if (f) frames.push(f);
    }
    return frames;
  }

  /** Same-person check between two profiles (L2 on the faceprint ratio vectors). */
  static match(a, b, threshold = 0.15) {
    const dist = faceprintDistance(a.faceprint, b.faceprint);
    return { distance: dist, same: dist <= threshold };
  }
}

function seek(video, t) {
  return new Promise((resolve) => {
    const on = () => { video.removeEventListener('seeked', on); resolve(); };
    video.addEventListener('seeked', on);
    video.currentTime = t;
  });
}

export { FACEPRINT_MEASURES, poseNormalize, frontality };
