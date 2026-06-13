/**
 * iDEBT SDK — a high-level facade over the contract clients and the three
 * off-chain services. Consumers typically use this directly rather than
 * touching the lower-level clients individually.
 */

import {
  type Address,
  type Hex,
  type PublicClient,
  type WalletClient,
  encodeAbiParameters,
  keccak256,
  parseAbiParameters
} from "viem";

import { MindXClient } from "./mindx-client.js";
import { AgenticPlaceClient } from "./agenticplace-client.js";
import { BANKONClient } from "./bankon-client.js";
import { ParsecX402Client, type X402ReceiptBundle } from "./parsec-x402-client.js";
import { chainOf } from "./chainmap.js";

export interface IDebtAddresses {
  oracle:    Address;
  index:     Address;
  debtToken: Address;
  x402:      Address;
  mindx:     Address;
  agents:    Address;
  bankon:    Address;
  governor:  Address;
  treasury:  Address;
  voteToken: Address;
}

export interface HeirInput {
  successor: Address;
  sharesBps: number; // 0..10_000
}

export interface IDebtSDKOptions {
  publicClient: PublicClient;
  walletClient?: WalletClient;
  addresses: IDebtAddresses;
  mindx?: MindXClient;
  agents?: AgenticPlaceClient;
  bankon?: BANKONClient;
  x402?: ParsecX402Client;
}

export const SCOPE_OPEN  = keccak256(new TextEncoder().encode("iDEBT.open"))  as Hex;
export const SCOPE_CLAIM = keccak256(new TextEncoder().encode("iDEBT.claim")) as Hex;

export class IDebtSDK {
  readonly publicClient: PublicClient;
  readonly walletClient?: WalletClient;
  readonly addresses: IDebtAddresses;

  readonly mindx:  MindXClient;
  readonly agents: AgenticPlaceClient;
  readonly bankon: BANKONClient;
  readonly x402:   ParsecX402Client;

  constructor(opts: IDebtSDKOptions) {
    this.publicClient = opts.publicClient;
    this.walletClient = opts.walletClient;
    this.addresses    = opts.addresses;
    this.mindx  = opts.mindx  ?? new MindXClient();
    this.agents = opts.agents ?? new AgenticPlaceClient();
    this.bankon = opts.bankon ?? new BANKONClient();
    this.x402   = opts.x402   ?? new ParsecX402Client();
  }

  // -------------------------------------------------------------- //
  //                          HEIR HELPERS                          //
  // -------------------------------------------------------------- //

  /** Hash a single heir tuple into a Merkle leaf. */
  static heirLeaf(h: HeirInput): Hex {
    return keccak256(
      encodeAbiParameters(parseAbiParameters("address, uint16"), [h.successor, h.sharesBps])
    );
  }

  /** Build a sorted-pair Merkle root from heir tuples. Returns root + per-leaf proof. */
  static buildHeirTree(heirs: HeirInput[]): { root: Hex; proofs: Hex[][]; leaves: Hex[] } {
    if (heirs.length === 0) throw new Error("no heirs");
    const leaves = heirs.map(IDebtSDK.heirLeaf);
    const levels: Hex[][] = [leaves];
    while (levels[levels.length - 1]!.length > 1) {
      const cur = levels[levels.length - 1]!;
      const next: Hex[] = [];
      for (let i = 0; i < cur.length; i += 2) {
        const a = cur[i]!;
        const b = cur[i + 1] ?? a;
        next.push(
          a < b
            ? keccak256(`0x${a.slice(2)}${b.slice(2)}` as Hex)
            : keccak256(`0x${b.slice(2)}${a.slice(2)}` as Hex)
        );
      }
      levels.push(next);
    }
    const root = levels[levels.length - 1]![0]!;
    const proofs: Hex[][] = leaves.map((_, idx) => {
      const path: Hex[] = [];
      let i = idx;
      for (let lvl = 0; lvl < levels.length - 1; ++lvl) {
        const cur = levels[lvl]!;
        const sib = i % 2 === 0 ? cur[i + 1] ?? cur[i]! : cur[i - 1]!;
        path.push(sib);
        i = Math.floor(i / 2);
      }
      return path;
    });
    return { root, proofs, leaves };
  }

  /** Encode the `heirProof` bytes parameter expected by `iDEBT.claimInheritance`. */
  static encodeHeirProof(heir: HeirInput, proof: Hex[]): Hex {
    return encodeAbiParameters(
      parseAbiParameters("address, uint16, bytes32[]"),
      [heir.successor, heir.sharesBps, proof]
    );
  }

  // -------------------------------------------------------------- //
  //                         X402 SHORTCUTS                         //
  // -------------------------------------------------------------- //

  /** Whole x402 flow for a scope: create intent → wait for receipt → `consume`. */
  async payScope(scope: Hex, chainId: number): Promise<X402ReceiptBundle> {
    if (!this.walletClient?.account) throw new Error("walletClient with account required");
    const payer = this.walletClient.account.address;
    if (!chainOf(chainId)) throw new Error(`unknown chainId ${chainId}`);

    const { bundle } = await this.x402.payAndResolve(payer, scope, chainId);
    return bundle;
  }

  // -------------------------------------------------------------- //
  //                          READ HELPERS                          //
  // -------------------------------------------------------------- //

  /** Read the live stress score from the index. */
  async stressScore(): Promise<bigint> {
    return (await this.publicClient.readContract({
      address: this.addresses.index,
      abi: [{
        type: "function", name: "score", stateMutability: "view",
        inputs: [], outputs: [{ type: "uint256" }]
      }],
      functionName: "score"
    })) as bigint;
  }
}

export { MindXClient } from "./mindx-client.js";
export { AgenticPlaceClient } from "./agenticplace-client.js";
export { BANKONClient } from "./bankon-client.js";
export { ParsecX402Client, type X402ReceiptBundle, type X402Receipt, type X402Price, type X402PaymentIntent } from "./parsec-x402-client.js";
export * as Chainmap from "./chainmap.js";
