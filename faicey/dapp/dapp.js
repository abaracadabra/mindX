// dapp.js — generic, ABI-driven contract interaction for the SoundWave voiceprint dApp.
//
// Convention (bankoneth-style): the contract ABI lives in abis/<name>.abi.js (swap the file
// to change contract — the UI reads it generically), addresses live in deployments/<chainId>.json,
// and contracts.json is the manifest. No ethers, no CDN — encoding via in-house abi-codec.js,
// transport via window.ethereum. Pure-JS prototype; the production target is .ts/.tsx.

import { encodeCall, decodeOutputs, signatureOf, selectorFor } from './abi-codec.js';
import { DeltaVerse } from './deltaverse.js';

const $ = (id) => document.getElementById(id);
const log = (msg, cls = '') => {
  const el = document.createElement('div');
  el.className = 'logline ' + cls;
  el.textContent = msg;
  $('log').prepend(el);
};

const state = { manifest: null, contract: null, abi: null, selectors: null, address: null, account: null, chainId: null };
const deltaverse = new DeltaVerse($('deltaverse'));

// ── boot ──
(async function boot() {
  state.manifest = await fetch('./contracts.json').then((r) => r.json());
  const sel = $('contract-select');
  state.manifest.contracts.forEach((c) => {
    const o = document.createElement('option');
    o.value = c.name; o.textContent = c.name; sel.appendChild(o);
  });
  sel.onchange = () => selectContract(sel.value);
  $('connect').onclick = connect;
  await selectContract(state.manifest.contracts[0].name);
  deltaverse.start();
})();

async function selectContract(name) {
  const entry = state.manifest.contracts.find((c) => c.name === name);
  const mod = await import('./' + entry.abiModule);
  state.contract = name;
  state.abi = mod.abi;
  state.selectors = mod.selectors;
  await loadAddress();
  renderSurface();
  renderVoiceprintForm();
  refreshSupply();
}

async function loadAddress() {
  state.address = null;
  if (!state.chainId) return;
  try {
    const dep = await fetch(`./deployments/${state.chainId}.json`).then((r) => (r.ok ? r.json() : {}));
    state.address = dep[state.contract] || null;
  } catch { /* not deployed on this chain */ }
  $('surface-meta').textContent = state.address ? `@ ${state.address}` : '(not deployed on this chain — run forge deploy + export-abis)';
}

// ── wallet ──
async function connect() {
  if (!window.ethereum) { log('No wallet (window.ethereum) found.', 'err'); return; }
  const [acct] = await window.ethereum.request({ method: 'eth_requestAccounts' });
  state.account = acct;
  state.chainId = parseInt(await window.ethereum.request({ method: 'eth_chainId' }), 16);
  $('chain').textContent = 'chain ' + state.chainId;
  $('connect').textContent = acct.slice(0, 6) + '…' + acct.slice(-4);
  window.ethereum.on?.('chainChanged', () => location.reload());
  await loadAddress();
  refreshSupply();
  log(`connected ${acct} on chain ${state.chainId}`, 'ok');
}

// ── low-level calls ──
async function callRead(fn, args = []) {
  if (!state.address) throw new Error('contract address unknown (connect + deploy)');
  const data = encodeCall(fn, selectorFor(fn, state.selectors), args);
  const ret = await window.ethereum.request({ method: 'eth_call', params: [{ to: state.address, data }, 'latest'] });
  return decodeOutputs(fn.outputs || [], ret);
}
async function sendWrite(fn, args = []) {
  if (!state.account) throw new Error('connect a wallet first');
  if (!state.address) throw new Error('contract address unknown');
  const data = encodeCall(fn, selectorFor(fn, state.selectors), args);
  const tx = await window.ethereum.request({ method: 'eth_sendTransaction', params: [{ from: state.account, to: state.address, data }] });
  log(`tx ${tx} — ${fn.name}(${args.join(', ')})`, 'ok');
  return tx;
}

// ── generic surface: render every function from the ABI ──
function renderSurface() {
  const reads = $('reads'), writes = $('writes');
  reads.innerHTML = ''; writes.innerHTML = '';
  for (const fn of state.abi.filter((f) => f.type === 'function')) {
    const isRead = fn.stateMutability === 'view' || fn.stateMutability === 'pure';
    const box = document.createElement('div');
    box.className = 'fn';
    const inputs = (fn.inputs || []).map((inp, i) =>
      `<input data-i="${i}" placeholder="${inp.name || 'arg'+i}: ${inp.type}"/>`).join('');
    box.innerHTML = `<div class="fn-name">${fn.name}<span class="sig">${signatureOf(fn).replace(fn.name,'')}</span></div>${inputs}<button>${isRead ? 'call' : 'send'}</button><div class="out"></div>`;
    const btn = box.querySelector('button');
    btn.onclick = async () => {
      const args = collectArgs(fn, box);
      try {
        if (isRead) box.querySelector('.out').textContent = fmt(await callRead(fn, args));
        else await sendWrite(fn, args);
      } catch (e) { box.querySelector('.out').textContent = '✗ ' + e.message; }
    };
    (isRead ? reads : writes).appendChild(box);
  }
}

function collectArgs(fn, box) {
  return (fn.inputs || []).map((inp, i) => {
    const raw = box.querySelector(`input[data-i="${i}"]`).value.trim();
    const m = inp.type.match(/^(\w+)\[(\d+)\]$/);
    if (m) return raw.split(',').map((s) => s.trim());
    return raw;
  });
}

const fmt = (v) => (typeof v === 'object' ? JSON.stringify(v, null, 1) : String(v));

// ── supply panel ──
async function refreshSupply() {
  const fn = state.abi.find((f) => f.name === 'supplyInfo');
  if (!fn || !state.address) { $('supply').textContent = ''; return; }
  try {
    const [cap, minted, remaining, dec] = await callRead(fn);
    const whole = (x) => (BigInt(x) / 10n ** BigInt(dec)).toLocaleString();
    $('supply').innerHTML = `cap <b>${whole(cap)}</b> WAV · minted <b>${whole(minted)}</b> · remaining <b>${whole(remaining)}</b> · ${dec} decimals`;
  } catch { /* not deployed */ }
}

// ── voiceprint registration form (headline action) ──
function renderVoiceprintForm() {
  const reg = state.abi.find((f) => f.name === 'registerVoicePrint');
  const host = $('voiceprint-form');
  if (!reg) { host.innerHTML = '<p class="hint">This contract has no registerVoicePrint.</p>'; return; }
  // sample forensic measurement (220.5 Hz tone) — real values × 1e18
  const sample = {
    hash: '0x' + 'a1'.repeat(32),
    sampleRate: 44100,
    m: ['220500000000000000000','421000000000000000','219900000000000000000','430700000000000000000','80000000000000000','3140000000000000000'],
    precision: '900000000000000000',
  };
  host.innerHTML = `
    <input id="vp-hash" value="${sample.hash}" placeholder="sha256 hash (bytes32)"/>
    <div class="vp-grid">
      <input id="vp-sr" value="${sample.sampleRate}" placeholder="sampleRate Hz"/>
      <input id="vp-m0" value="${sample.m[0]}" placeholder="dominantFreq ×1e18"/>
      <input id="vp-m1" value="${sample.m[1]}" placeholder="amplitude ×1e18"/>
      <input id="vp-m2" value="${sample.m[2]}" placeholder="centroid ×1e18"/>
      <input id="vp-m3" value="${sample.m[3]}" placeholder="rolloff ×1e18"/>
      <input id="vp-m4" value="${sample.m[4]}" placeholder="zcr ×1e18"/>
      <input id="vp-m5" value="${sample.m[5]}" placeholder="hnr ×1e18"/>
      <input id="vp-p" value="${sample.precision}" placeholder="precision ×1e18"/>
    </div>
    <button id="vp-go">register voiceprint → mint WAV</button>`;
  $('vp-go').onclick = async () => {
    const m = [0,1,2,3,4,5].map((i) => $('vp-m'+i).value.trim());
    const args = [$('vp-hash').value.trim(), $('vp-sr').value.trim(), m, $('vp-p').value.trim()];
    try {
      await sendWrite(reg, args);
      // DeltaVerse: this participant joins the field — star colored by frequency, sized by precision
      deltaverse.addParticipant({
        freq: Number(m[0]) / 1e18,
        precision: Number($('vp-p').value) / 1e18,
        id: state.account || $('vp-hash').value.slice(0, 10),
      });
      refreshSupply();
    } catch (e) { log('✗ ' + e.message, 'err'); }
  };
}
