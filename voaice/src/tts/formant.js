/**
 * formant.js — clean-room formant text-to-speech (model-free, node + browser).
 *
 * Real, intelligible (retro/robotic) speech with NO model download — a source-filter synthesizer
 * in the Klatt tradition: a voiced glottal pulse train (or noise) excites a cascade of digital
 * formant resonators, with a phoneme→formant table, a compact English letter-to-sound front-end,
 * an F0 contour, and coarticulation between segments. text → Float32Array PCM.
 *
 * Clean-room provenance: built from PUBLIC-DOMAIN references only — Dennis Klatt's 1980 JASA
 * cascade/parallel formant design and the standard Peterson–Barney vowel-formant table. No GPL
 * espeak/gnuspeech source and no abandonware SAM code was read or copied. This is voaice's own code.
 *
 *   import { FormantTTS } from 'voaice/formant'   // or src/tts/formant.js
 *   const tts = new FormantTTS({ sampleRate: 24000, f0: 120 });
 *   const samples = tts.synthesize('hello, I am a voice');   // Float32Array in [-1,1]
 */

// ── phoneme inventory ──
// Vowels: [F1, F2, F3] (Hz, Peterson–Barney averages); diphthongs interpolate two targets.
const VOWELS = {
  iy: [270, 2290, 3010], ih: [390, 1990, 2550], eh: [530, 1840, 2480], ae: [660, 1720, 2410],
  aa: [730, 1090, 2440], ao: [570, 840, 2410], uh: [440, 1020, 2240], uw: [300, 870, 2240],
  er: [490, 1350, 1690], ax: [640, 1190, 2390], // schwa
  // diphthongs as [startVowel, endVowel]
  ey: ['eh', 'iy'], ay: ['aa', 'iy'], oy: ['ao', 'iy'], ow: ['ax', 'uw'], aw: ['aa', 'uw'],
};
// Consonants: { voiced, manner, f:[F1,F2,F3]?, noise:{f,bw,level}?, dur }
const CONS = {
  m: { voiced: 1, manner: 'nasal', f: [250, 1100, 2100], dur: 0.07 },
  n: { voiced: 1, manner: 'nasal', f: [250, 1700, 2600], dur: 0.07 },
  ng: { voiced: 1, manner: 'nasal', f: [250, 2300, 2700], dur: 0.08 },
  l: { voiced: 1, manner: 'approx', f: [360, 1300, 2700], dur: 0.06 },
  r: { voiced: 1, manner: 'approx', f: [490, 1350, 1690], dur: 0.06 },
  w: { voiced: 1, manner: 'approx', f: [300, 610, 2200], dur: 0.06 },
  y: { voiced: 1, manner: 'approx', f: [270, 2290, 3010], dur: 0.05 },
  s: { voiced: 0, manner: 'fric', noise: { f: 6000, bw: 1500, level: 0.5 }, dur: 0.09 },
  sh: { voiced: 0, manner: 'fric', noise: { f: 3000, bw: 1200, level: 0.55 }, dur: 0.09 },
  f: { voiced: 0, manner: 'fric', noise: { f: 1800, bw: 2500, level: 0.35 }, dur: 0.08 },
  th: { voiced: 0, manner: 'fric', noise: { f: 5500, bw: 3000, level: 0.3 }, dur: 0.08 },
  h: { voiced: 0, manner: 'fric', noise: { f: 1500, bw: 3000, level: 0.25 }, dur: 0.05 },
  z: { voiced: 1, manner: 'fric', f: [300, 1700, 2500], noise: { f: 5500, bw: 1500, level: 0.3 }, dur: 0.08 },
  v: { voiced: 1, manner: 'fric', f: [300, 1100, 2200], noise: { f: 1800, bw: 2500, level: 0.2 }, dur: 0.07 },
  zh: { voiced: 1, manner: 'fric', f: [300, 1700, 2400], noise: { f: 3000, bw: 1200, level: 0.3 }, dur: 0.08 },
  p: { voiced: 0, manner: 'stop', noise: { f: 1500, bw: 3000, level: 0.45 }, dur: 0.07 },
  t: { voiced: 0, manner: 'stop', noise: { f: 4000, bw: 2500, level: 0.5 }, dur: 0.07 },
  k: { voiced: 0, manner: 'stop', noise: { f: 2200, bw: 2500, level: 0.5 }, dur: 0.07 },
  b: { voiced: 1, manner: 'stop', f: [250, 1100, 2200], noise: { f: 1200, bw: 2500, level: 0.25 }, dur: 0.07 },
  d: { voiced: 1, manner: 'stop', f: [250, 1700, 2600], noise: { f: 3500, bw: 2000, level: 0.3 }, dur: 0.07 },
  g: { voiced: 1, manner: 'stop', f: [250, 2000, 2600], noise: { f: 2000, bw: 2000, level: 0.3 }, dur: 0.07 },
  ch: { voiced: 0, manner: 'stop', noise: { f: 3000, bw: 1500, level: 0.5 }, dur: 0.1 },
  j: { voiced: 1, manner: 'stop', f: [300, 1700, 2400], noise: { f: 3000, bw: 1500, level: 0.35 }, dur: 0.1 },
};
const VOWEL_DUR = 0.14;

// ── English letter-to-sound (compact rule reciter) ──
// Pragmatic, not linguistically complete — enough to make common words recognizable.
const DIGRAPHS = { th: 'th', sh: 'sh', ch: 'ch', ph: 'f', wh: 'w', ck: 'k', ng: 'ng', qu: 'kw', gh: '', kn: 'n', wr: 'r' };
const VOWEL_PAIRS = { ee: 'iy', ea: 'iy', oo: 'uw', ou: 'aw', ow: 'aw', oa: 'ow', ai: 'ey', ay: 'ey', oy: 'oy', oi: 'oy', au: 'ao', aw: 'ao', ey: 'iy', ie: 'iy', ue: 'uw' };
const SINGLE = { b: 'b', c: 'k', d: 'd', f: 'f', g: 'g', h: 'h', j: 'j', k: 'k', l: 'l', m: 'm', n: 'n', p: 'p', q: 'k', r: 'r', s: 's', t: 't', v: 'v', w: 'w', x: 'ks', y: 'y', z: 'z' };
const SHORT_VOWEL = { a: 'ae', e: 'eh', i: 'ih', o: 'aa', u: 'uh' };
const LONG_VOWEL = { a: 'ey', e: 'iy', i: 'ay', o: 'ow', u: 'uw' };
const isV = (c) => 'aeiou'.includes(c);

/** Split a mapping string (e.g. "ks", "kw") into known phonemes, greedily 2-then-1 char. */
function splitPh(s) {
  const out = [];
  for (let i = 0; i < s.length; ) {
    const two = s.slice(i, i + 2);
    if (VOWELS[two] || CONS[two]) { out.push(two); i += 2; }
    else { out.push(s[i]); i += 1; }
  }
  return out;
}

/** Rule-based grapheme→phoneme for one lowercase word. Returns a phoneme list. */
function wordToPhonemes(w) {
  const ph = [];
  const n = w.length;
  for (let i = 0; i < n; ) {
    const two = w.slice(i, i + 2);
    if (DIGRAPHS[two] !== undefined) { if (DIGRAPHS[two]) splitPh(DIGRAPHS[two]).forEach((p) => push(ph, p)); i += 2; continue; }
    if (VOWEL_PAIRS[two]) { push(ph, VOWEL_PAIRS[two]); i += 2; continue; }
    const c = w[i];
    if (isV(c)) {
      // word-final 'e' after a consonant is silent (the "magic e")
      if (c === 'e' && i === n - 1 && i > 0 && !isV(w[i - 1])) { i += 1; continue; }
      // long vowel when followed by a single consonant + final silent e:  CVCe
      const long = i + 2 < n && !isV(w[i + 1]) && w[i + 2] === 'e' && i + 3 === n;
      push(ph, long ? LONG_VOWEL[c] : SHORT_VOWEL[c]);
      i += 1;
    } else if (SINGLE[c]) {
      if (c === 'c' && 'eiy'.includes(w[i + 1])) push(ph, 's');       // soft c
      else if (c === 'g' && 'eiy'.includes(w[i + 1])) push(ph, 'j');  // soft g
      else splitPh(SINGLE[c]).forEach((p) => push(ph, p));
      i += 1;
    } else { i += 1; }
  }
  // a word that produced no vowel gets a schwa so it stays audible
  if (!ph.some((p) => VOWELS[p])) push(ph, 'ax');
  return ph;
}
function push(arr, p) { if (p && (VOWELS[p] || CONS[p])) arr.push(p); }

/** Split text into words + punctuation pauses. */
function textToPhonemes(text) {
  const out = [];
  for (const tok of String(text).toLowerCase().split(/\s+/)) {
    const word = tok.replace(/[^a-z']/g, '');
    if (word) { out.push(...wordToPhonemes(word)); }
    if (/[.,!?;:]/.test(tok)) out.push('_'); // pause marker
    out.push('_w'); // short inter-word gap
  }
  return out;
}

// ── Klatt digital resonator: y[n] = A·x[n] + B·y[n-1] + C·y[n-2] ──
function makeResonator(fs) {
  let A = 1, B = 0, C = 0, y1 = 0, y2 = 0;
  return {
    set(F, BW) {
      const r = Math.exp((-Math.PI * BW) / fs);
      const theta = (2 * Math.PI * F) / fs;
      B = 2 * r * Math.cos(theta); C = -r * r; A = 1 - B - C;
    },
    step(x) { const y = A * x + B * y1 + C * y2; y2 = y1; y1 = y; return y; },
  };
}

export class FormantTTS {
  /** @param {{ sampleRate?:number, f0?:number, f0End?:number, speed?:number }} [opts] */
  constructor(opts = {}) {
    this.sampleRate = opts.sampleRate || 24000;
    this.f0 = opts.f0 || 120;             // base pitch (persona-tunable)
    this.f0End = opts.f0End || (opts.f0 || 120) * 0.85; // declination
    this.speed = opts.speed || 1.0;
  }

  /** Resolve a phoneme token to synthesis targets {f1,f2,f3, voiced, noise, dur}. */
  _target(p) {
    if (p === '_') return { silence: 0.18 };
    if (p === '_w') return { silence: 0.04 };
    const v = VOWELS[p];
    if (v) {
      if (Array.isArray(v) && typeof v[0] === 'string') { // diphthong
        const a = VOWELS[v[0]], b = VOWELS[v[1]];
        return { glide: [a, b], voiced: 1, dur: VOWEL_DUR * 1.3 };
      }
      return { f: v, voiced: 1, dur: VOWEL_DUR };
    }
    const c = CONS[p];
    if (c) return { f: c.f || [400, 1200, 2400], voiced: c.voiced, noise: c.noise, manner: c.manner, dur: c.dur };
    return { silence: 0.03 };
  }

  /**
   * Synthesize text to mono Float32 PCM in [-1,1].
   * @param {string} text
   * @returns {Float32Array}
   */
  synthesize(text) {
    const fs = this.sampleRate;
    const segs = textToPhonemes(text).map((p) => this._target(p));
    const totalDur = segs.reduce((a, s) => a + (s.silence || s.dur || 0.05) / this.speed, 0.05);
    const out = new Float32Array(Math.max(1, Math.ceil(totalDur * fs)));

    const R1 = makeResonator(fs), R2 = makeResonator(fs), R3 = makeResonator(fs);
    const Rn = makeResonator(fs); // fricative noise shaper
    let glotPhase = 0;
    let pos = 0;
    const N = out.length;

    // current (interpolated) formant state, started from a neutral schwa
    let cf = [640, 1190, 2390];

    for (let si = 0; si < segs.length; si++) {
      const s = segs[si];
      const dur = (s.silence != null ? s.silence : s.dur || 0.05) / this.speed;
      const len = Math.max(1, Math.round(dur * fs));
      if (s.silence != null) { pos += len; glotPhase = 0; continue; }

      // target formants (end of glide for diphthongs handled via per-sample interp)
      const fStart = s.glide ? s.glide[0] : s.f;
      const fEnd = s.glide ? s.glide[1] : s.f;
      const voiced = s.voiced;
      const noise = s.noise;
      // amplitude envelope: quick attack, gentle release
      for (let i = 0; i < len && pos < N; i++, pos++) {
        const u = i / len;                       // 0..1 within segment
        const tGlobal = pos / N;
        const f0 = this.f0 + (this.f0End - this.f0) * tGlobal; // declination

        // coarticulation: first 35% ramps cf from the previous state toward this segment's start
        const co = Math.min(1, u / 0.35);
        const tf0 = cf[0] + (fStart[0] - cf[0]) * co;
        const tf1 = cf[1] + (fStart[1] - cf[1]) * co;
        const tf2 = cf[2] + (fStart[2] - cf[2]) * co;
        // within-segment glide toward fEnd
        const f1 = tf0 + (fEnd[0] - tf0) * u;
        const f2 = tf1 + (fEnd[1] - tf1) * u;
        const f3 = tf2 + (fEnd[2] - tf2) * u;
        R1.set(f1, 70); R2.set(f2, 100); R3.set(f3, 160);

        // source
        let src = 0;
        if (voiced) {
          glotPhase += f0 / fs;
          if (glotPhase >= 1) glotPhase -= 1;
          // shaped glottal pulse: a soft impulse near phase 0 (Rosenberg-ish)
          src = glotPhase < 0.4 ? Math.sin(Math.PI * glotPhase / 0.4) ** 2 - 0.5 : -0.1;
        }
        // voiced output through the formant cascade
        let y = voiced ? R3.step(R2.step(R1.step(src))) : 0;

        // frication noise (consonants), shaped by a noise resonator
        if (noise) {
          Rn.set(noise.f, noise.bw);
          const nz = Rn.step((Math.random() * 2 - 1)) * noise.level;
          // stops burst at onset; fricatives steady
          const env = s.manner === 'stop' ? Math.max(0, 1 - u * 3) : 1;
          y += nz * env;
        }
        // amplitude envelope (avoid clicks)
        const amp = Math.min(1, u / 0.05) * Math.min(1, (1 - u) / 0.08);
        out[pos] += y * amp * (voiced ? 1.6 : 1.0);
      }
      cf = fEnd; // carry formant state into the next segment
    }

    // normalize to a comfortable peak
    let peak = 0;
    for (let i = 0; i < N; i++) peak = Math.max(peak, Math.abs(out[i]));
    if (peak > 0) { const g = 0.85 / peak; for (let i = 0; i < N; i++) out[i] *= g; }
    return out;
  }
}

export default FormantTTS;
