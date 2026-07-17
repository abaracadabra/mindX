# faicey → DeltaVerse iNFT minting (ERC-7857)

A faicey artifact — a **faceprint**, a **voiceprint**, or a **bound `.persona`** —
becomes an on-chain Intelligent NFT on the DeltaVerse `iNFT_7857` contract. The
print's reproducible hash *is* the token's `contentRoot`, so what is minted is
the exact, verifiable identity faicey measured — not a picture of it.

Two modules cover the path, and the boundary between them is deliberate:

| module | turns … | into … |
|--------|---------|--------|
| `src/face_clone/inft.js` | a faicey artifact | the ERC-7857 mint **payload** (the `mintAgent` argument set) |
| `src/face_clone/minter.js` | that payload | a ready-to-broadcast **transaction** (`to` + ABI-encoded `data` + chain) |

**faicey builds the transaction. The wallet owner signs and broadcasts it.**
Nothing here holds a key or submits anything — the mint is the owner's action,
in their own wallet (a user in MetaMask, or the OVERLORD's ceremony).

---

## 1. The payload — `inft.js`

```js
import { toInftMint } from './src/face_clone/inft.js';

const payload = await toInftMint(artifact, {
  to: '0x…',                    // owner (optional here — can default to the sender later)
  storageURI: 'ipfs://Qm…',     // where the sealed artifact lives
  thotRoot: '0x…',              // optional: mindX memory-lineage root
  name: 'Jaimla',               // travels in the tokenURI metadata
});
```

`toInftMint()` returns an ERC-7857 payload:

```js
{
  standard: 'ERC-7857',
  mintAgent: {
    to, contentRoot, storageURI, metadataRoot,
    dimensions, parallelUnits, sealedKeyHash, tokenURI_,
  },
  attachThotRoot: { thotRoot } | undefined,
  chainId,
}
```

- **`contentRoot`** — the artifact's reproducible sha256. The print hash *is* the
  content root, so the chain anchors the measured identity, byte-for-byte.
- **`dimensions`** — a valid ERC-7857 embedding dimension. `dimensionFor(n)` snaps
  a measurement-vector length to the nearest valid size in `VALID_DIMENSIONS`
  (`8 · 64 · 256 · 512 · 768 · 1024 · 2048 · 4096 · 8192 · 65536 · 1048576`).
- The measurement vector travels in the **tokenURI** metadata — the token is
  self-describing.

---

## 2. The transaction — `minter.js`

```js
import { toMintTx } from './src/face_clone/minter.js';

const tx = toMintTx(payload, {
  contract: '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9', // the deployed iNFT_7857
  chainId: 31337,
  from: ownerAddress,     // optional — defaults the owner (mintAgent.to) to the sender
});
```

returns:

```js
{
  contract, chainId,
  mint: {
    to: contract,          // the iNFT contract
    data: '0xbabb11b9…',   // selector + ABI-encoded mintAgent args
    value: '0x0',
    chainId,
    functionName: 'mintAgent',
    args: [ /* the 8 mintAgent args, for a viem/ethers caller */ ],
  },
  attachThot?: (tokenId) => ({ … }),   // present only when the payload carries a thotRoot
}
```

Broadcast it with whatever the owner's wallet uses:

```js
// browser wallet
await window.ethereum.request({
  method: 'eth_sendTransaction',
  params: [{ from: owner, to: tx.mint.to, data: tx.mint.data }],
});

// or viem / ethers — the { functionName, args } form is ready for encodeFunctionData
```

A `thotRoot` becomes a **second** transaction: `attachThotRoot(tokenId, root)`,
run *after* the mint returns its `tokenId`, to link mindX's memory lineage to the
freshly minted agent.

### The ABI encoder

`minter.js` ships a minimal, self-contained ABI encoder for exactly the two calls
used, with the function selectors read straight from the compiled artifact
(`daio/contracts/out/iNFT_7857.sol/iNFT_7857.json`):

| function | selector |
|----------|----------|
| `mintAgent(address,bytes32,string,bytes32,uint32,uint8,bytes32,string)` | `0xbabb11b9` |
| `attachThotRoot(uint256,bytes32)` | `0xbc7aa9eb` |

Because the selectors are precompiled, **no keccak is needed in the browser**. The
encoder was **cross-checked byte-for-byte against [viem](https://viem.sh)**, and
`src/face_clone/minter.test.js` locks it in-repo with a round-trip decoder: it
encodes a real payload, decodes the calldata back, and asserts every argument
survives — proof the bytes a wallet would broadcast are a real, valid transaction.

`IINFT_ABI` (a two-function fragment) is exported for viem/ethers callers who
would rather encode through the ABI than take the pre-encoded `data`.

---

## 3. In the live demo

The `/face` demo carries the whole path as two buttons:

- **`⬡ iNFT payload`** — binds the current persona as an ERC-7857 payload,
  client-side, and downloads it.
- **`⛓ mint`** — connects the browser wallet, builds the transaction with
  `toMintTx`, and submits it for the owner to **sign and approve**
  (`eth_requestAccounts` → `eth_sendTransaction`). The deployed contract address
  is editable and defaults to the recognised `iNFT_7857`.

On the server, `POST /api/inft/mint-payload` builds a payload from a posted
print/persona (for the blockchain agent factory).

---

## Deployment status

The `iNFT_7857` contract is deployed on the local anvil chain (`31337`) at
`0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9`. **Mainnet is not yet deployed** —
the mainnet mint awaits the OVERLORD deployment ceremony. Until then the payload
and the transaction are fully exercised against the local chain, and the encoder
is proven against viem regardless of where it broadcasts.

---

## Verification

```
node src/face_clone/inft.test.js      # payload shape, dimension snapping, hash = contentRoot
node src/face_clone/minter.test.js    # calldata round-trips; thot follow-up; owner defaults to sender
```

See [FACE_CLONE.md](./FACE_CLONE.md) for the print pipeline that produces the
artifact, and the [CHANGELOG](../CHANGELOG.md) (`2.4.0` payload · `2.5.0` minter).
