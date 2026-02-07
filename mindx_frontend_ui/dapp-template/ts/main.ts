/**
 * Production entry – TypeScript.
 * Build with tsc/vite and load this bundle from index.html for production.
 * For prototype, index.html loads dapp.js instead.
 */

import { config } from './config';

function init(): void {
  const apiEl = document.getElementById('api-base');
  if (apiEl) apiEl.textContent = config.apiBase;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
