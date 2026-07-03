// Copyright 2026 BANKON. All rights reserved. Apache-2.0.
// Minimal, zero-dependency DOM helpers — API-compatible with parsec-wallet's
// src/lib/dom.ts (el/btn/input/select/toast) so dato views drop straight in.
// Plain ESM JS: runs in the browser with no build and imports cleanly into
// parsec-wallet's Vite bundle.

export function el(tag, opts = {}) {
  const node = document.createElement(tag);
  if (opts.cls) node.className = opts.cls;
  if (opts.text != null) node.textContent = String(opts.text);
  if (opts.html != null) node.innerHTML = opts.html;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  if (opts.style) Object.assign(node.style, opts.style);
  if (opts.onClick) node.addEventListener('click', opts.onClick);
  for (const c of opts.children || []) if (c) node.append(c);
  return node;
}

export function input(opts = {}) {
  const node = el('input', { cls: opts.cls || 'dato-input' });
  if (opts.placeholder) node.placeholder = opts.placeholder;
  if (opts.value != null) node.value = opts.value;
  if (opts.type) node.type = opts.type;
  if (opts.onInput) node.addEventListener('input', () => opts.onInput(node.value));
  if (opts.onEnter) node.addEventListener('keydown', (e) => { if (e.key === 'Enter') opts.onEnter(node.value); });
  return node;
}

export function select(options, opts = {}) {
  const node = el('select', { cls: opts.cls || 'dato-select' });
  for (const o of options) {
    const optEl = el('option', { text: o.label });
    optEl.value = o.value;
    if (opts.value === o.value) optEl.selected = true;
    node.append(optEl);
  }
  if (opts.onChange) node.addEventListener('change', () => opts.onChange(node.value));
  return node;
}

export function btn(label, opts = {}) {
  const cls = ['dato-btn'];
  if (opts.intent) cls.push('dato-btn--' + opts.intent);
  if (opts.minimal) cls.push('dato-btn--minimal');
  const node = el('button', { cls: cls.join(' '), text: label });
  if (opts.icon) node.setAttribute('data-icon', opts.icon);
  if (opts.disabled) node.disabled = true;
  if (opts.onClick) node.addEventListener('click', opts.onClick);
  return node;
}

let _toastHost = null;
export function toast(message, kind = 'info') {
  if (!_toastHost) {
    _toastHost = el('div', { cls: 'dato-toasts' });
    document.body.append(_toastHost);
  }
  const t = el('div', { cls: 'dato-toast dato-toast--' + kind, text: message });
  _toastHost.append(t);
  setTimeout(() => t.remove(), 4200);
}

export function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
