// Copyright 2026 BANKON. All rights reserved. Apache-2.0.
// dato UI views — hub · naming · data. Factory functions returning HTMLElement,
// in parsec-wallet's view idiom. createDatoUI({ navigate, client, dom }) returns
// { hub, name, data } so the same views mount standalone or inside parsec-wallet.

import { TIERS } from './client.js';
import { DATO_SUITE } from './deploy.js';

const TIER_HELP = {
  immortal: 'permanent Arweave upload — the ~200-year guarantee; never changes',
  immutable: 'sha256 hash-locked + anchored; re-commit with different bytes is rejected',
  mutable: 'editable, versioned dato state',
};

export function createDatoUI({ navigate, client, dom, deployBridge = null }) {
  const { el, btn, input, select, toast } = dom;
  const card = (children) => el('div', { cls: 'dato-card', children });
  const header = (title, sub) => el('div', {
    cls: 'dato-view__header',
    children: [
      el('div', { cls: 'dato-brand', children: [el('span', { cls: 'dato-brand__mark', text: '◈' }), el('h2', { text: title })] }),
      sub ? el('p', { cls: 'dato-view__sub', text: sub }) : null,
    ],
  });

  // ── HUB ────────────────────────────────────────────────────────────────
  function hub() {
    return el('div', {
      cls: 'dato-view',
      children: [
        header('dato', 'A DAIO-owned data-DAO: permanence naming + data, three tiers.'),
        el('div', {
          cls: 'dato-hub__grid',
          children: [
            tile('Naming', 'Compose & register <handle>.<tier>.<root>. ar.io ARNS names are a purchase.', 'dato-name'),
            tile('Data', 'Commit data at immortal / immutable / mutable; view proofs.', 'dato-data'),
            tile('Commerce', 'Spawn a dato, request-to-join with an x402 fee — agentic commerce.', 'dato-commerce'),
            tile('Deploy', 'Hand off the dato contracts to the OVERLORD deployer; bind on-chain.', 'dato-deploy'),
          ],
        }),
        el('p', { cls: 'dato-view__foot', text: 'Modular component — include in parsec-wallet via registerDatoViews().' }),
      ],
    });
  }
  function tile(title, desc, view) {
    return el('div', {
      cls: 'dato-tile', onClick: () => navigate(view),
      children: [el('h3', { text: title }), el('p', { text: desc }), el('span', { cls: 'dato-tile__go', text: 'open →' })],
    });
  }

  // ── NAMING ──────────────────────────────────────────────────────────────
  function name() {
    let handle = '', tier = 'immortal', root = 'blockchain';
    const preview = el('code', { cls: 'dato-name__preview', text: '—' });
    const purchaseNote = el('div', { cls: 'dato-note' });
    const list = el('div', { cls: 'dato-list' });

    const refresh = () => {
      try { preview.textContent = client.composeName(handle || 'handle', tier, root).name; }
      catch { preview.textContent = '—'; }
      const r = client.rootList().find((x) => x.name === root);
      purchaseNote.className = 'dato-note' + (r?.purchase ? ' dato-note--warn' : '');
      purchaseNote.textContent = r?.purchase
        ? `⚠ "${root}" is an ar.io ARNS root — registration is a PURCHASE (HyperBEAM/ARIO).`
        : `"${root}" is a free dato-registry name.`;
    };
    const reload = async () => {
      const names = await client.listNames();
      list.replaceChildren(...(names.length
        ? names.map((n) => el('div', { cls: 'dato-row', children: [
            el('code', { text: n.name }),
            el('span', { cls: 'dato-pill dato-pill--' + n.tier, text: n.tier }),
            el('span', { cls: 'dato-row__meta', text: (n.controller || 'local').slice(0, 14) }),
          ] }))
        : [el('p', { cls: 'dato-muted', text: 'No names yet.' })]));
    };

    const tierSel = select(TIERS.map((t) => ({ value: t, label: t })), { value: tier, onChange: (v) => { tier = v; refresh(); } });
    const rootSel = select(client.rootList().map((r) => ({ value: r.name, label: `${r.name}${r.purchase ? ' (purchase)' : ''}` })), { value: root, onChange: (v) => { root = v; refresh(); } });

    const register = async () => {
      try {
        const res = await client.registerName(handle, tier, root, { controller: client.controller });
        if (res.needsPurchase) {
          toast(res.message, 'warn');
          purchaseNote.textContent = res.message;
          const buy = btn('Register on ar.io (purchase)', { intent: 'primary', onClick: res.handoff });
          purchaseNote.append(document.createElement('br'), buy);
          return;
        }
        toast(`Registered ${res.name}`, 'success'); reload();
      } catch (e) { toast(String(e.message || e), 'error'); }
    };

    refresh(); reload();
    return el('div', { cls: 'dato-view', children: [
      el('div', { cls: 'dato-view__bar', children: [btn('← hub', { minimal: true, onClick: () => navigate('dato-hub') }), el('h2', { text: 'dato naming' })] }),
      card([
        el('label', { cls: 'dato-label', text: 'handle' }),
        input({ placeholder: 'e.g. archive', onInput: (v) => { handle = v; refresh(); }, onEnter: register }),
        el('div', { cls: 'dato-row2', children: [
          el('div', { children: [el('label', { cls: 'dato-label', text: 'tier (declares permanence)' }), tierSel, el('p', { cls: 'dato-help', text: TIER_HELP[tier] })] }),
          el('div', { children: [el('label', { cls: 'dato-label', text: 'root (extensible)' }), rootSel] }),
        ] }),
        el('div', { cls: 'dato-name__previewRow', children: [el('span', { text: 'name:' }), preview] }),
        purchaseNote,
        btn('Register name', { intent: 'primary', onClick: register }),
      ]),
      el('h3', { cls: 'dato-section', text: 'Registered names' }), list,
    ] });
  }

  // ── DATA ──────────────────────────────────────────────────────────────
  function data() {
    let handle = '', tier = 'immutable', root = 'blockchain', content = '';
    const list = el('div', { cls: 'dato-list' });

    const reload = async () => {
      const recs = await client.listRecords();
      list.replaceChildren(...(recs.length ? recs.map(recRow) : [el('p', { cls: 'dato-muted', text: 'No records yet.' })]));
    };
    const recRow = (r) => el('div', { cls: 'dato-row dato-row--rec', children: [
      el('code', { text: r.name }),
      el('span', { cls: 'dato-pill dato-pill--' + r.tier, text: r.tier + (r.version > 1 ? ` v${r.version}` : '') }),
      el('span', { cls: 'dato-row__meta', text: r.proof ? r.proof.slice(0, 22) + '…' : (r.status || '') }),
      el('span', { cls: 'dato-row__meta', text: 'sha ' + r.sha256.slice(0, 10) }),
    ] });

    const commit = async () => {
      try {
        const rec = await client.commit(handle, tier, root, content);
        toast(rec.status === 'pending-arweave-upload'
          ? `Committed (immortal) — Arweave upload pending server-side for ${rec.name}`
          : `Committed ${rec.name}${rec.proof ? ' · ' + rec.proof.slice(0, 18) + '…' : ''}`,
          rec.status === 'pending-arweave-upload' ? 'warn' : 'success');
        reload();
      } catch (e) { toast(String(e.message || e), 'error'); }
    };

    const tierSel = select(TIERS.map((t) => ({ value: t, label: t })), { value: tier, onChange: (v) => { tier = v; help.textContent = TIER_HELP[v]; } });
    const rootSel = select(client.rootList().map((r) => ({ value: r.name, label: r.name })), { value: root, onChange: (v) => { root = v; } });
    const help = el('p', { cls: 'dato-help', text: TIER_HELP[tier] });

    reload();
    return el('div', { cls: 'dato-view', children: [
      el('div', { cls: 'dato-view__bar', children: [btn('← hub', { minimal: true, onClick: () => navigate('dato-hub') }), el('h2', { text: 'dato data' })] }),
      card([
        el('div', { cls: 'dato-row2', children: [
          el('div', { children: [el('label', { cls: 'dato-label', text: 'handle' }), input({ placeholder: 'doc1', onInput: (v) => { handle = v; } })] }),
          el('div', { children: [el('label', { cls: 'dato-label', text: 'tier' }), tierSel] }),
        ] }),
        el('div', { children: [el('label', { cls: 'dato-label', text: 'root' }), rootSel] }),
        help,
        el('label', { cls: 'dato-label', text: 'content' }),
        (() => { const ta = el('textarea', { cls: 'dato-textarea', attrs: { rows: '4', placeholder: 'data to commit…' } }); ta.addEventListener('input', () => { content = ta.value; }); return ta; })(),
        btn('Commit data', { intent: 'primary', onClick: commit }),
      ]),
      el('h3', { cls: 'dato-section', text: 'Records' }), list,
    ] });
  }

  // ── COMMERCE (spawn + request-to-join with x402 fee) ─────────────────────
  function commerce() {
    let handle = '', tier = 'immortal', root = 'blockchain', fee = 0, openJoin = true;
    let joinWallet = client.controller || '';
    const list = el('div', { cls: 'dato-list' });

    const reload = async () => {
      const datos = await client.listDatos();
      list.replaceChildren(...(datos.length ? datos.map(datoRow) : [el('p', { cls: 'dato-muted', text: 'No datos yet — spawn one.' })]));
    };
    const datoRow = (d) => {
      const memberN = Object.keys(d.members || {}).length;
      const feeTxt = d.joinFeeMicroUSD ? `$${(d.joinFeeMicroUSD / 1e6).toFixed(4)} join` : 'free join';
      const joinBtn = btn(d.joinFeeMicroUSD ? 'Pay & join (x402)' : 'Join', {
        intent: 'primary', onClick: () => doJoin(d),
      });
      return el('div', { cls: 'dato-row dato-row--rec', children: [
        el('code', { text: d.name }),
        el('span', { cls: 'dato-pill dato-pill--' + d.tier, text: d.tier }),
        el('span', { cls: 'dato-row__meta', text: `${memberN} member${memberN === 1 ? '' : 's'} · ${feeTxt}` }),
        joinBtn,
      ] });
    };

    const doJoin = async (d) => {
      const wallet = joinWallet || prompt('Wallet address to join as:') || '';
      if (!wallet) return;
      try {
        const q = client.quoteJoin(d.datoId);
        let feeTx = null, feePaid = 0;
        if (!q.free) {
          // Agentic commerce: settle the join fee over x402. A wallet backend
          // (parsec / CLI) mints the X-PAYMENT credential; standalone we attach a
          // demo receipt so the flow is exercised end-to-end.
          const settle = client.settleX402 || null;
          if (settle) { const r = await settle(q); feeTx = r.receipt; feePaid = r.amount; }
          else { feeTx = 'x402-demo-' + Math.random().toString(36).slice(2, 10); feePaid = q.feeMicroUSD; toast(`x402 fee ${q.feeMicroUSD} µUSD settled (demo) on ${q.x402Endpoint}`, 'warn'); }
        }
        await client.joinDato(d.datoId, wallet, { feeTx, feePaidMicroUSD: feePaid, settings: {} });
        toast(`Joined ${d.name}${feeTx ? ' · fee ' + feeTx.slice(0, 14) : ''}`, 'success');
        reload();
      } catch (e) { toast(String(e.message || e), 'error'); }
    };

    const spawn = async () => {
      try {
        const d = await client.spawnDato(handle, tier, root, { joinFeeMicroUSD: fee, openJoin });
        toast(`Spawned ${d.name} (DAIO-owned)`, 'success'); reload();
      } catch (e) { toast(String(e.message || e), 'error'); }
    };

    const tierSel = select(TIERS.map((t) => ({ value: t, label: t })), { value: tier, onChange: (v) => { tier = v; } });
    const rootSel = select(client.rootList().map((r) => ({ value: r.name, label: r.name })), { value: root, onChange: (v) => { root = v; } });

    reload();
    return el('div', { cls: 'dato-view', children: [
      el('div', { cls: 'dato-view__bar', children: [btn('← hub', { minimal: true, onClick: () => navigate('dato-hub') }), el('h2', { text: 'dato commerce' })] }),
      card([
        el('p', { cls: 'dato-help', text: 'Spawn a DAIO-owned dato. A join fee (microUSD) makes membership a paid, x402-settled action — agentic commerce.' }),
        el('div', { cls: 'dato-row2', children: [
          el('div', { children: [el('label', { cls: 'dato-label', text: 'handle' }), input({ placeholder: 'guild', onInput: (v) => { handle = v; } })] }),
          el('div', { children: [el('label', { cls: 'dato-label', text: 'tier' }), tierSel] }),
        ] }),
        el('div', { cls: 'dato-row2', children: [
          el('div', { children: [el('label', { cls: 'dato-label', text: 'root' }), rootSel] }),
          el('div', { children: [el('label', { cls: 'dato-label', text: 'join fee (microUSD, 0 = free)' }), input({ type: 'number', value: '0', onInput: (v) => { fee = Number(v) || 0; } })] }),
        ] }),
        btn('Spawn dato', { intent: 'primary', onClick: spawn }),
      ]),
      el('div', { cls: 'dato-card', children: [
        el('label', { cls: 'dato-label', text: 'join as wallet' }),
        input({ placeholder: '0x… / arweave addr', value: joinWallet, onInput: (v) => { joinWallet = v; } }),
      ] }),
      el('h3', { cls: 'dato-section', text: 'Datos (request-to-join)' }), list,
    ] });
  }

  // ── DEPLOY (handoff to the OVERLORD deployer + bind on-chain) ────────────
  function deploy() {
    const statusBox = el('div', { cls: 'dato-list' });
    const bindRow = el('div', {});

    const render = async () => {
      if (!deployBridge) {
        statusBox.replaceChildren(el('p', { cls: 'dato-note dato-note--warn',
          text: 'No deploy bridge wired. Include via registerDatoViews({ deployerHandoff, onchainBackend, deploymentsSource }).' }));
        return;
      }
      let st;
      try { st = await deployBridge.status(); }
      catch (e) { statusBox.replaceChildren(el('p', { cls: 'dato-muted', text: 'status: ' + e.message })); return; }
      statusBox.replaceChildren(...st.contracts.map((c) => el('div', {
        cls: 'dato-row',
        children: [
          el('span', { cls: 'dato-row__dot', text: c.deployed ? '●' : '○', style: { color: c.deployed ? 'var(--dato-ok)' : 'var(--dato-mut)' } }),
          el('code', { text: c.name }),
          el('span', { cls: 'dato-row__meta', text: c.address ? c.address.slice(0, 10) + '…' + c.address.slice(-6) : c.role }),
        ],
      })));
      bindRow.replaceChildren(
        st.deployed
          ? btn('Bind UI to on-chain dato', { intent: 'primary', onClick: async () => {
              try { const a = await deployBridge.bind(client); toast('Bound to DatoCore ' + (a.DatoCore || '').slice(0, 10) + '…', 'success'); }
              catch (e) { toast(String(e.message || e), 'error'); }
            } })
          : btn('Hand off to OVERLORD deployer →', { intent: 'primary', onClick: () => { const u = deployBridge.handoff(); if (typeof u === 'string') toast('Opened deployer: ' + u, 'info'); } }),
      );
    };

    render();
    return el('div', { cls: 'dato-view', children: [
      el('div', { cls: 'dato-view__bar', children: [btn('← hub', { minimal: true, onClick: () => navigate('dato-hub') }), el('h2', { text: 'dato deploy' })] }),
      card([
        el('p', { cls: 'dato-help', text: `Suite "${DATO_SUITE.id}" → DeltaVerse deployer (pages/deploy.html). DEPLOY→LAUNCH in order; DatoCore is owned by the DAIO. Then bind this UI to the deployed addresses.` }),
        el('div', { cls: 'dato-deploy__order', children: [el('span', { cls: 'dato-muted', text: 'order: ' }), el('code', { text: DATO_SUITE.contracts.map((c) => c.name).join(' → ') })] }),
      ]),
      el('h3', { cls: 'dato-section', text: 'Contracts' }), statusBox,
      el('div', { cls: 'dato-card', children: [bindRow] }),
    ] });
  }

  return { hub, name, data, commerce, deploy };
}
