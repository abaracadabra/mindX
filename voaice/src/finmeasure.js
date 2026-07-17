/**
 * finmeasure.js — quantitative-finance estimation, applied to voice measurement
 * for ACCURACY.
 *
 * A voice signal is a time series, and quant finance has the sharpest toolset
 * anywhere for measuring a noisy series *with a stated uncertainty*. Those exact
 * tools sharpen the scope's numbers:
 *
 *   • Kalman filter        — optimal estimate of a noisy scalar (the pitch track),
 *                            reducing variance frame-to-frame and reporting its own
 *                            uncertainty. The standard state estimator in quant.
 *   • standard error / CI  — the measurement's ± confidence interval (accuracy).
 *   • EWMA volatility       — RiskMetrics σ; on a pitch track this IS voice
 *                            JITTER; on amplitudes it IS SHIMMER — real
 *                            forensic/clinical voice measures.
 *   • moments (skew/kurt)  — the distribution shape of the samples.
 *   • Bollinger bands      — mean ± k·σ envelope for the pitch track.
 *   • z-score / outliers   — anomaly detection (a splice reads as an outlier).
 *
 * Nothing here is decorative: a Kalman-smoothed pitch with a 95% CI is a more
 * accurate, more honest number than a raw per-frame estimate. Pure, headless-
 * tested; the sci-fi HUD that displays it lives in the demo.
 *
 * © Professor Codephreak - rage.pythai.net
 */

// ── moments ─────────────────────────────────────────────────────────────────
export function mean(x) { if (!x.length) return 0; let s = 0; for (let i = 0; i < x.length; i++) s += x[i]; return s / x.length; }
export function variance(x, sample = true) {
  const n = x.length; if (n < 2) return 0;
  const m = mean(x); let s = 0; for (let i = 0; i < n; i++) s += (x[i] - m) ** 2;
  return s / (sample ? n - 1 : n);
}
export function stddev(x, sample = true) { return Math.sqrt(variance(x, sample)); }
export function skewness(x) {
  const n = x.length; if (n < 3) return 0;
  const m = mean(x), sd = stddev(x, false); if (sd === 0) return 0;
  let s = 0; for (let i = 0; i < n; i++) s += ((x[i] - m) / sd) ** 3;
  return s / n;
}
/** Raw kurtosis (normal ≈ 3); subtract 3 for excess. */
export function kurtosis(x) {
  const n = x.length; if (n < 4) return 0;
  const m = mean(x), sd = stddev(x, false); if (sd === 0) return 0;
  let s = 0; for (let i = 0; i < n; i++) s += ((x[i] - m) / sd) ** 4;
  return s / n;
}

// ── EWMA (RiskMetrics) ──────────────────────────────────────────────────────
export function ewma(x, lambda = 0.94) {
  if (!x.length) return 0;
  let s = x[0]; for (let i = 1; i < x.length; i++) s = lambda * s + (1 - lambda) * x[i];
  return s;
}
/** EWMA volatility of the series' first differences (σ, RiskMetrics form). */
export function ewmaVol(x, lambda = 0.94) {
  if (x.length < 2) return 0;
  let v = (x[1] - x[0]) ** 2;
  for (let i = 2; i < x.length; i++) v = lambda * v + (1 - lambda) * (x[i] - x[i - 1]) ** 2;
  return Math.sqrt(v);
}

// ── uncertainty: standard error + confidence interval ───────────────────────
export function standardError(x) { const n = x.length; return n ? stddev(x) / Math.sqrt(n) : 0; }
/** {mean, se, lo, hi, ci} at a z multiplier (1.96 ≈ 95%). */
export function confidenceInterval(x, z = 1.96) {
  const m = mean(x), se = standardError(x), ci = z * se;
  return { mean: m, se, ci, lo: m - ci, hi: m + ci };
}

// ── Kalman filter (1-D random-walk model): optimal noisy-scalar estimate ─────
export class Kalman {
  constructor(opts = {}) {
    this.q = opts.q ?? 1e-3;   // process noise (how fast the truth can move)
    this.r = opts.r ?? 0.08;   // measurement noise (how noisy each reading is)
    this.x = opts.x ?? 0;      // state estimate
    this.p = opts.p ?? 1;      // estimate variance
    this._init = false;
  }
  /** Fold in a measurement z → {x (estimate), p (variance), std}. */
  update(z) {
    if (!this._init) { this.x = z; this._init = true; return { x: this.x, p: this.p, std: Math.sqrt(this.p) }; }
    this.p += this.q;                         // predict
    const k = this.p / (this.p + this.r);     // Kalman gain
    this.x += k * (z - this.x);               // correct
    this.p *= (1 - k);
    return { x: this.x, p: this.p, std: Math.sqrt(this.p) };
  }
  reset() { this._init = false; this.p = 1; this.x = 0; }
}

// ── voice jitter / shimmer = volatility of the pitch / amplitude track ──────
/** Relative average perturbation (local jitter/shimmer), as a fraction. */
export function relativePerturbation(series) {
  const x = series.filter((v) => v > 0);
  if (x.length < 2) return 0;
  let d = 0; for (let i = 1; i < x.length; i++) d += Math.abs(x[i] - x[i - 1]);
  const avg = mean(x);
  return avg ? (d / (x.length - 1)) / avg : 0;
}
export const jitter = (f0Series) => relativePerturbation(f0Series);   // period/F0 perturbation
export const shimmer = (ampSeries) => relativePerturbation(ampSeries); // amplitude perturbation

// ── Bollinger bands: mean ± k·σ envelope ────────────────────────────────────
export function bollinger(x, k = 2, lambda = 0.94) {
  const mid = ewma(x, lambda), vol = ewmaVol(x, lambda);
  return { mid, upper: mid + k * vol, lower: mid - k * vol, width: 2 * k * vol };
}

// ── z-score / outliers: statistical anomaly (splice) detection ──────────────
export function zScore(v, m, sd) { return sd > 0 ? (v - m) / sd : 0; }
export function outliers(x, k = 3) {
  const m = mean(x), sd = stddev(x); const out = [];
  if (sd === 0) return out;
  for (let i = 0; i < x.length; i++) if (Math.abs((x[i] - m) / sd) > k) out.push(i);
  return out;
}

/** Lag-`lag` autocorrelation (persistence): 1 = perfectly correlated. */
export function autocorr(x, lag = 1) {
  const n = x.length; if (n <= lag) return 0;
  const m = mean(x); let num = 0, den = 0;
  for (let i = 0; i < n; i++) den += (x[i] - m) ** 2;
  for (let i = 0; i < n - lag; i++) num += (x[i] - m) * (x[i + lag] - m);
  return den ? num / den : 0;
}

// ── EVM 18-decimal precision (matches faceprint.js / Scientific.js / SoundWave) ─
export const ONE18 = 10n ** 18n; // 18-decimal fixed-point scale
/** Non-negative real → 18-dp fixed-point BigInt (real × 1e18), 9 real decimals kept then padded. */
export function toFixed18(v) {
  if (!isFinite(v) || v < 0) v = 0;
  return BigInt(Math.round(Math.abs(v) * 1e9)) * 10n ** 9n;
}
/**
 * SIGNED 18-decimal fixed-point string — accuracy carried to conventional EVM
 * 18 decimals (finance measures like skewness / z-score can be negative, so the
 * sign is preserved). e.g. 220.14 → "220.140000000000000000", −0.5 → "-0.5000…".
 */
export function toFixed18Str(v) {
  if (!isFinite(v)) v = 0;
  const neg = v < 0;
  const scaled = BigInt(Math.round(Math.abs(v) * 1e9)) * 10n ** 9n; // 18-dp magnitude (carry-safe)
  const whole = scaled / ONE18, frac = scaled % ONE18;
  return (neg ? '-' : '') + whole.toString() + '.' + frac.toString().padStart(18, '0');
}
export const fromFixed18 = (x) => Number(x) / 1e18;

/**
 * The accuracy readout as an 18-dp measurement record — Kalman-stabilised
 * frequency ± confidence interval, jitter, shimmer, all at EVM precision. This
 * is the number that can travel on-chain / into a voiceprint alongside the rest.
 */
export function accuracy18({ f0, ci, jitter: j, shimmer: sh, clarity }) {
  return {
    f0_hz: toFixed18Str(f0 ?? 0),
    ci95_hz: toFixed18Str(ci ?? 0),
    jitter_pct: toFixed18Str((j ?? 0) * 100),
    shimmer_pct: toFixed18Str((sh ?? 0) * 100),
    clarity: toFixed18Str(clarity ?? 0),
    precision_decimals: 18,
  };
}

export default Kalman;
