# Example: claim alice.bankon.eth

Reproducible snippet for the canonical Flow A claim.

## Via curl + viem

```bash
# 1. Quote the price
forge call --rpc-url $MAINNET_RPC $BANKON_PRICE_ORACLE \
  "priceUSD(string,uint256)(uint256)" "alice" 1
# → 5000000  (== $5.00 USD per year, 6-decimal)

# 2. Claim via the CLI
bankoneth claim alice --duration 1 --rail eth --inft --list
# → tx: 0x<hash>
```

## Via @bankoneth/core in TypeScript

```ts
import { createPublicClient, createWalletClient, http, custom, namehash } from "viem";
import { mainnet } from "viem/chains";
import { BankonethClient } from "@bankoneth/core";

const publicClient = createPublicClient({ chain: mainnet, transport: http() });
const walletClient = createWalletClient({ chain: mainnet, transport: custom((window as any).ethereum) });
const [owner] = await walletClient.getAddresses();

const client = new BankonethClient(
  publicClient,
  walletClient,
  /* addresses */ JSON.parse(fs.readFileSync("./bankoneth-addresses.json", "utf-8")),
  namehash("bankon.eth"),
);

const tx = await client.claim({
  label: "alice",
  owner,
  durationYears: 1,
  payment: "eth",
  inftModeA: true,
  listOnAgenticPlace: true,
});
console.log("tx:", tx);
```

## Verifying the resolution

```bash
# Confirm the resolver returns the deterministic ERC-6551 TBA
forge call --rpc-url $MAINNET_RPC $BANKON_RESOLVER \
  "addr(bytes32)(address)" $(cast namehash "alice.bankon.eth")
# → 0x<tba-address>

# Confirm the TBA on 0G holds the agent identity
forge call --rpc-url $ZEROG_RPC $ZEROG_INFT \
  "ownerOf(uint256)(address)" <tokenId-from-event>
```
