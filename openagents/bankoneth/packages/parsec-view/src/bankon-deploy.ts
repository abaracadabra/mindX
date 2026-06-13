// SPDX-License-Identifier: Apache-2.0
//
// bankon-deploy.ts — the production parsec view-module for the bankon.eth
// subdomain minter + agent registry + generic ABI explorer (EVM). Rendered
// through a ParsecHost so it slots natively into parsec-wallet's vanilla-TS +
// Blueprint view system (no Lit, no iframe). See README for the ~10-line
// adapter that wires parsec's real el/btn/store/ethers into this factory.

import * as F from "./bankon-forms.js";
import type { ParsecHost, Eip1193 } from "./host.js";

const CHAINS: Record<number, string> = { 1: "Ethereum", 11155111: "Sepolia", 31337: "Anvil (local)" };

export interface BankonDeployView {
  render(): HTMLElement;
}

export function createBankonDeployView(host: ParsecHost): BankonDeployView {
  const { el, btn, input, toast, ethers } = host;

  let provider: Eip1193 | null = null;
  let browserProvider: InstanceType<typeof ethers.BrowserProvider> | null = null;
  let account: string | null = host.account ?? null;
  let chainId: number | null = null;
  let manifest: F.Manifest | null = null;
  let deployments: F.Deployments | null = null;
  let activeTab: "presets" | "explorer" = "presets";

  const root = el("div", { cls: "parsec-view parsec-bankon-deploy" });

  function render(): HTMLElement {
    root.innerHTML = "";
    root.appendChild(header());
    root.appendChild(connectBar());
    root.appendChild(tabs());
    const body = el("div", { cls: "parsec-bankon-deploy__body" });
    root.appendChild(body);
    if (activeTab === "presets") renderPresets(body);
    else renderExplorer(body);
    return root;
  }

  function header(): HTMLElement {
    const h = el("div", { cls: "parsec-view__header" });
    if (host.navigate) h.appendChild(btn("Back", { minimal: true, icon: "arrow-left", onClick: () => host.navigate!("dashboard") }));
    h.appendChild(el("h2", { cls: "parsec-view__title", text: "bankon.eth deployer" }));
    return h;
  }

  function connectBar(): HTMLElement {
    const bar = el("div", { cls: "parsec-bankon-deploy__connect" });
    if (account) {
      bar.appendChild(el("span", { cls: "bp5-tag bp5-intent-success", text: `${account.slice(0, 6)}…${account.slice(-4)}` }));
      bar.appendChild(el("span", { cls: "bp5-tag", text: chainId ? CHAINS[chainId] || `chain ${chainId}` : "…" }));
    } else {
      bar.appendChild(btn("Connect wallet", { intent: "primary", onClick: () => void connect() }));
    }
    return bar;
  }

  function tabs(): HTMLElement {
    const nav = el("div", { cls: "parsec-bankon-deploy__tabs" });
    const mk = (id: typeof activeTab, label: string) =>
      btn(label, { minimal: activeTab !== id, intent: activeTab === id ? "primary" : "none", onClick: () => { activeTab = id; render(); } });
    nav.appendChild(mk("presets", "Mint & flows"));
    nav.appendChild(mk("explorer", "Contract explorer"));
    return nav;
  }

  async function connect(): Promise<void> {
    try {
      provider = await host.getEvmProvider();
      if (!provider) { toast("No EVM wallet found — install MetaMask.", "danger"); return; }
      const accts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
      account = accts[0];
      chainId = parseInt((await provider.request({ method: "eth_chainId" })) as string, 16);
      browserProvider = new ethers.BrowserProvider(provider as never);
      await loadDeployments();
      render();
    } catch (e) {
      toast("Connect failed: " + msg(e), "danger");
    }
  }

  async function loadManifest(): Promise<void> {
    if (!manifest) manifest = await F.loadManifest(host.publicBase);
  }
  async function loadDeployments(): Promise<void> {
    if (chainId == null) return;
    try { deployments = await F.loadDeployments(host.publicBase, chainId); } catch { deployments = null; }
  }
  function requireAddress(key: string, title: string): string {
    const a = deployments ? F.addressFor(deployments, key) : null;
    if (!a) throw new Error(`${title} not deployed on ${CHAINS[chainId ?? 0] || "this chain"} (zero in deployments/${F.constants.deploymentFileFor(chainId ?? 0)}).`);
    return a;
  }

  // ── Presets ────────────────────────────────────────────────────────────
  function renderPresets(body: HTMLElement): void {
    void loadManifest().then(() => {
      body.innerHTML = "";
      if (!manifest) { body.appendChild(note(body, "manifest unavailable")); return; }
      const grid = el("div", { cls: "parsec-bankon-deploy__grid" });
      for (const p of manifest.presets) {
        grid.appendChild(el("div", {
          cls: "parsec-card parsec-card--click",
          children: [el("h3", { text: p.title }), el("div", { cls: "parsec-muted", text: p.subtitle || "" })],
          onClick: () => openPreset(body, p),
        }));
      }
      body.appendChild(grid);
    }).catch((e) => { body.appendChild(note(body, msg(e))); });
  }

  function openPreset(body: HTMLElement, p: F.Preset): void {
    body.innerHTML = "";
    body.appendChild(btn("Back", { minimal: true, onClick: () => renderPresets(body) }));
    body.appendChild(el("h3", { text: p.title }));
    if (p.note) body.appendChild(el("div", { cls: "parsec-note", text: p.note }));
    if (!account) body.appendChild(el("div", { cls: "parsec-note", text: "Connect a wallet to submit." }));

    const inputs: Record<string, HTMLInputElement> = {};
    for (const f of p.fields) {
      body.appendChild(el("div", { cls: "parsec-field-label", html: `${f.label || f.name} <code>${f.type}</code>${f.optional ? " · optional" : ""}` }));
      const inp = input({ placeholder: f.placeholder || f.default || "", value: f.fill === "account" && account ? account : f.default || "" });
      inputs[f.name] = inp; body.appendChild(inp);
      if (f.help) body.appendChild(el("div", { cls: "parsec-muted", text: f.help }));
    }
    const out = el("div", { cls: "parsec-result" });
    const submit = btn(p.mode === "read" ? "Query" : "Submit transaction", { intent: "primary", onClick: () => void runPreset(p, inputs, out, submit) });
    body.appendChild(submit);
    body.appendChild(out);
  }

  async function runPreset(p: F.Preset, inputs: Record<string, HTMLInputElement>, out: HTMLElement, submit: HTMLButtonElement): Promise<void> {
    out.textContent = "";
    try {
      const values: Record<string, string> = {};
      for (const [k, i] of Object.entries(inputs)) values[k] = i.value;
      const c = manifest!.contracts.find((x) => x.deploymentKey === p.contract)!;

      if (p.flow === "resolve") {
        const address = requireAddress(c.deploymentKey, c.title);
        const abi = await F.loadAbi(host.publicBase, c);
        const node = F.namehash(ethers, values.name);
        const addr = await F.readContract({ provider: browserProvider, address, abi, fn: "addr", args: [node], ethers });
        const text = values.key ? await F.readContract({ provider: browserProvider, address, abi, fn: "text", args: [node, values.key], ethers }) : "";
        out.textContent = `namehash: ${node}\naddr(): ${addr}` + (values.key ? `\ntext(${values.key}): ${text || "(empty)"}` : "");
        return;
      }

      const address = requireAddress(c.deploymentKey, c.title);
      const abi = await F.loadAbi(host.publicBase, c);
      const args = F.buildPresetArgs(p, values, { ethers, account });
      if (p.mode === "read") {
        const r = await F.readContract({ provider: browserProvider, address, abi, fn: p.fn!, args, ethers });
        out.textContent = stringify(r);
        return;
      }
      if (!browserProvider) throw new Error("connect a wallet first");
      submit.disabled = true; out.textContent = "awaiting signature…";
      const signer = await browserProvider.getSigner();
      const tx = await F.writeContract({ signer, address, abi, fn: p.fn!, args, value: p.payable ? 0n : undefined, ethers });
      out.textContent = "sent: " + tx.hash + "\nwaiting…";
      const r = await tx.wait();
      out.textContent = `✅ confirmed in block ${r.blockNumber}\n${tx.hash}`;
      toast("Transaction confirmed", "success");
    } catch (e) {
      out.textContent = "✗ " + msg(e);
    } finally {
      submit.disabled = false;
    }
  }

  // ── Generic explorer ─────────────────────────────────────────────────────
  function renderExplorer(body: HTMLElement): void {
    void loadManifest().then(() => {
      body.innerHTML = "";
      body.appendChild(el("div", { cls: "parsec-note", text: "Pick a deployed bankon contract; reads query instantly, writes prompt your wallet." }));
      const sel = document.createElement("select");
      sel.className = "bp5-html-select";
      sel.appendChild(new Option("— select —", ""));
      for (const c of manifest!.contracts) sel.appendChild(new Option(`${c.title} · ${c.name}`, c.deploymentKey));
      body.appendChild(sel);
      const panels = el("div");
      body.appendChild(panels);
      sel.addEventListener("change", async () => {
        panels.innerHTML = "";
        const c = manifest!.contracts.find((x) => x.deploymentKey === sel.value);
        if (!c) return;
        try {
          const abi = await F.loadAbi(host.publicBase, c);
          const address = requireAddress(c.deploymentKey, c.title);
          renderAbiPanels(panels, abi, address);
        } catch (e) { panels.appendChild(el("div", { cls: "parsec-result", text: msg(e) })); }
      });
    }).catch((e) => body.appendChild(el("div", { cls: "parsec-result", text: msg(e) })));
  }

  function renderAbiPanels(panels: HTMLElement, abi: F.AbiFn[], address: string): void {
    const { reads, writes } = F.categorizeAbi(abi);
    panels.appendChild(el("span", { cls: "bp5-tag", text: address }));
    panels.appendChild(el("h3", { text: `Read (${reads.length})` }));
    for (const fn of reads) panels.appendChild(fnCard(fn, abi, address, false));
    panels.appendChild(el("h3", { text: `Write (${writes.length})` }));
    for (const fn of writes) panels.appendChild(fnCard(fn, abi, address, true));
  }

  function fnCard(fn: F.AbiFn, abi: F.AbiFn[], address: string, isWrite: boolean): HTMLElement {
    const payable = fn.stateMutability === "payable";
    const card = el("div", { cls: "parsec-fn-card" });
    card.appendChild(el("div", { cls: "parsec-fn-sig", html: `${F.signatureOf(fn)} <span class="bp5-tag bp5-minimal">${fn.stateMutability}</span>` }));
    const fields: HTMLInputElement[] = [];
    for (const i of fn.inputs) {
      card.appendChild(el("div", { cls: "parsec-field-label", html: `${i.name || "arg"} <code>${i.type}</code>` }));
      const inp = input({ placeholder: i.type });
      fields.push(inp); card.appendChild(inp);
    }
    let valueInput: HTMLInputElement | null = null;
    if (payable) { card.appendChild(el("div", { cls: "parsec-field-label", html: "value <code>ETH</code>" })); valueInput = input({ placeholder: "0.0" }); card.appendChild(valueInput); }
    const out = el("div", { cls: "parsec-result" });
    const b = btn(isWrite ? "Write" : "Query", {
      intent: isWrite ? "primary" : "none",
      onClick: async () => {
        out.textContent = "…";
        try {
          const args = fn.inputs.map((i, idx) => F.coerceArg(i.type, fields[idx].value));
          if (!isWrite) {
            const r = await F.readContract({ provider: browserProvider, address, abi, fn: fn.name, args, ethers });
            out.textContent = stringify(r);
          } else {
            if (!browserProvider) throw new Error("connect a wallet first");
            const signer = await browserProvider.getSigner();
            const value = valueInput && valueInput.value ? ethers.parseEther(valueInput.value) : undefined;
            b.disabled = true;
            const tx = await F.writeContract({ signer, address, abi, fn: fn.name, args, value, ethers });
            out.textContent = "sent: " + tx.hash + "\nwaiting…";
            const r = await tx.wait();
            out.textContent = `✅ block ${r.blockNumber}\n${tx.hash}`;
          }
        } catch (e) { out.textContent = "✗ " + msg(e); } finally { b.disabled = false; }
      },
    });
    card.appendChild(b); card.appendChild(out);
    return card;
  }

  function note(_body: HTMLElement, t: string): HTMLElement { return el("div", { cls: "parsec-note", text: t }); }

  return { render };
}

function msg(e: unknown): string {
  const any = e as { shortMessage?: string; message?: string };
  return any?.shortMessage || any?.message || String(e);
}
function stringify(r: unknown): string {
  if (typeof r === "bigint") return r.toString();
  if (Array.isArray(r)) return r.map(stringify).join("\n");
  if (r && typeof r === "object") { try { return JSON.stringify(r, (_, v) => (typeof v === "bigint" ? v.toString() : v), 2); } catch { return String(r); } }
  return String(r);
}
