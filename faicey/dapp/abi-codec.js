// abi-codec.js — minimal in-house ABI encode/decode (no ethers, no CDN).
//
// Selectors come precomputed from the generated abi.js (forge methodIdentifiers), so the
// browser never needs keccak. Inputs across the SoundWave/Jaimla surface are all static
// types (address, uintN, bool, bytes32, fixed uintN[k]); decoding additionally handles
// `string` and static `tuple` returns. Enough to drive these contracts generically.

const hex = (n, width = 64) => n.toString(16).padStart(width, '0');

function stripHex(s) {
  return s.startsWith('0x') ? s.slice(2) : s;
}

// ── canonical signature for selector lookup (e.g. "transfer(address,uint256)") ──
export function canonicalType(t) {
  if (t.type === 'tuple') return '(' + t.components.map(canonicalType).join(',') + ')';
  if (t.type.startsWith('tuple[')) {
    const inner = '(' + t.components.map(canonicalType).join(',') + ')';
    return inner + t.type.slice(5);
  }
  return t.type;
}
export function signatureOf(fn) {
  return `${fn.name}(${(fn.inputs || []).map(canonicalType).join(',')})`;
}

// ── encode static argument(s) ──
function encodeWord(type, value) {
  if (type === 'address') return hex(BigInt(value), 64);
  if (type === 'bool') return hex(value ? 1n : 0n, 64);
  if (type.startsWith('uint') || type.startsWith('int')) return hex(BigInt(value), 64);
  if (type.startsWith('bytes') && type !== 'bytes') {
    // bytesN — right-padded
    return stripHex(value).padEnd(64, '0');
  }
  throw new Error('encodeWord: unsupported static type ' + type);
}

/** Encode a function call → 0x<selector><args> (static inputs only). */
export function encodeCall(fn, selector, values) {
  let out = '';
  (fn.inputs || []).forEach((inp, i) => {
    const v = values[i];
    const m = inp.type.match(/^(\w+)\[(\d+)\]$/); // fixed array uintN[k]
    if (m) {
      const base = m[1];
      for (const el of v) out += encodeWord(base, el);
    } else {
      out += encodeWord(inp.type, v);
    }
  });
  return '0x' + selector + out;
}

// ── decode outputs ──
function readWord(data, off) {
  return data.slice(off * 64, off * 64 + 64);
}
function decodeStatic(type, word, components) {
  if (type === 'address') return '0x' + word.slice(24);
  if (type === 'bool') return BigInt('0x' + word) === 1n;
  if (type.startsWith('uint') || type.startsWith('int')) return BigInt('0x' + word).toString();
  if (type.startsWith('bytes')) return '0x' + word;
  return '0x' + word;
}

/**
 * Decode return data for a function's outputs. Supports static scalars, `string`,
 * and static `tuple` (all-static components).
 * @returns {any|any[]} single value if one output, else array
 */
export function decodeOutputs(outputs, dataHex) {
  const data = stripHex(dataHex);
  const vals = [];
  let head = 0;
  for (const out of outputs) {
    if (out.type === 'string' || out.type === 'bytes') {
      const off = Number(BigInt('0x' + readWord(data, head))) / 32;
      const len = Number(BigInt('0x' + readWord(data, off)));
      const bytes = data.slice((off + 1) * 64, (off + 1) * 64 + len * 2);
      vals.push(out.type === 'string' ? hexToUtf8(bytes) : '0x' + bytes);
      head += 1;
    } else if (out.type === 'tuple') {
      const obj = {};
      out.components.forEach((c) => {
        obj[c.name] = decodeStatic(c.type, readWord(data, head));
        head += 1;
      });
      vals.push(obj);
    } else {
      vals.push(decodeStatic(out.type, readWord(data, head)));
      head += 1;
    }
  }
  return vals.length === 1 ? vals[0] : vals;
}

function hexToUtf8(h) {
  let s = '';
  for (let i = 0; i < h.length; i += 2) s += String.fromCharCode(parseInt(h.substr(i, 2), 16));
  return decodeURIComponent(escape(s));
}

/** keccak-free selector lookup from the generated `selectors` map. */
export function selectorFor(fn, selectors) {
  const sig = signatureOf(fn);
  const sel = selectors[sig];
  if (!sel) throw new Error('no selector for ' + sig + ' (re-run export-abis)');
  return sel;
}
