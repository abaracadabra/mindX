/**
 * persona.js — the unified cloned digital identity: FACE + VOICE.
 *
 * The culmination of the FACE/VOICE duality: a person cloned across both modalities. Combines a
 * faicey faceprint (faceprint.js) and an (optional) voaice voiceprint (Scientific.js) into one
 * deterministic, forensic **persona print** — registerable on-chain as `registerPersona(hash,
 * uint256[], precision)`, the union of `registerFacePrint` + `registerVoicePrint`.
 *
 * Either modality alone is valid (a face-only or voice-only persona); together they bind a single
 * identity. Deterministic: same prints → same persona hash. Pure JS (sha256 via node:crypto or
 * SubtleCrypto), no model.
 */

async function sha256Hex(str) {
  if (typeof process !== 'undefined' && process.versions && process.versions.node) {
    const { createHash } = await import('node:crypto');
    return createHash('sha256').update(str).digest('hex');
  }
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

// accept either a full print object ({hash, measuresStr|m, precisionScore}) or registerArgs
function norm(print) {
  if (!print) return null;
  const hash = print.hash;
  const m = print.measuresStr || print.m || [];
  const precisionScore = (print.precisionScore != null ? print.precisionScore : print.precision) ?? '0';
  return hash ? { hash, m: m.map(String), precisionScore: String(precisionScore) } : null;
}

/**
 * Bind a faceprint and/or voiceprint into one persona print.
 * @param {{ face?:object, voice?:object, label?:string }} parts  face/voice = print or registerArgs
 * @returns {Promise<{
 *   hash:string, kind:'persona', label:string|null,
 *   modalities:string[], face:object|null, voice:object|null,
 *   registerArgs:{ hash:string, faceHash:string, voiceHash:string, m:string[], precisionScore:string }
 * }>}
 */
export async function personaPrint(parts = {}) {
  const face = norm(parts.face);
  const voice = norm(parts.voice);
  if (!face && !voice) throw new Error('persona: need a faceprint and/or a voiceprint');

  const modalities = [face && 'face', voice && 'voice'].filter(Boolean);
  // canonical payload → persona hash (order fixed: face then voice)
  const payload = {
    v: 1,
    kind: 'persona',
    modalities,
    faceHash: face ? face.hash : '',
    voiceHash: voice ? voice.hash : '',
    measures: [...(face ? face.m : []), ...(voice ? voice.m : [])],
  };
  const hash = '0x' + (await sha256Hex(JSON.stringify(payload)));

  // combined precision = product of the present modalities' precision (both must be confident)
  const fp = face ? Number(face.precisionScore) / 1e18 : 1;
  const vp = voice ? Number(voice.precisionScore) / 1e18 : 1;
  const precision = clamp01(fp * vp);
  const precisionScore = (BigInt(Math.round(precision * 1e9)) * 10n ** 9n).toString();

  return {
    hash,
    kind: 'persona',
    label: parts.label || null,
    modalities,
    face,
    voice,
    registerArgs: {
      hash,
      faceHash: face ? face.hash : '0x0',
      voiceHash: voice ? voice.hash : '0x0',
      m: payload.measures,
      precisionScore,
    },
  };
}

/** Same-persona test across modalities — both prints must individually match. */
export function personaMatch(a, b, faceThresh = 0.15, voiceThresh = 0.15) {
  const sameFace = a.face && b.face ? a.face.hash === b.face.hash : null;
  const sameVoice = a.voice && b.voice ? a.voice.hash === b.voice.hash : null;
  return { hash: a.hash === b.hash, sameFace, sameVoice };
}

function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
