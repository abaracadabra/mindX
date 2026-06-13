/*
 * keccak.js — self-contained Keccak-256 (Ethereum) + address prediction helpers.
 *
 * Used ONLY by the admin console (admin.html) for PREVIEW: predicting CREATE and
 * CREATE2 addresses before broadcasting. The core deployer (index.html + deployer.js)
 * stays keccak-free; this is read-only admin tooling, not in the signing/trust path.
 * No external dependency. Public-domain Keccak-f[1600] (BigInt lanes).
 * (c) BANKON all rights preserved.
 */
(function () {
  "use strict";
  const RC = [
    0x0000000000000001n, 0x0000000000008082n, 0x800000000000808an, 0x8000000080008000n,
    0x000000000000808bn, 0x0000000080000001n, 0x8000000080008081n, 0x8000000000008009n,
    0x000000000000008an, 0x0000000000000088n, 0x0000000080008009n, 0x000000008000000an,
    0x000000008000808bn, 0x800000000000008bn, 0x8000000000008089n, 0x8000000000008003n,
    0x8000000000008002n, 0x8000000000000080n, 0x000000000000800an, 0x800000008000000an,
    0x8000000080008081n, 0x8000000000008080n, 0x0000000080000001n, 0x8000000080008008n,
  ];
  const R = [0, 1, 62, 28, 27, 36, 44, 6, 55, 20, 3, 10, 43, 25, 39, 41, 45, 15, 21, 8, 18, 2, 61, 56, 14];
  const MASK = (1n << 64n) - 1n;
  const rotl = (x, n) => ((x << n) | (x >> (64n - n))) & MASK;

  function keccakF(s) {
    for (let round = 0; round < 24; round++) {
      const C = new Array(5);
      for (let x = 0; x < 5; x++) C[x] = s[x] ^ s[x + 5] ^ s[x + 10] ^ s[x + 15] ^ s[x + 20];
      const D = new Array(5);
      for (let x = 0; x < 5; x++) D[x] = C[(x + 4) % 5] ^ rotl(C[(x + 1) % 5], 1n);
      for (let x = 0; x < 5; x++) for (let y = 0; y < 5; y++) s[x + 5 * y] ^= D[x];
      const B = new Array(25);
      for (let x = 0; x < 5; x++) for (let y = 0; y < 5; y++) B[y + 5 * ((2 * x + 3 * y) % 5)] = rotl(s[x + 5 * y], BigInt(R[x + 5 * y]));
      for (let x = 0; x < 5; x++) for (let y = 0; y < 5; y++) s[x + 5 * y] = B[x + 5 * y] ^ (~B[((x + 1) % 5) + 5 * y] & B[((x + 2) % 5) + 5 * y]);
      s[0] ^= RC[round];
    }
  }

  // bytes (Uint8Array) → 32-byte Uint8Array digest (Keccak-256, rate 1088 bits = 136 bytes).
  function keccak256Bytes(msg) {
    const rate = 136;
    const s = new Array(25).fill(0n);
    const padded = new Uint8Array(Math.ceil((msg.length + 1) / rate) * rate);
    padded.set(msg);
    padded[msg.length] ^= 0x01;
    padded[padded.length - 1] ^= 0x80;
    for (let off = 0; off < padded.length; off += rate) {
      for (let i = 0; i < rate / 8; i++) {
        let lane = 0n;
        for (let b = 0; b < 8; b++) lane |= BigInt(padded[off + i * 8 + b]) << BigInt(8 * b);
        s[i] ^= lane;
      }
      keccakF(s);
    }
    const out = new Uint8Array(32);
    for (let i = 0; i < 4; i++) { let lane = s[i]; for (let b = 0; b < 8; b++) out[i * 8 + b] = Number((lane >> BigInt(8 * b)) & 0xffn); }
    return out;
  }

  const hexToBytes = (h) => { h = (h || "").replace(/^0x/i, ""); const a = new Uint8Array(h.length / 2); for (let i = 0; i < a.length; i++) a[i] = parseInt(h.substr(i * 2, 2), 16); return a; };
  const bytesToHex = (b) => "0x" + Array.from(b).map((x) => x.toString(16).padStart(2, "0")).join("");
  const keccak256 = (hexOrBytes) => bytesToHex(keccak256Bytes(typeof hexOrBytes === "string" ? hexToBytes(hexOrBytes) : hexOrBytes));

  // CREATE2 address = keccak256(0xff ++ deployer ++ salt ++ keccak256(initCode))[12:]
  function create2Address(deployer, salt, initCodeHex) {
    const initHash = keccak256(initCodeHex).slice(2);
    const pre = "ff" + deployer.replace(/^0x/i, "").toLowerCase() + salt.replace(/^0x/i, "") + initHash;
    return "0x" + keccak256("0x" + pre).slice(-40);
  }
  // CREATE address = keccak256(rlp([sender, nonce]))[12:]
  function createAddress(sender, nonce) {
    const s = sender.replace(/^0x/i, "").toLowerCase();
    let nb;
    if (nonce === 0) nb = "80";
    else if (nonce <= 0x7f) nb = nonce.toString(16).padStart(2, "0");
    else { let h = nonce.toString(16); if (h.length % 2) h = "0" + h; const len = h.length / 2; nb = (0x80 + len).toString(16) + h; }
    const addrItem = "94" + s;                       // 0x80+0x14 ++ 20-byte address
    const payload = addrItem + nb;
    const plen = payload.length / 2;
    const prefix = (0xc0 + plen).toString(16).padStart(2, "0");
    return "0x" + keccak256("0x" + prefix + payload).slice(-40);
  }

  // self-test against known Keccak-256 vectors (logs a warning if the impl is wrong).
  function selfTest() {
    const empty = keccak256("0x");
    const ok = empty === "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470";
    if (!ok) console.error("keccak.js self-test FAILED:", empty);
    return ok;
  }

  window.BankonKeccak = { keccak256, create2Address, createAddress, selfTest };
  selfTest();
})();
