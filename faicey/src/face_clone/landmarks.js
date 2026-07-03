/**
 * landmarks.js — lazy MediaPipe Face Landmarker loader (the torch-free, CPU/WASM geometry source).
 *
 * Wraps `@mediapipe/tasks-vision` FaceLandmarker (Apache-2.0, TFLite/WASM — no torch, no Python).
 * It emits 478 3D landmarks + a 4×4 facial transformation matrix + 52 ARKit blendshapes per image,
 * for single images (`detect`), perspective sets (`detect` ×N) and video (`detectForVideo`).
 *
 * Doctrine: the WASM fileset and the model bundle (`face_landmarker.task`, ~3.7 MB) are vendored
 * locally (no CDN) under static/vendor/mediapipe/. The dependency is OPTIONAL and loaded lazily —
 * absent it (or in Node without the WASM), the clone engine still computes a faceprint from any
 * landmarks supplied directly. This mirrors voaice's optional onnxruntime/sherpa backends.
 */

let _vision = null;
let _probed = false;

/** Lazily resolve @mediapipe/tasks-vision, or null if not installed. */
export async function tryLoadVision() {
  if (_probed) return _vision;
  _probed = true;
  try {
    _vision = await import('@mediapipe/tasks-vision');
  } catch {
    _vision = null;
  }
  return _vision;
}

export class FaceLandmarkerClient {
  /**
   * @param {{ wasmDir?:string, modelPath?:string, numFaces?:number }} [opts]
   *   wasmDir   — vendored MediaPipe WASM fileset dir (default static/vendor/mediapipe/wasm)
   *   modelPath — vendored face_landmarker.task (default static/vendor/mediapipe/face_landmarker.task)
   */
  constructor(opts = {}) {
    this.wasmDir = opts.wasmDir || '/static/vendor/mediapipe/wasm';
    this.modelPath = opts.modelPath || '/static/vendor/mediapipe/face_landmarker.task';
    this.numFaces = opts.numFaces || 1;
    this.imageLm = null;
    this.videoLm = null;
  }

  async available() {
    return !!(await tryLoadVision());
  }

  async _create(runningMode) {
    const vision = await tryLoadVision();
    if (!vision) throw new Error('face_clone: @mediapipe/tasks-vision not installed (vendor it under static/vendor/mediapipe).');
    const fileset = await vision.FilesetResolver.forVisionTasks(this.wasmDir);
    return vision.FaceLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: this.modelPath },
      runningMode,
      numFaces: this.numFaces,
      outputFaceBlendshapes: true,
      outputFacialTransformationMatrixes: true,
    });
  }

  /** Normalise a MediaPipe result into our frame shape. */
  _frame(result) {
    if (!result || !result.faceLandmarks || !result.faceLandmarks.length) return null;
    const landmarks = result.faceLandmarks[0].map((p) => ({ x: p.x, y: p.y, z: p.z }));
    const matrix = result.facialTransformationMatrixes && result.facialTransformationMatrixes[0]
      ? result.facialTransformationMatrixes[0].data
      : null;
    const blendshapes = result.faceBlendshapes && result.faceBlendshapes[0]
      ? result.faceBlendshapes[0].categories
      : null;
    return { landmarks, matrix, blendshapes, confidence: 1 };
  }

  /** Detect one still image (HTMLImageElement / ImageBitmap / canvas). */
  async detect(image) {
    if (!this.imageLm) this.imageLm = await this._create('IMAGE');
    return this._frame(this.imageLm.detect(image));
  }

  /** Detect one video frame at a timestamp (ms). Reuses a VIDEO-mode landmarker. */
  async detectVideoFrame(frame, timestampMs) {
    if (!this.videoLm) this.videoLm = await this._create('VIDEO');
    return this._frame(this.videoLm.detectForVideo(frame, timestampMs));
  }
}
