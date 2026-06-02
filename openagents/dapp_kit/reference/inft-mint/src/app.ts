// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// iNFT_7857 mint reference dApp. Exercises:
//   1. EIP-6963 wallet connection
//   2. switchChain → 0G Galileo (16601)
//   3. contractsFor('0g-galileo') → iNFT_7857
//   4. write.mint(parentRoot, cid, sealedMetadata)
//   5. tx receipt + on-chain event decoding
//
// Reads the deployment record from /deployments/0g-galileo.json
// (publicly served by Vite from the public/ dir).
//
// Contract spec composition:
//   docs/services/wallet_connection_as_a_service.md  (steps 1-2)
//   docs/services/contract_interaction_as_a_service.md  (steps 3-5)

import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import {
  connect,
  switchChain,
  type ConnectedAccount,
  WalletNotFound,
  WalletRejected,
  ChainAddRequired,
  addChain,
} from "@openagents/wallet";
import { contractsFor, type ContractsRegistry } from "@openagents/contracts";
import type { Address, Hash, Hex } from "viem";

@customElement("inft-mint-app")
export class InftMintApp extends LitElement {
  static styles = css`
    :host { display: block; }
    h1 { font-weight: 600; letter-spacing: 0.5px; }
    .step {
      border-left: 3px solid var(--muted, #4a5060);
      padding: 12px 16px;
      margin: 16px 0;
      background: rgba(255, 255, 255, 0.02);
      border-radius: 0 4px 4px 0;
    }
    .step.active { border-left-color: var(--accent, #8be9fd); }
    .step.done   { border-left-color: #50fa7b; }
    label { display: block; margin: 8px 0 4px; font-size: 12px; color: var(--muted, #4a5060); text-transform: uppercase; letter-spacing: 0.5px; }
    input {
      width: 100%;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--fg, #e6edf3);
      border-radius: 4px;
      font-family: ui-monospace, monospace;
      font-size: 13px;
    }
    button {
      background: var(--accent, #8be9fd);
      color: #0a0a0f;
      border: 0;
      padding: 10px 18px;
      border-radius: 4px;
      font-weight: 600;
      cursor: pointer;
      margin-top: 12px;
      font-size: 14px;
    }
    button[disabled] { opacity: 0.4; cursor: not-allowed; }
    .error { color: #ff6b6b; margin-top: 12px; font-size: 13px; }
    pre {
      background: rgba(255, 255, 255, 0.03);
      padding: 12px;
      border-radius: 4px;
      overflow-x: auto;
      font-size: 12px;
      margin-top: 12px;
    }
  `;

  @state() account?: ConnectedAccount;
  @state() registry?: ContractsRegistry;
  @state() parentRoot = "0x" + "1".repeat(64);
  @state() cid = "bafkrei" + "z".repeat(50);
  @state() sealedHex = "0x";
  @state() txHash?: Hash;
  @state() tokenId?: bigint;
  @state() error?: string;
  @state() running = false;

  private async step1Connect() {
    this.error = undefined;
    this.running = true;
    try {
      const acct = await connect();
      this.account = acct;
    } catch (err) {
      if (err instanceof WalletNotFound) {
        this.error = "No wallet found. Install MetaMask, Coinbase Wallet, or another EIP-6963 wallet.";
      } else if (err instanceof WalletRejected) {
        this.error = "You rejected the connection request.";
      } else {
        this.error = err instanceof Error ? err.message : String(err);
      }
    } finally {
      this.running = false;
    }
  }

  private async step2Switch() {
    if (!this.account) return;
    this.error = undefined;
    this.running = true;
    try {
      try {
        this.account = await switchChain(this.account, "0g-galileo");
      } catch (e) {
        if (e instanceof ChainAddRequired) {
          await addChain(this.account, "0g-galileo");
          this.account = await switchChain(this.account, "0g-galileo");
        } else {
          throw e;
        }
      }
      this.registry = await contractsFor("0g-galileo", {
        signer: this.account,
        deploymentSource: "/deployments/0g-galileo.json",
      });
    } catch (err) {
      this.error = err instanceof Error ? err.message : String(err);
    } finally {
      this.running = false;
    }
  }

  private async step3Mint() {
    if (!this.registry || !this.account) return;
    this.error = undefined;
    this.running = true;
    try {
      // Read the iNFT_7857 handle from the registry. The handle's `write.mint`
      // composes onto viem's writeContract via the connected wallet.
      const inft = (this.registry as unknown as Record<string, unknown>)["iNFT_7857"] as
        | {
            address: Address;
            write: { mint: (args: readonly [Hex, string, Hex]) => Promise<Hash> };
          }
        | undefined;
      if (!inft) throw new Error("iNFT_7857 not in /deployments/0g-galileo.json");
      const txHash = await inft.write.mint([
        this.parentRoot as Hex,
        this.cid,
        this.sealedHex as Hex,
      ]);
      this.txHash = txHash;
      // Wait for receipt + decode the Mint event for the token id.
      const receipt = await this.registry.publicClient.waitForTransactionReceipt({
        hash: txHash,
        confirmations: 1,
      });
      // Look for a Mint(uint256, address, bytes32) log. The first log's first
      // indexed topic is the token id (after the event signature).
      const mintLog = receipt.logs.find(
        (l) => l.address.toLowerCase() === inft.address.toLowerCase(),
      );
      if (mintLog && mintLog.topics.length >= 2 && mintLog.topics[1]) {
        this.tokenId = BigInt(mintLog.topics[1]);
      }
    } catch (err) {
      this.error = err instanceof Error ? err.message : String(err);
    } finally {
      this.running = false;
    }
  }

  override render() {
    return html`
      <h1>iNFT_7857 mint reference</h1>
      <p style="color: var(--muted, #4a5060)">
        Built with the openagents/ dApp kit. Runs in vite dev (browser) or
        wrapped in Tauri 2 (native shell). Same source.
      </p>

      <div class="step ${this.account ? "done" : "active"}">
        <strong>Step 1 — Connect wallet</strong>
        ${this.account
          ? html`<div>✓ ${short(this.account.address)} · chain ${this.account.chainId} · ${this.account.rdns}</div>`
          : html`<button ?disabled=${this.running} @click=${this.step1Connect}>Connect</button>`}
      </div>

      <div class="step ${this.registry ? "done" : this.account ? "active" : ""}">
        <strong>Step 2 — Switch to 0G Galileo (16601)</strong>
        ${this.registry
          ? html`<div>✓ Connected to 0G Galileo. iNFT_7857 contract loaded.</div>`
          : html`<button ?disabled=${!this.account || this.running} @click=${this.step2Switch}>
              Switch chain
            </button>`}
      </div>

      <div class="step ${this.txHash ? "done" : this.registry ? "active" : ""}">
        <strong>Step 3 — Mint iNFT</strong>
        <label>parentRoot (bytes32)</label>
        <input .value=${this.parentRoot} @input=${(e: Event) => (this.parentRoot = (e.target as HTMLInputElement).value)} />
        <label>cid (IPFS CID v1)</label>
        <input .value=${this.cid} @input=${(e: Event) => (this.cid = (e.target as HTMLInputElement).value)} />
        <label>sealedMetadata (hex)</label>
        <input .value=${this.sealedHex} @input=${(e: Event) => (this.sealedHex = (e.target as HTMLInputElement).value)} />
        <button ?disabled=${!this.registry || this.running} @click=${this.step3Mint}>
          ${this.running ? "Submitting…" : "Mint"}
        </button>
        ${this.txHash
          ? html`<pre>tx: ${this.txHash}
${this.tokenId ? "tokenId: " + this.tokenId.toString() : ""}</pre>`
          : html``}
      </div>

      ${this.error ? html`<div class="error">${this.error}</div>` : html``}
    `;
  }
}

function short(addr: string): string {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}
