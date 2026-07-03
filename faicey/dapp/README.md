# SoundWave voiceprint dApp

ABI-driven dApp for **SoundWave (SND / WAV)** — register forensic voiceprints (18-decimal
precision) and mint WAV. Pure-JS prototype; the production target is `.ts` / `.tsx`.

## Convention (index.html · dapp.js · abi.js)

Follows the bankoneth pattern so a contract change is a one-file swap:

```
dapp/
├── index.html                  landing + dApp shell
├── dapp.js                     generic, ABI-driven interaction (functionality)
├── abi-codec.js                in-house ABI encode/decode (no ethers, no CDN)
├── deltaverse.js               WebGL participant field (stars = voiceprints)
├── styled.css / styled.scss    cypherpunk2048 styling
├── abis/<Contract>.abi.js      ← AUTO-GENERATED ABI + selectors (swap to change contract)
├── deployments/<chainId>.json  ← AUTO-GENERATED addresses (kept OUT of the abi)
└── contracts.json              manifest the UI loads
```

- **`abi.js` changes with each contract.** `dapp.js` reads it generically and renders every
  function (reads → call buttons, writes → forms). To point the UI at another contract, swap
  the `abis/<Name>.abi.js` file — no UI edits.
- **Addresses are separate.** A redeploy only rewrites `deployments/<chainId>.json`; the abi.js
  and UI are untouched.
- **No CDN, no ethers.** Calldata is encoded by `abi-codec.js`; method selectors come precomputed
  from the Foundry artifact (so the browser never needs keccak); transport is `window.ethereum`.

## Build & deploy (Foundry preferred for local; Hardhat template for deploy)

```bash
cd ../contracts
forge build && forge test                      # Foundry — preferred local testing
node script/export-abis.mjs                    # → dapp/abis/*.abi.js + contracts.json

# local chain = anvil (preferred):
anvil &
forge script script/DeploySoundWave.s.sol --rpc-url http://127.0.0.1:8545 --broadcast \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
node script/export-abis.mjs                     # auto-includes the deployed address

# OR Hardhat (deployment template) — also auto-exports the address:
cd hardhat && npx hardhat run scripts/deploy.js --network localhost
```

Then serve `dapp/` statically and open `index.html`.

## Forensic voiceprints (SCIENTIFIC, 18 decimals)

The six acoustic measures come from voaice's **Scientific** tool (`voaice/src/Scientific.js`),
each `real_value × 1e18`, hashed (sha256) into a reproducible, unique voiceprint:

```js
import { Scientific } from 'voaice';
const sci = new Scientific({ sampleRate: 44100 });
const m = sci.measure(frame);                  // frame: Float32Array in [-1,1]
const { hash, sampleRate, m: measures, precisionScore } = sci.toRegisterArgs(m);
// → SoundWaveToken.registerVoicePrint(hash, sampleRate, measures, precisionScore)
```

## DeltaVerse participant field

`deltaverse.js` renders each registered voiceprint as a star (hue = dominant frequency,
size = precision) in a WebGL field (`GL_POINTS`, 2D-canvas fallback) — stars are participants.

## cypherpunk2048

Crypto-agile / PQ-ready posture (Tier-A): no PQ-washing; the EVM surface is crypto-agile and
ready for a post-quantum signature swap. See the cypherpunk2048 quantum-resistance standard.
