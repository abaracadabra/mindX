#!/usr/bin/env node
/**
 * aivatar CLI — inspect, verify and describe `.persona` files.
 *
 *   aivatar modes                    — the three tiers and their gates
 *   aivatar inspect <file.persona>   — identity, embodiment, EARNED tier, provenance
 *   aivatar verify  <file.persona>   — recompute every hash; exit 1 if anything is off
 *   aivatar grade   '<json>'         — what tier would these measurements earn?
 *   aivatar capability               — what can THIS host actually do?
 *
 * © Professor Codephreak - rage.pythai.net
 */
import { PersonaStudio, MODES, grade, verify, validate } from './src/index.js';

const [, , cmd, ...args] = process.argv;
const bold = (s) => `\x1b[1m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;
const ok = (s) => `\x1b[32m${s}\x1b[0m`;
const bad = (s) => `\x1b[31m${s}\x1b[0m`;

const usage = () => {
  console.log(`${bold('aivatar')} — the definitive .persona creation tool
  ${bold('modes')}                     the three fidelity tiers + their gates
  ${bold('inspect')} <file.persona>    identity, embodiment, earned tier, provenance
  ${bold('verify')}  <file.persona>    recompute every hash (exit 1 on tamper)
  ${bold('grade')}   '<json>'          what tier do these measurements earn?
  ${bold('capability')}                what can this host actually do?

${dim('face: faicey · voice: voaice · rig: facerig · mind: cognitive .persona')}`);
};

switch (cmd) {
  case 'modes': {
    for (const m of Object.values(MODES)) {
      console.log(`\n${bold(m.name.toUpperCase())} — ${m.intent}`);
      console.log(`  face   ${m.face.source}, ≥${m.face.minFrames} frame(s), ${m.face.render}${m.face.textured ? ' + textures' : ''}`);
      console.log(`  voice  ${m.voice.engine}${m.voice.clone ? ' (clone)' : ''}, ${m.voice.sampleRate}Hz/${m.voice.bitDepth}-bit, ${m.voice.quality}`);
      console.log(`  export ${m.export.formats.join(', ')}${m.export.manifest ? ' + signed manifest' : ''}`);
      console.log(`  consent ${m.provenance.consent}${m.provenance.required ? dim(' (provenance MANDATORY)') : ''}`);
      if (m.name === 'scientific') {
        for (const [lvl, g] of Object.entries(m.gates)) {
          console.log(`  ${bold(lvl)} gates: rmse≤${g.faceRmse} · frames≥${g.faceFrames} · voice≥${g.voiceSimilarity} · ref≥${g.referenceSeconds}s · spectral≤${g.spectralDistance}`);
        }
      } else if (m.gates) {
        const g = m.gates;
        console.log(`  gates: rmse≤${g.faceRmse} · frames≥${g.faceFrames} · voice≥${g.voiceSimilarity} · ref≥${g.referenceSeconds}s`);
      }
    }
    console.log(`\n${dim('A tier is EARNED by measurement, never chosen. stamp() downgrades rather than flatters.')}`);
    break;
  }

  case 'inspect': {
    if (!args[0]) { usage(); process.exit(1); }
    const { persona, validation, provenance } = await PersonaStudio.load(args[0]);
    const f = persona.fidelity;
    console.log(`\n${bold(persona.identity.name || '(unnamed)')} ${dim(persona.hash || '')}`);
    if (persona.identity.description) console.log(`  ${persona.identity.description}`);
    console.log(`\n  ${bold('tier')}      ${f.mode}${f.realism ? '/' + f.realism : ''} ${f.requested && f.requested.mode !== f.mode ? bad(`(requested ${f.requested.mode}${f.requested.realism ? '/' + f.requested.realism : ''} — DOWNGRADED)`) : ok('(earned)')}`);
    if (f.graded?.failed?.length) console.log(`  ${dim('failed gates: ' + f.graded.failed.join(', '))}`);
    console.log(`  ${bold('face')}      ${persona.embodiment.face ? `${persona.embodiment.face.frames} frame(s), ${persona.embodiment.face.source}` : dim('none')}`);
    console.log(`  ${bold('voice')}     ${persona.embodiment.voice ? `${persona.embodiment.voice.engine}, ${persona.embodiment.voice.sampleRate}Hz/${persona.embodiment.voice.bitDepth}` : dim('none')}`);
    console.log(`  ${bold('mind')}      ${persona.cognition.behavioral_traits?.length ? persona.cognition.behavioral_traits.join(', ') : dim('no traits')}`);
    console.log(`  ${bold('consent')}   ${persona.provenance.consent ? persona.provenance.consent.consentKind : dim('none')}`);
    console.log(`  ${bold('custody')}   ${persona.provenance.custody?.length || 0} step(s)`);
    console.log(`  ${bold('manifest')}  ${persona.provenance.manifest ? (persona.provenance.manifest.signature ? ok('signed by ' + (persona.provenance.manifest.signer || '?')) : bad('UNSIGNED')) : dim('none')}`);
    if (Object.keys(f.measured || {}).length) {
      console.log(`\n  ${bold('measured')}`);
      for (const [k, v] of Object.entries(f.measured)) {
        const src = f.measuredSource?.[k] || 'computed';
        console.log(`    ${k.padEnd(18)} ${String(typeof v === 'number' ? v.toFixed(4) : v).padEnd(10)} ${dim(src)}`);
      }
    }
    console.log(`\n  ${validation.ok ? ok('✔ valid') : bad('✘ invalid: ' + validation.errors.join('; '))}`);
    console.log(`  ${provenance.ok ? ok('✔ provenance intact') : bad('✘ provenance: ' + provenance.errors.join('; '))}\n`);
    break;
  }

  case 'verify': {
    if (!args[0]) { usage(); process.exit(1); }
    const { persona, validation, provenance } = await PersonaStudio.load(args[0]);
    const good = validation.ok && provenance.ok;
    console.log(good ? ok('✔ VERIFIED') : bad('✘ FAILED'));
    [...validation.errors, ...provenance.errors].forEach((e) => console.log('  ' + bad(e)));
    validation.warnings.forEach((w) => console.log('  ' + dim(w)));
    if (good) console.log(dim(`  ${persona.fidelity.mode}${persona.fidelity.realism ? '/' + persona.fidelity.realism : ''} · ${provenance.signed ? 'signed by ' + provenance.signer : 'unsigned'}`));
    process.exit(good ? 0 : 1);
  }

  case 'grade': {
    const measured = JSON.parse(args[0] || '{}');
    const g = grade(measured);
    console.log(`${bold(g.mode)}${g.realism ? '/' + g.realism : ''}`);
    if (g.passed.length) console.log(ok('  passed: ') + g.passed.join(', '));
    if (g.failed.length) console.log(bad('  failed: ') + g.failed.join(', '));
    break;
  }

  case 'capability': {
    const cap = await new PersonaStudio().capability();
    console.log(`\n  face (faicey)    ${cap.face ? ok('yes') : bad('no')}`);
    console.log(`  voice (voaice)   ${cap.voice ? ok('yes') : bad('no')}`);
    console.log(`  voice cloning    ${cap.voiceClone ? ok('yes') : bad('no')}`);
    console.log(`  forensic         ${cap.forensic ? ok('yes') : bad('no')}`);
    console.log(`  export wav/ogg   ${cap.export.wav ? ok('wav') : bad('—')} ${cap.export.ogg ? ok('ogg') : dim('ogg needs ffmpeg')}`);
    console.log(`  signing key      ${cap.signing ? ok('yes') : dim('none (scientific tier needs one)')}`);
    console.log(`\n  ${bold('max honest mode:')} ${cap.maxHonestMode}\n`);
    break;
  }

  default:
    usage();
}
