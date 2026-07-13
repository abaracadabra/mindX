/**
 * wav.js — zero-dependency PCM WAV codec.
 *
 * Pure Node (Buffer + DataView). Encodes Float32 samples in [-1,1] to a canonical
 * 16-bit mono PCM WAV, and decodes 8/16/24/32-bit PCM and 32-bit float WAV back to a
 * Float32Array. No external deps — the neural engine uses this to (a) emit output WAV
 * and (b) decode a reference clip into frames for Scientific.js voiceprinting.
 *
 *   import { encodeWav, decodeWav } from 'voaice/wav';
 *   const buf = encodeWav(float32, 24000);          // -> Buffer (WAV bytes)
 *   const { samples, sampleRate } = decodeWav(buf); // -> Float32Array in [-1,1]
 */

const clamp = (v) => (v > 1 ? 1 : v < -1 ? -1 : v);

/**
 * Encode mono Float32 samples to a PCM WAV buffer.
 * Default stays the canonical 16-bit PCM; quality-tier exports (Exporter.js)
 * pass `bitDepth` 24 (int PCM) or 32 (IEEE float, fmt=3).
 * @param {Float32Array|number[]} samples values in [-1,1]
 * @param {number} [sampleRate=24000]
 * @param {{bitDepth?: 16|24|32}} [opts]
 * @returns {Buffer}
 */
export function encodeWav(samples, sampleRate = 24000, { bitDepth = 16 } = {}) {
  if (![16, 24, 32].includes(bitDepth)) {
    throw new Error(`encodeWav: unsupported bitDepth ${bitDepth} (16|24|32)`);
  }
  const n = samples.length;
  const bytesPerSample = bitDepth >> 3;
  const isFloat = bitDepth === 32; // 32-bit is written as IEEE float (fmt=3)
  const blockAlign = bytesPerSample; // mono
  const byteRate = sampleRate * blockAlign;
  const dataSize = n * bytesPerSample;
  const buf = Buffer.alloc(44 + dataSize);

  // RIFF header
  buf.write('RIFF', 0, 'ascii');
  buf.writeUInt32LE(36 + dataSize, 4);
  buf.write('WAVE', 8, 'ascii');
  // fmt chunk
  buf.write('fmt ', 12, 'ascii');
  buf.writeUInt32LE(16, 16); // fmt chunk size
  buf.writeUInt16LE(isFloat ? 3 : 1, 20); // 1 = int PCM, 3 = IEEE float
  buf.writeUInt16LE(1, 22); // channels = mono
  buf.writeUInt32LE(sampleRate, 24);
  buf.writeUInt32LE(byteRate, 28);
  buf.writeUInt16LE(blockAlign, 32);
  buf.writeUInt16LE(bitDepth, 34);
  // data chunk
  buf.write('data', 36, 'ascii');
  buf.writeUInt32LE(dataSize, 40);

  let off = 44;
  for (let i = 0; i < n; i++) {
    const s = clamp(samples[i]);
    if (isFloat) {
      buf.writeFloatLE(s, off);
    } else if (bitDepth === 24) {
      const v = s < 0 ? Math.round(s * 0x800000) : Math.round(s * 0x7fffff);
      buf.writeUInt8(v & 0xff, off);
      buf.writeUInt8((v >> 8) & 0xff, off + 1);
      buf.writeUInt8((v >> 16) & 0xff, off + 2);
    } else {
      // symmetric quantisation to int16
      buf.writeInt16LE(s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff), off);
    }
    off += bytesPerSample;
  }
  return buf;
}

/**
 * Decode a PCM/float WAV buffer to mono Float32 samples in [-1,1].
 * Supports 8/16/24/32-bit integer PCM (fmt=1) and 32-bit float (fmt=3); multi-channel
 * input is down-mixed to mono by averaging channels.
 * @param {Buffer|Uint8Array|ArrayBuffer} input
 * @returns {{samples: Float32Array, sampleRate: number, channels: number}}
 */
export function decodeWav(input) {
  const buf = Buffer.isBuffer(input) ? input : Buffer.from(input);
  if (buf.length < 12 || buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WAVE') {
    throw new Error('decodeWav: not a RIFF/WAVE file');
  }

  let audioFormat = 1;
  let channels = 1;
  let sampleRate = 24000;
  let bitsPerSample = 16;
  let dataOffset = -1;
  let dataSize = 0;

  // walk chunks
  let p = 12;
  while (p + 8 <= buf.length) {
    const id = buf.toString('ascii', p, p + 4);
    const size = buf.readUInt32LE(p + 4);
    const body = p + 8;
    if (id === 'fmt ') {
      audioFormat = buf.readUInt16LE(body);
      channels = buf.readUInt16LE(body + 2) || 1;
      sampleRate = buf.readUInt32LE(body + 4);
      bitsPerSample = buf.readUInt16LE(body + 14);
    } else if (id === 'data') {
      dataOffset = body;
      dataSize = Math.min(size, buf.length - body);
      break; // samples follow; stop scanning
    }
    p = body + size + (size & 1); // chunks are word-aligned
  }
  if (dataOffset < 0) throw new Error('decodeWav: no data chunk');

  const bytesPerSample = bitsPerSample >> 3;
  const frameCount = Math.floor(dataSize / (bytesPerSample * channels));
  const out = new Float32Array(frameCount);

  const readSample = (off) => {
    if (audioFormat === 3 && bitsPerSample === 32) return buf.readFloatLE(off);
    switch (bitsPerSample) {
      case 8:
        return (buf.readUInt8(off) - 128) / 128; // 8-bit PCM is unsigned
      case 16:
        return buf.readInt16LE(off) / 0x8000;
      case 24: {
        let v = buf[off] | (buf[off + 1] << 8) | (buf[off + 2] << 16);
        if (v & 0x800000) v |= ~0xffffff; // sign-extend
        return v / 0x800000;
      }
      case 32:
        return buf.readInt32LE(off) / 0x80000000;
      default:
        throw new Error(`decodeWav: unsupported bit depth ${bitsPerSample}`);
    }
  };

  for (let i = 0; i < frameCount; i++) {
    let acc = 0;
    const base = dataOffset + i * bytesPerSample * channels;
    for (let c = 0; c < channels; c++) acc += readSample(base + c * bytesPerSample);
    out[i] = acc / channels;
  }
  return { samples: out, sampleRate, channels };
}

/** Slice mono samples into fixed-size frames (last frame zero-padded). */
export function frames(samples, frameSize = 2048, hop = frameSize) {
  const out = [];
  for (let start = 0; start + 1 < samples.length; start += hop) {
    const f = new Float32Array(frameSize);
    const end = Math.min(samples.length, start + frameSize);
    for (let i = start; i < end; i++) f[i - start] = samples[i];
    out.push(f);
  }
  return out;
}
