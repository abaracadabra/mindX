/**
 * emotion.js — engine-owned emotion model, fanned out to voice + face.
 *
 * Chatterbox (Resemble AI) is the TTS known for built-in emotion control, but its surface is a
 * single CONTINUOUS scalar `exaggeration` (0..1, 0.5 = neutral) plus `cfg_weight`/`temperature`
 * and Turbo's paralinguistic tags `[laugh]`/`[chuckle]`/`[cough]` — it exposes NO discrete
 * emotion class to read back. So voaice OWNS the emotion as `{label, intensity}` and fans it out:
 *
 *   emotion {label,intensity}
 *     → toVoiceParams() → { exaggeration, cfg_weight, temperature, prosody }  (drives the voice)
 *     → toFace()        → { expression, weight, hue }                          (drives faicey FACE)
 *
 * Because the FACE is driven from the SAME owned emotion, expression display works even when the
 * audio backend can't emote (Kokoro/ZipVoice) — only Chatterbox actually actuates the voice params.
 * Face `expression` names match faicey's vocabulary so `faicey.setExpression(expression, weight)`
 * takes them directly.
 */

// label → fan-out. `face` ∈ faicey expressions/morphs; `exg/cfg/temp` are Chatterbox baselines at
// intensity 0.6; `prosody` is the fallback for non-emotive backends; `hue` tints the display.
export const EMOTIONS = {
  neutral:   { face: 'neutral',   exg: 0.50, cfg: 0.50, temp: 0.80, hue: 150, prosody: { pitch: 1.00, speed: 1.00 } },
  happy:     { face: 'happy',     exg: 0.65, cfg: 0.45, temp: 0.90, hue: 90,  prosody: { pitch: 1.08, speed: 1.06 } },
  excited:   { face: 'excited',   exg: 0.85, cfg: 0.32, temp: 1.00, hue: 60,  prosody: { pitch: 1.14, speed: 1.12 } },
  calm:      { face: 'smile',     exg: 0.45, cfg: 0.60, temp: 0.70, hue: 175, prosody: { pitch: 0.98, speed: 0.95 } },
  sad:       { face: 'sad',       exg: 0.35, cfg: 0.62, temp: 0.62, hue: 215, prosody: { pitch: 0.90, speed: 0.90 } },
  angry:     { face: 'angry',     exg: 0.88, cfg: 0.30, temp: 0.95, hue: 0,   prosody: { pitch: 1.05, speed: 1.08 } },
  surprised: { face: 'surprised', exg: 0.78, cfg: 0.40, temp: 0.95, hue: 45,  prosody: { pitch: 1.16, speed: 1.05 } },
  confused:  { face: 'confused',  exg: 0.52, cfg: 0.55, temp: 0.85, hue: 280, prosody: { pitch: 1.02, speed: 0.96 } },
  thinking:  { face: 'thinking',  exg: 0.42, cfg: 0.60, temp: 0.78, hue: 195, prosody: { pitch: 0.97, speed: 0.94 } },
};

export const EMOTION_LABELS = Object.keys(EMOTIONS);

// Chatterbox Turbo paralinguistic tags → a face animation trigger (a timed event, not a state).
export const PARALINGUISTIC_TAGS = ['laugh', 'chuckle', 'cough'];
const TAG_FACE = { laugh: 'laugh', chuckle: 'happy', cough: 'surprised' };

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const DEFAULT_INTENSITY = 0.6; // matches the EMOTIONS baselines

/**
 * Normalise any emotion input to a resolved descriptor.
 * @param {string|{label?:string, intensity?:number}|null|undefined} input
 * @returns {{ label:string, intensity:number, def:object }}
 */
export function resolveEmotion(input) {
  let label = 'neutral';
  let intensity = DEFAULT_INTENSITY;
  if (typeof input === 'string') label = input;
  else if (input && typeof input === 'object') {
    if (input.label) label = input.label;
    if (typeof input.intensity === 'number') intensity = input.intensity;
  }
  if (!EMOTIONS[label]) label = 'neutral';
  intensity = clamp(intensity, 0, 1);
  return { label, intensity, def: EMOTIONS[label] };
}

/**
 * Voice parameters (Chatterbox-shaped) for an emotion. `exaggeration` interpolates from neutral
 * (0.5) toward the emotion's baseline, scaled by intensity (baseline reached at intensity 0.6),
 * and may exceed 1 for dramatic delivery (clamped). `prosody` is for non-emotive backends.
 * @returns {{ exaggeration:number, cfg_weight:number, temperature:number, prosody:{pitch:number,speed:number} }}
 */
export function toVoiceParams(input) {
  const { intensity, def } = resolveEmotion(input);
  const k = intensity / DEFAULT_INTENSITY; // 0 at intensity 0, 1 at the baseline 0.6
  const exaggeration = clamp(0.5 + (def.exg - 0.5) * k, 0, 1.2);
  // pacing/expressiveness ease toward their baselines with intensity
  const cfg_weight = clamp(0.5 + (def.cfg - 0.5) * Math.min(1, k), 0, 1);
  const temperature = clamp(0.8 + (def.temp - 0.8) * Math.min(1, k), 0.4, 1.2);
  const prosody = {
    pitch: 1 + (def.prosody.pitch - 1) * Math.min(1.2, k),
    speed: 1 + (def.prosody.speed - 1) * Math.min(1.2, k),
  };
  return { exaggeration, cfg_weight, temperature, prosody };
}

/**
 * Face descriptor for an emotion — feeds faicey.setExpression(expression, weight) directly.
 * @returns {{ expression:string, weight:number, hue:number, label:string }}
 */
export function toFace(input) {
  const { label, intensity, def } = resolveEmotion(input);
  return { expression: def.face, weight: clamp(intensity, 0, 1), hue: def.hue, label };
}

/** Full fan-out in one call (what synthesize() attaches to results). */
export function fanOut(input) {
  const { label, intensity } = resolveEmotion(input);
  return { label, intensity, voice: toVoiceParams(input), face: toFace(input) };
}

/**
 * Extract Chatterbox-style paralinguistic tags from text. Returns the cleaned text and the tag
 * events (each a face trigger). Unknown bracket tokens are left in place.
 * @param {string} text
 * @returns {{ clean:string, tags:Array<{tag:string, face:string, at:number}> }}
 */
export function extractTags(text) {
  const tags = [];
  const clean = String(text || '').replace(/\[([a-z]+)\]/gi, (m, t) => {
    const tag = t.toLowerCase();
    if (PARALINGUISTIC_TAGS.includes(tag)) {
      tags.push({ tag, face: TAG_FACE[tag], at: tags.length });
      return ' ';
    }
    return m; // leave non-paralinguistic brackets untouched
  });
  return { clean: clean.replace(/\s+/g, ' ').trim(), tags };
}
