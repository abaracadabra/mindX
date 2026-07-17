/**
 * inft.js — mint a faicey FACE / VOICE / persona as a DeltaVerse iNFT (ERC-7857).
 *
 * The old "NFT minter" only wrote OpenSea metadata. This binds a faicey artifact
 * to the DeltaVerse Intelligent-NFT contract (daio/contracts/inft/iNFT_7857.sol):
 * an ERC-7857 iNFT wraps INTELLIGENCE — a content root, its storage URI, its
 * dimensions — and optionally a THOT root (mindX's memory lineage). A faceprint,
 * a voiceprint, or a bound persona IS that intelligence: an 18-dp measurement
 * vector with a reproducible hash. So the print's hash becomes the iNFT's
 * `contentRoot`, and `mintAgent(...)` args fall straight out.
 *
 *   import { toInftMint } from './inft.js';
 *   const payload = await toInftMint(personaPrintOrFaceprint, {
 *     to: '0xowner', storageURI: 'ipfs://…', thotRoot: '0x…',
 *   });
 *   // → { standard:'ERC-7857', mintAgent:{ to, contentRoot, storageURI,
 *   //      metadataRoot, dimensions, parallelUnits, sealedKeyHash, tokenURI },
 *   //     attachThotRoot?, metadata }
 *
 * The payload is the exact argument set the iNFT_7857.mintAgent() call takes,
 * plus the OpenSea tokenURI metadata. Hand it to the DeltaVerse deployer/minter
 * or POST it to the blockchain agent factory. Pure JS, browser + Node.
 *
 * © Professor Codephreak - rage.pythai.net
 */

// ERC-7857 accepts these embedding dimensions only (iNFT_7857._isValidDimension).
export const VALID_DIMENSIONS = [8, 64, 256, 512, 768, 1024, 2048, 4096, 8192, 65536, 1048576];

/** Smallest valid iNFT dimension that holds `n` measures. */
export function dimensionFor(n) {
  for (const d of VALID_DIMENSIONS) if (d >= n) return d;
  return VALID_DIMENSIONS[VALID_DIMENSIONS.length - 1];
}

async function sha256Hex(str) {
  if (typeof process !== 'undefined' && process.versions?.node) {
    const { createHash } = await import('node:crypto');
    return '0x' + createHash('sha256').update(str).digest('hex');
  }
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return '0x' + [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

const isBytes32 = (h) => typeof h === 'string' && /^0x[0-9a-fA-F]{64}$/.test(h);

/** Read the hash / measures / kind out of any faicey print (face, voice, persona). */
function normalize(artifact) {
  if (!artifact) throw new Error('inft: nothing to mint');
  const hash = artifact.hash;
  if (!isBytes32(hash)) throw new Error('inft: artifact needs a 32-byte hash (0x + 64 hex)');
  const measures = artifact.measuresStr || artifact.registerArgs?.m || [];
  const modalities = artifact.modalities // persona print
    || (artifact.measureNames?.length ? ['face'] : artifact.features ? ['voice'] : []);
  const kind = artifact.kind
    || (modalities.includes('face') && modalities.includes('voice') ? 'persona'
      : modalities[0] || 'faceprint');
  const precisionScore = artifact.precisionScore != null ? String(artifact.precisionScore)
    : artifact.registerArgs?.precisionScore != null ? String(artifact.registerArgs.precisionScore) : '0';
  return { hash, measures, modalities, kind, precisionScore };
}

/**
 * Build a DeltaVerse iNFT-7857 mint payload from a faicey print.
 * @param {object} artifact  a faceprint / voiceprint / personaPrint (with .hash)
 * @param {{to?:string, storageURI?:string, tokenURI?:string, thotRoot?:string,
 *          parallelUnits?:number, sealedKeyHash?:string, name?:string,
 *          description?:string, image?:string, chainId?:number}} [opts]
 */
export async function toInftMint(artifact, opts = {}) {
  const a = normalize(artifact);
  const contentRoot = a.hash; // the print hash IS the intelligence content root

  const dimensions = dimensionFor(a.measures.length || 8);
  const parallelUnits = Math.max(1, opts.parallelUnits ?? 1);
  const storageURI = opts.storageURI || `faicey:${a.kind}/${contentRoot.slice(2, 18)}`;

  // metadata — OpenSea-shaped, and carries the on-chain-verifiable print fields
  const metadata = {
    name: opts.name || `${a.kind[0].toUpperCase() + a.kind.slice(1)} · ${contentRoot.slice(2, 10)}`,
    description: opts.description ||
      `A faicey ${a.kind} bound as a DeltaVerse iNFT (ERC-7857): 18-decimal ${a.modalities.join(' + ') || a.kind} measures with a reproducible signature.`,
    image: opts.image || undefined,
    attributes: [
      { trait_type: 'standard', value: 'ERC-7857' },
      { trait_type: 'kind', value: a.kind },
      { trait_type: 'modalities', value: (a.modalities.join('+') || a.kind) },
      { trait_type: 'dimensions', value: dimensions },
      { trait_type: 'precision', value: (Number(a.precisionScore) / 1e18).toFixed(3) },
    ],
    // the verifiable payload — the measures + the contentRoot they hash to
    faicey: { contentRoot, kind: a.kind, modalities: a.modalities, measures: a.measures,
      registerArgs: artifact.registerArgs || null },
  };
  const metadataRoot = await sha256Hex(JSON.stringify(metadata.faicey));
  // sealedKey: the content here is PUBLIC (a measurement, not secret material), so
  // the sealed-key hash is a deterministic commitment, not an encryption secret.
  const sealedKeyHash = opts.sealedKeyHash || (await sha256Hex('faicey-public:' + contentRoot));
  const tokenURI = opts.tokenURI || ('data:application/json;base64,' + b64(JSON.stringify(metadata)));

  const payload = {
    standard: 'ERC-7857',
    contract: 'iNFT_7857',
    source: 'DeltaVerse/contracts-evm/cognition-inft/iNFT_7857.sol',
    chainId: opts.chainId ?? null,
    mintAgent: {
      to: opts.to || null, // the owner — required at mint time
      contentRoot,
      storageURI,
      metadataRoot,
      dimensions,
      parallelUnits,
      sealedKeyHash,
      tokenURI_: tokenURI,
    },
    metadata,
  };
  // link the mind's memory lineage, if a THOT root was supplied
  if (opts.thotRoot) {
    if (!isBytes32(opts.thotRoot)) throw new Error('inft: thotRoot must be a 32-byte hash');
    payload.attachThotRoot = { thotRoot: opts.thotRoot };
  }
  return payload;
}

/** base64 that works in Node and the browser. */
function b64(s) {
  if (typeof Buffer !== 'undefined') return Buffer.from(s, 'utf8').toString('base64');
  return btoa(unescape(encodeURIComponent(s)));
}

export default toInftMint;
