# bankoneth — Canonical ENS Addresses Reference

Pinned at the time of writing. **Verify against
[`docs.ens.domains/learn/deployments`](https://docs.ens.domains/learn/deployments)
before every mainnet deployment.** The two ENS spec docs we built bankoneth
from cited some Sepolia addresses as if they were mainnet — caveat lector.

The `DeployEthereum.s.sol` script's `_verifyChainAddresses` function asserts
the two most critical addresses (`NameWrapper`, `ETHRegistrarController`)
against the values below. Mismatch reverts the deploy.

## Ethereum mainnet (chain id 1)

| Contract | Address |
|---|---|
| `ENSRegistry` | `0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e` |
| `BaseRegistrarImplementation` (.eth ERC-721) | `0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85` |
| `ETHRegistrarController` | `0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547` |
| `NameWrapper` | `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401` |
| `PublicResolver` | `0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63` |
| `ReverseRegistrar` | `0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb` |
| USDC (ERC-20) | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| ERC-6551 Registry (singleton) | `0x000000006551c19487814612e58FE06813775758` |

## Sepolia (chain id 11_155_111)

| Contract | Address |
|---|---|
| `NameWrapper` | `0x0635513f179D50A207757E05759CbD106d7dFcE8` |
| `ETHRegistrarController` | `0xfb3cE5D01e0f33f41DbB39035dB9745962F1f968` |

(Used by the rehearsal deploy with `ALLOW_TESTNET=true`.)

## 0G (Galileo testnet)

| Detail | Value |
|---|---|
| Chain id | `16601` |
| Native gas | ZG |

Some 0G docs cited `16602`; the canonical value as of May 2026 is `16601`.
Re-verify before each testnet deploy.

## Algorand mainnet

| Detail | Value |
|---|---|
| USDC ASA id | `31566704` |
| NFD V3 registry app id | `760937186` |
| CAIP-2 | `algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=` |

GoPlausible's CAIP-2 uses non-standard characters (`/`, `+`, `=`); strict
parsers may need to widen the regex.

## ERC-7857 reference

| Detail | Value |
|---|---|
| Repo | `github.com/0gfoundation/0g-agent-nft` |
| Branch (authoritative draft) | `eip-7857-draft` |
| Commit (pinned at vendor time) | (operator: fill in at vendor time) |

ERC-7857 is still draft. Pin a specific commit hash when forking; subscribe
to the EIPs RFC changes — selectors and the `TransferValidityProof` struct
layout may change before finalization.
