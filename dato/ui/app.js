// Copyright 2026 BANKON. All rights reserved. Apache-2.0.
// Standalone mount for the dato UI — a tiny hash router so the suite runs on its
// own (no parsec-wallet, no build): `python -m http.server` in dato/ui then open
// index.html. The SAME views power the parsec-wallet inclusion (see parsec.js).

import * as dom from './dom.js';
import { DatoClient } from './client.js';
import { createDatoUI } from './views.js';
import { DeployBridge } from './deploy.js';

const root = document.getElementById('app');
const views = {};
const navigate = (name) => { location.hash = '#' + name; render(); };

const client = new DatoClient({
  // standalone uses localStorage; ar.io ARNS handoff opens the ARNS app.
  arioHandoff: (arns) => window.open('https://arns.app/#/manage/names/' + encodeURIComponent(arns), '_blank'),
});
client.controller = 'local-demo';

// Standalone deploy bridge: status from an optional local manifest; handoff opens
// the DeltaVerse deployer. On-chain binding is a host (parsec) concern.
const deployBridge = new DeployBridge({
  deploymentsSource: './deployments.json',
  deployerUrl: 'https://deltaverse.pythai.net/pages/deploy.html',
});

const ui = createDatoUI({ navigate, client, dom, deployBridge });
views['dato-hub'] = ui.hub;
views['dato-name'] = ui.name;
views['dato-data'] = ui.data;
views['dato-commerce'] = ui.commerce;
views['dato-deploy'] = ui.deploy;

function render() {
  const name = (location.hash.replace(/^#/, '') || 'dato-hub');
  const view = views[name] || views['dato-hub'];
  dom.clear(root);
  root.append(view());
}

window.addEventListener('hashchange', render);
render();
