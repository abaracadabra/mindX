/**
 * mindX Dapp – prototype / hacks (plain .js)
 * For production and financial services: migrate to .ts and .tsx (see README).
 */

(function () {
    'use strict';

    const API_PORT = window.MINDX_BACKEND_PORT || '8000';
    const API_BASE = window.MINDX_API_URL || `http://localhost:${API_PORT}`;

    function byId(id) {
        return document.getElementById(id);
    }

    function setApiBase() {
        const el = byId('api-base');
        if (el) el.textContent = API_BASE;
    }

    async function connectWallet() {
        const status = byId('wallet-status');
        const btn = byId('btn-connect');
        if (!window.ethereum) {
            if (status) status.textContent = 'No wallet (e.g. MetaMask)';
            return;
        }
        try {
            if (btn) btn.disabled = true;
            if (status) status.textContent = 'Connecting…';
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            const addr = accounts && accounts[0];
            if (status) status.textContent = addr ? `${addr.slice(0, 6)}…${addr.slice(-4)}` : 'Not connected';
            if (btn) btn.disabled = false;
        } catch (e) {
            if (status) status.textContent = 'Connection failed';
            if (btn) btn.disabled = false;
        }
    }

    function init() {
        setApiBase();
        const btn = byId('btn-connect');
        if (btn) btn.addEventListener('click', connectWallet);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
