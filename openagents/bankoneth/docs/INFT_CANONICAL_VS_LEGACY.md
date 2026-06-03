# iNFT: canonical (`contracts/inft7857/`) vs legacy (`contracts/inft/iNFT_7857.sol`)

Two iNFT implementations coexist — both kept, the canonical one is the extensible path.

| | **Legacy** `contracts/inft/iNFT_7857.sol` | **Canonical** `contracts/inft7857/bankon_inft_subname.sol` |
|---|---|---|
| Origin | custom mindX design (copied from daio) | ported from the BANKON ERC-7857+6551 spec |
| Transfer | `transferWithSealedKey(from,to,id,bytes,bytes)` | `iTransfer(to,id,TransferValidityProof[])` (canonical) |
| Clone | `cloneAgent(id,to,bytes,bytes)` | `iClone(to,id,TransferValidityProof[])` |
| Verifier | inline ECDSA oracle signer | pluggable `verifier() → IERC7857DataVerifier` (`OracleType{TEE,ZKP}`) |
| Metadata | event-based | `intelligentDataOf(id) → IntelligentData[]` |
| TBA | via `BankonInftAdapter` (operator-attested) | native ERC-6551 (`bankon_tba_account` + registry proxy) |
| ENS | adapter binding | NameWrapper-backed at mint (`mintUnified`) |
| Standards | ERC-721 + custom | ERC-721 + 7857 + 5192 + 2981 + 4906 + 7572 |
| Chain | 0G Galileo 16601 (dApp) | + 0G Aristotle mainnet 16661 |

**Use the canonical stack** for new work — it's marketplace-interoperable (OpenSea reads ERC-721 +
2981 + 5192 + 4906 + 7572), TBA-native, and modular. The legacy contract stays for the existing
`inft.html` page + `BankonInftAdapter` wiring + its 143-fn ABI; not removed.

The dApp surfaces both: `inft.html` (legacy, 0G page) and `name-service.html` (canonical, ERC-6551).
