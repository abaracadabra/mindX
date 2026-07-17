/**
 * minter.js — wire a faicey iNFT payload to the DeltaVerse minter.
 *
 * `inft.js` builds the ERC-7857 mint PAYLOAD (the mintAgent argument set).
 * This turns that payload into a ready-to-broadcast TRANSACTION: the `to`
 * (contract address), the ABI-encoded `data` (selector + args), and the chain —
 * exactly what a wallet's `eth_sendTransaction` or viem's `sendTransaction`
 * takes. It does NOT submit anything: signing and broadcasting is the wallet
 * owner's action (the OVERLORD's ceremony, or a user approving in MetaMask).
 *
 *   import { toMintTx } from './minter.js';
 *   const tx = toMintTx(payload, { contract: '0xCf7…', chainId: 31337 });
 *   // → { mint: { to, data, value:'0x0', chainId, functionName, args },
 *   //     attachThot?: (tokenId) => { to, data, ... } }
 *   await window.ethereum.request({ method:'eth_sendTransaction',
 *     params:[{ from: owner, to: tx.mint.to, data: tx.mint.data }] });
 *
 * A minimal, self-contained ABI encoder handles exactly the two functions used
 * (selectors taken from the compiled artifact, so no keccak is needed in the
 * browser). Pure JS, browser + Node.
 *
 * © Professor Codephreak - rage.pythai.net
 */

// Selectors from daio/contracts/out/iNFT_7857.sol/iNFT_7857.json (methodIdentifiers).
export const SELECTORS = {
  mintAgent: '0xbabb11b9',      // mintAgent(address,bytes32,string,bytes32,uint32,uint8,bytes32,string)
  attachThotRoot: '0xbc7aa9eb', // attachThotRoot(uint256,bytes32)
};

const strip0x = (h) => (h.startsWith('0x') ? h.slice(2) : h);
const pad32 = (hex) => hex.padStart(64, '0');
const bytes32 = (h) => { const s = strip0x(h).toLowerCase(); if (s.length !== 64) throw new Error(`not bytes32: ${h}`); return s; };
const uintHex = (n) => pad32(BigInt(n).toString(16));
const addr = (a) => { const s = strip0x(a).toLowerCase(); if (s.length !== 40 || !/^[0-9a-f]{40}$/.test(s)) throw new Error(`not an address: ${a}`); return pad32(s); };

/** ABI-encode a UTF-8 string: 32-byte length + right-padded data. */
function encodeString(str) {
  const bytes = new TextEncoder().encode(str);
  let hex = '';
  for (const b of bytes) hex += b.toString(16).padStart(2, '0');
  const len = uintHex(bytes.length);
  const padded = hex.length % 64 === 0 ? hex : hex.padEnd(hex.length + (64 - (hex.length % 64)), '0');
  return { len, data: padded, words: 1 + padded.length / 64 };
}

/**
 * Encode mintAgent(address,bytes32,string,bytes32,uint32,uint8,bytes32,string).
 * Head = 8 × 32 bytes (dynamic strings become offset pointers); tail = the
 * two strings. Offsets are relative to the start of the argument block.
 */
export function encodeMintAgent(m) {
  const storage = encodeString(m.storageURI);
  const token = encodeString(m.tokenURI_);
  const HEAD = 8 * 32;                       // 8 head words, bytes
  const offStorage = HEAD;                   // first dynamic
  const offToken = HEAD + (1 + (storage.words - 1)) * 32; // after storage len+data
  const head =
    addr(m.to) +
    bytes32(m.contentRoot) +
    uintHex(offStorage) +
    bytes32(m.metadataRoot) +
    uintHex(m.dimensions) +
    uintHex(m.parallelUnits) +
    bytes32(m.sealedKeyHash) +
    uintHex(offToken);
  const tail = storage.len + storage.data + token.len + token.data;
  return SELECTORS.mintAgent + head + tail;
}

/** Encode attachThotRoot(uint256 tokenId, bytes32 thotRoot). */
export function encodeAttachThot(tokenId, thotRoot) {
  return SELECTORS.attachThotRoot + uintHex(tokenId) + bytes32(thotRoot);
}

/**
 * Build the transaction(s) that mint this payload on the DeltaVerse iNFT_7857.
 * @param {object} payload  from toInftMint()
 * @param {{contract:string, chainId?:number, from?:string}} opts
 *   contract — the deployed iNFT_7857 address (required)
 * @returns {{mint:object, attachThot?:Function, contract:string, chainId:number|null}}
 */
export function toMintTx(payload, opts = {}) {
  if (payload?.standard !== 'ERC-7857') throw new Error('minter: not an ERC-7857 payload');
  const contract = opts.contract;
  if (!contract) throw new Error('minter: the deployed iNFT_7857 contract address is required');
  const m = { ...payload.mintAgent };
  if (opts.from && !m.to) m.to = opts.from; // default the owner to the sender
  if (!m.to) throw new Error('minter: mintAgent.to (owner) must be set');
  const chainId = opts.chainId ?? payload.chainId ?? null;

  const data = encodeMintAgent(m);
  const mint = {
    to: contract, from: opts.from || undefined, data, value: '0x0', chainId,
    functionName: 'mintAgent',
    // viem/ethers-friendly: the same call as { abi, functionName, args }
    args: [m.to, m.contentRoot, m.storageURI, m.metadataRoot, m.dimensions, m.parallelUnits, m.sealedKeyHash, m.tokenURI_],
  };

  const out = { contract, chainId, mint };
  // the THOT-lineage link is a SECOND tx — it needs the tokenId the mint returns
  if (payload.attachThotRoot?.thotRoot) {
    const thotRoot = payload.attachThotRoot.thotRoot;
    out.attachThot = (tokenId) => ({ to: contract, from: opts.from || undefined,
      data: encodeAttachThot(tokenId, thotRoot), value: '0x0', chainId,
      functionName: 'attachThotRoot', args: [String(tokenId), thotRoot] });
  }
  return out;
}

/** Minimal ABI fragment for the two calls (for viem/ethers callers). */
export const IINFT_ABI = [
  { type: 'function', name: 'mintAgent', stateMutability: 'nonpayable',
    inputs: [
      { name: 'to', type: 'address' }, { name: 'contentRoot', type: 'bytes32' },
      { name: 'storageURI', type: 'string' }, { name: 'metadataRoot', type: 'bytes32' },
      { name: 'dimensions', type: 'uint32' }, { name: 'parallelUnits', type: 'uint8' },
      { name: 'sealedKeyHash', type: 'bytes32' }, { name: 'tokenURI_', type: 'string' },
    ], outputs: [{ name: 'tokenId', type: 'uint256' }] },
  { type: 'function', name: 'attachThotRoot', stateMutability: 'nonpayable',
    inputs: [{ name: 'tokenId', type: 'uint256' }, { name: 'thotRoot', type: 'bytes32' }], outputs: [] },
];

export default toMintTx;
