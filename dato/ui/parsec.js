// Copyright 2026 BANKON. All rights reserved. Apache-2.0.
// parsec-wallet inclusion adapter — register dato's naming + data views into
// parsec-wallet's router/store with one call. Modular: parsec-wallet stays the
// host; dato is a drop-in feature.
//
// In parsec-wallet/src/main.ts:
//
//   import { registerDatoViews } from '<…>/dato/ui/parsec.js';
//   import { registerView } from './lib/router';
//   import { store } from './lib/store';
//   import * as dom from './lib/dom';                       // parsec's own el/btn/input/toast
//   registerDatoViews({ registerView, navigate: (v) => store.navigate(v), dom,
//     controller: () => store.get().accounts[store.get().activeAccountIndex]?.address,
//     arioHandoff: () => store.navigate('name-manage') }); // hand ARNS purchase to parsec's ario flow
//
// Then add hub/name/data entries to parsec's nav. dom is optional — falls back to
// dato's bundled ./dom.js (API-compatible), so this also works outside parsec.

import { DatoClient } from './client.js';
import { createDatoUI } from './views.js';
import { DeployBridge } from './deploy.js';

export function registerDatoViews(api) {
  const {
    registerView,
    navigate = (v) => { location.hash = '#' + v; },
    dom,
    controller = () => 'local',
    arioHandoff = null,
    backend = null,
    extraRoots = [],
    settleX402 = null,   // optional (quote) => { receipt, amount } — parsec/CLI mints the x402 payment
    deployerHandoff = null,    // (suiteId) => navigate to the in-app OVERLORD deployer
    deployerUrl = null,        // or an absolute URL to DeltaVerse pages/deploy.html
    onchainBackend = null,     // (addresses) => DatoClient backend bound to deployed contracts
    deploymentsSource = '/live/contracts.json',
  } = api || {};
  if (typeof registerView !== 'function') throw new Error('registerDatoViews needs api.registerView');

  return Promise.resolve(dom || import('./dom.js')).then((domMod) => {
    const client = new DatoClient({ backend, extraRoots, arioHandoff });
    client.controller = typeof controller === 'function' ? controller() : controller;
    if (settleX402) client.settleX402 = settleX402;
    const deployBridge = new DeployBridge({ deployerHandoff, deployerUrl, onchainBackend, deploymentsSource });
    const ui = createDatoUI({ navigate, client, dom: domMod, deployBridge });
    registerView('dato-hub', ui.hub);
    registerView('dato-name', ui.name);
    registerView('dato-data', ui.data);
    registerView('dato-commerce', ui.commerce);
    registerView('dato-deploy', ui.deploy);
    return { views: ['dato-hub', 'dato-name', 'dato-data', 'dato-commerce', 'dato-deploy'], client, deployBridge };
  });
}
