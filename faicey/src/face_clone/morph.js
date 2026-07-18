/**
 * morph.js — the morph modes.
 *
 * Beyond human ↔ machine, the face morphs on a sliding scale into archetypes —
 * vampire, elf, dragon, pleiadian — each a procedural overlay driven by the
 * landmarks (fangs, pointed ears, scales + horns, large luminous eyes) at the
 * slider's intensity. Stylised, generic, and landmark-tracked so they express.
 *
 * The registry + palettes + intensity math are pure and tested; the archetype
 * drawing is the demo's browser layer. (`mech.js` holds the one-sided
 * human↔machine ramp; this holds the whole-face archetypes.)
 *
 * © Professor Codephreak - rage.pythai.net
 */

export const MORPH_MODES = Object.freeze([
  { key: 'none', label: 'human', whole: false },
  { key: 'mech', label: 'machine', whole: false, side: true },
  { key: 'vampire', label: 'vampire', whole: true },
  { key: 'elf', label: 'elf', whole: true },
  { key: 'dragon', label: 'dragon', whole: true },
  { key: 'pleiadian', label: 'pleiadian', whole: true },
]);

export const MORPH_PALETTE = Object.freeze({
  vampire: { skin: '#e7dfe4', accent: '#7a1020', eye: '#d21226', fang: '#f4eee9' },
  elf: { skin: '#e9e6d6', accent: '#5b7c4a', eye: '#3fae8f', ear: '#dcd4bc' },
  dragon: { skin: '#3b6b4a', accent: '#c8992a', eye: '#ffcf3a', scale: '#2c5238', horn: '#d8c9a0' },
  pleiadian: { skin: '#dfe6ff', accent: '#8ea6ff', eye: '#bfe0ff', glow: 'rgba(150,190,255,0.6)' },
});

export function morphMode(key) { return MORPH_MODES.find((m) => m.key === key) || MORPH_MODES[0]; }
export const isWholeFace = (key) => !!morphMode(key).whole;
export const clampIntensity = (v) => Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0));

/** Palette for a mode, or null for none/mech (mech has its own palette). */
export const morphPalette = (key) => MORPH_PALETTE[key] || null;

/**
 * Age slider → a life band. 0 = child, 1 = elder. Drives procedural aging
 * (line depth, sag) and is recorded in the .persona.
 */
export function ageBand(v) {
  const t = clampIntensity(v);
  if (t < 0.15) return 'child';
  if (t < 0.35) return 'youth';
  if (t < 0.6) return 'adult';
  if (t < 0.82) return 'mature';
  return 'elder';
}
/** Map the age slider to an approximate year count (for the .persona note). */
export const ageYears = (v) => Math.round(6 + clampIntensity(v) * 84); // 6 → 90

export default MORPH_MODES;
