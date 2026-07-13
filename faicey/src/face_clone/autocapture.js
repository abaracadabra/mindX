/**
 * autocapture.js — guided, hands-free webcam capture for face cloning.
 *
 * A pure state machine: feed it the facial transformation matrix from each
 * live frame (FaceLandmarkerClient.detectVideoFrame) and it decides WHEN to
 * snap the three clone angles (front / left / right) — pose must sit inside
 * the target band and HOLD there for `holdFrames` consecutive frames, so we
 * never capture mid-turn motion blur.
 *
 * Sign-convention agnostic: "left" is simply the first side captured; "right"
 * is the opposite yaw sign. Mirrored preview, camera handedness, none of it
 * matters — only |yaw| bands and sign OPPOSITION do.
 *
 *   const ac = new AutoCapture();
 *   // per frame:
 *   const step = ac.update(frame ? frame.matrix : null);
 *   ui.say(step.instruction);
 *   if (step.capture) snapshots.push({ a: step.capture, canvas: grab() });
 *   if (ac.done) engine.cloneFromPerspectives(snapshots.map(s => s.canvas));
 *
 * No DOM, no MediaPipe imports — runs (and is tested) under plain Node.
 *
 * © Professor Codephreak - rage.pythai.net
 */

/** Signed yaw (radians) from a MediaPipe 4×4 facial transformation matrix. */
export function yawOf(matrix) {
  if (!matrix || matrix.length < 16) return null;
  return Math.atan2(matrix[8], matrix[10]);
}

/** Signed pitch (radians) — same rotation block as geometry.frontality. */
export function pitchOf(matrix) {
  if (!matrix || matrix.length < 16) return null;
  return Math.atan2(matrix[9], matrix[10]);
}

export class AutoCapture {
  /**
   * @param {{holdFrames?:number, frontMax?:number, sideMin?:number, sideMax?:number, pitchMax?:number}} [opts]
   *   holdFrames — consecutive in-band frames required before a snap (default 6)
   *   frontMax   — |yaw| ≤ this counts as front (default 0.12 rad ≈ 7°)
   *   sideMin/Max— side band (default 0.28–0.90 rad ≈ 16–52°)
   *   pitchMax   — |pitch| gate for any capture (default 0.35 rad ≈ 20°)
   */
  constructor(opts = {}) {
    this.holdFrames = opts.holdFrames ?? 6;
    this.frontMax = opts.frontMax ?? 0.12;
    this.sideMin = opts.sideMin ?? 0.28;
    this.sideMax = opts.sideMax ?? 0.9;
    this.pitchMax = opts.pitchMax ?? 0.35;
    this.reset();
  }

  reset() {
    this.captured = {}; // front|left|right -> yaw at capture
    this._sideSign = 0; // sign of the FIRST captured side (defines "left")
    this._hold = 0;
    this._holdSlot = null;
    return this;
  }

  get done() {
    return !!(this.captured.front !== undefined
      && this.captured.left !== undefined
      && this.captured.right !== undefined);
  }

  get needed() {
    return ['front', 'left', 'right'].filter((k) => this.captured[k] === undefined);
  }

  /** Which slot would the current yaw fill, or null. */
  _slotFor(yaw) {
    const a = Math.abs(yaw);
    if (a <= this.frontMax) return this.captured.front === undefined ? 'front' : null;
    if (a >= this.sideMin && a <= this.sideMax) {
      const sign = Math.sign(yaw) || 1;
      if (this._sideSign === 0) {
        // first side seen becomes "left" (convention-free)
        return this.captured.left === undefined ? 'left' : null;
      }
      if (sign === this._sideSign) return this.captured.left === undefined ? 'left' : null;
      return this.captured.right === undefined ? 'right' : null;
    }
    return null;
  }

  _instruction(yaw) {
    if (this.done) return 'all three angles captured ✓';
    const need = this.needed;
    if (yaw === null) return 'no face detected — center yourself in the frame';
    if (need.includes('front') && Math.abs(yaw) <= this.frontMax) return 'hold still… capturing FRONT';
    if (need.includes('front')) return 'face the camera straight on';
    if (this._sideSign === 0) return 'now turn your head to ONE side and hold';
    const wantSign = need.includes('left') ? this._sideSign : -this._sideSign;
    const same = Math.sign(yaw) === wantSign && Math.abs(yaw) >= this.sideMin;
    if (same && Math.abs(yaw) <= this.sideMax) return `hold still… capturing ${need[0].toUpperCase()}`;
    if (need.includes('left') && need.includes('right')) return 'turn your head to one side and hold';
    return 'now turn your head the OTHER way and hold';
  }

  /**
   * Feed one frame's matrix (or null when no face). Returns the step state;
   * `capture` is non-null exactly once per successful slot.
   */
  update(matrix) {
    const yaw = yawOf(matrix);
    const pitch = pitchOf(matrix);
    let capture = null;

    const inPitch = pitch !== null && Math.abs(pitch) <= this.pitchMax;
    const slot = yaw !== null && inPitch && !this.done ? this._slotFor(yaw) : null;

    if (slot && slot === this._holdSlot) {
      this._hold++;
      if (this._hold >= this.holdFrames) {
        this.captured[slot] = yaw;
        if (slot !== 'front' && this._sideSign === 0) this._sideSign = Math.sign(yaw) || 1;
        capture = slot;
        this._hold = 0;
        this._holdSlot = null;
      }
    } else {
      this._holdSlot = slot;
      this._hold = slot ? 1 : 0;
    }

    return {
      yaw,
      pitch,
      slot,
      capture,
      done: this.done,
      needed: this.needed,
      hold: this._holdSlot ? this._hold / this.holdFrames : 0,
      instruction: this._instruction(yaw),
    };
  }
}

export default AutoCapture;
