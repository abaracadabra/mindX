"use strict";
/*!
 * DeltaVerse — Identity (PRODUCTION lane · TypeScript · L1.5 unified multi-wallet login).
 *
 * Access in the DeltaVerse is granted from wallet-signature-based interaction. This adapter
 * normalizes every supported wallet to one flow — connect → challenge → sign → bundle — that
 * mirrors SIWE / EIP-4361 and bankoneth's /auth/challenge→/auth/verify. The LOGIN FLOW is
 * security-critical, so it lives in the strict-TypeScript production lane and compiles to
 * engine/identity.js (committed for the static/IPFS deploy). Script-style (no import/export)
 * so tsc emits the same UMD JS the <script> tags + Node tests use. See docs/CONVENTIONS.md.
 *
 *   PARSEC / parsec-wallet  (preferred)  Algorand · Arweave   — Tauri sign_challenge
 *   MetaMask                              EVM                   — personal_sign (EIP-191)
 *   Phantom                               EVM (injected)        — personal_sign
 *
 * Recognition is an unverified hint until a signature proves it. Privileged action stays
 * behind a verified signature (L2 server / on-chain). Zero deps; airgap / IPFS-friendly.
 */
(function (global) {
    'use strict';
    var doc = global.document;
    function tauri() { return global.__TAURI__ && global.__TAURI__.invoke ? global.__TAURI__ : null; }
    // ── nonce (browser crypto; never client-trusted for replay — the server burns it) ──
    function nonce(len) {
        len = len || 16;
        var c = global.crypto || global.msCrypto;
        var out = '';
        var alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789';
        if (c && c.getRandomValues) {
            var buf = new Uint8Array(len);
            c.getRandomValues(buf);
            for (var i = 0; i < len; i++)
                out += alphabet[buf[i] % alphabet.length];
            return out;
        }
        // last-resort fallback (still fine — replay defence is server-side per-nonce)
        for (var j = 0; j < len; j++)
            out += alphabet[(j * 7 + len) % alphabet.length];
        return out;
    }
    // ── EIP-6963 multi-injected provider discovery (no "last wallet wins" race) ──
    // Returns [{ info:{name,icon,rdns}, provider }]; falls back to window.ethereum.
    function discoverProviders() {
        var found = [];
        function onAnnounce(e) { if (e.detail && e.detail.provider)
            found.push(e.detail); }
        if (global.addEventListener && global.dispatchEvent) {
            global.addEventListener('eip6963:announceProvider', onAnnounce);
            try {
                global.dispatchEvent(new Event('eip6963:requestProvider'));
            }
            catch (e) { /* ignore */ }
            global.removeEventListener('eip6963:announceProvider', onAnnounce);
        }
        var eth = global.ethereum;
        if (eth) {
            var list = Array.isArray(eth.providers) ? eth.providers : [eth];
            list.forEach(function (p) {
                found.push({ info: { name: p.isMetaMask ? 'MetaMask' : (p.isPhantom ? 'Phantom' : (p.isCoinbaseWallet ? 'Coinbase' : 'Injected')) }, provider: p });
            });
        }
        var seen = [], out = [];
        found.forEach(function (f) { if (seen.indexOf(f.provider) === -1) {
            seen.push(f.provider);
            out.push(f);
        } });
        return out;
    }
    // ── EVM provider selection (MetaMask / Phantom-EVM via EIP-1193) ──
    function evmProvider(prefer) {
        var eth = global.ethereum;
        if (prefer === 'phantom' && global.phantom && global.phantom.ethereum)
            return global.phantom.ethereum;
        if (eth && Array.isArray(eth.providers)) {
            for (var i = 0; i < eth.providers.length; i++) {
                var p = eth.providers[i];
                if (prefer === 'metamask' && p.isMetaMask)
                    return p;
                if (prefer === 'phantom' && p.isPhantom)
                    return p;
            }
        }
        if (prefer === 'metamask' && eth && eth.isMetaMask)
            return eth;
        return eth || null; // default: whatever injected provider exists
    }
    // ── EIP-4361 (SIWE) message ──
    function challenge(opts) {
        opts = opts || {};
        var domain = opts.domain || (global.location ? global.location.host : 'deltaverse');
        var uri = opts.uri || (global.location ? global.location.origin + global.location.pathname : 'https://deltaverse.dao');
        var statement = opts.statement || 'Sign in to the DeltaVerse — prove control of your key.';
        var chainId = opts.chainId == null ? 1 : opts.chainId;
        var n = opts.nonce || nonce();
        var issuedAt = opts.issuedAt || new Date().toISOString();
        var lines = [
            domain + ' wants you to sign in with your account:',
            opts.address || '',
            '',
            statement,
            '',
            'URI: ' + uri,
            'Version: 1',
            'Chain ID: ' + chainId,
            'Nonce: ' + n,
            'Issued At: ' + issuedAt
        ];
        if (opts.resources && opts.resources.length) {
            lines.push('Resources:');
            opts.resources.forEach(function (r) { lines.push('- ' + r); });
        }
        return { message: lines.join('\n'), nonce: n, chainId: chainId, domain: domain };
    }
    // ── connect → { wallet, chain, address } ──
    function connect(wallet) {
        wallet = (wallet || '').toLowerCase();
        if (wallet === 'parsec') {
            var tw = tauri();
            if (tw) {
                return tw.invoke('parsec_login').then(function (a) {
                    var addr = a || 'mindx.algo';
                    if (global.sessionStorage)
                        global.sessionStorage.setItem('parsec_algo', addr);
                    return { wallet: 'parsec', chain: 'algorand', address: addr };
                });
            }
            // browser PARSEC bridge — parsec-wallet may inject window.parsec (Algorand connect + sign)
            var P = global.parsec;
            if (P && typeof P.connect === 'function') {
                return Promise.resolve(P.connect()).then(function (a) {
                    var addr = (a && (a.address || a)) || 'mindx.algo';
                    if (global.sessionStorage) global.sessionStorage.setItem('parsec_algo', addr);
                    return { wallet: 'parsec', chain: 'algorand', address: addr, _parsec: P };
                });
            }
            // PARSEC not present → recognized hint (unverified), like lock.js
            var algo = (global.sessionStorage && global.sessionStorage.getItem('parsec_algo')) || 'mindx.algo';
            return Promise.resolve({ wallet: 'parsec', chain: 'algorand', address: algo, unverified: true });
        }
        // EVM (metamask / phantom / default)
        var prov = evmProvider(wallet);
        if (!prov || !prov.request)
            return Promise.reject(new Error('no EVM wallet (install MetaMask / Phantom or connect PARSEC)'));
        return prov.request({ method: 'eth_requestAccounts' }).then(function (accts) {
            var addr = (accts && accts[0]) || null;
            return prov.request({ method: 'eth_chainId' }).then(function (id) {
                return { wallet: wallet || 'evm', chain: 'evm', address: addr, chainId: id ? parseInt(id, 16) : 1, _prov: prov };
            });
        });
    }
    // ── sign(message, conn) → signature ──
    function sign(message, conn) {
        conn = conn || {};
        if (conn.chain === 'algorand' || conn.chain === 'arweave' || conn.wallet === 'parsec') {
            var tw = tauri();
            if (tw)
                return tw.invoke('sign_challenge', { address: conn.address, message: message });
            // browser PARSEC bridge — window.parsec.signChallenge(address, message) → signature
            var P = conn._parsec || global.parsec;
            if (P && typeof P.signChallenge === 'function')
                return Promise.resolve(P.signChallenge(conn.address, message));
            return Promise.reject(new Error('PARSEC signer unavailable — open in the Tauri shell or inject window.parsec'));
        }
        var prov = conn._prov || evmProvider(conn.wallet);
        if (!prov || !prov.request)
            return Promise.reject(new Error('no EVM signer'));
        return prov.request({ method: 'personal_sign', params: [message, conn.address] });
    }
    // ── login333: the OVERLORD doorway — pass a wallet through the login333 gate (:8787) ──
    // Wallet-agnostic: GET /nonce?address= → sign the gate's message → POST /verify → { token, tier, name }.
    // opts.signMessage is REQUIRED. opts.lookupName is best-effort reverse-ENS for the *.bankon.eth subname
    // (deployer tier); omit and the gate classes member. Token = EVM-signed tier claim. See server/login333.mjs.
    function login333(opts) {
        opts = opts || {};
        var url = opts.url || global.LOGIN333_URL || '';
        var addr = opts.address;
        var mode = (opts.mode || 'eoa').toLowerCase();
        if (!url)
            return Promise.reject(new Error('no login333 gate url'));
        if (!addr || typeof opts.signMessage !== 'function')
            return Promise.reject(new Error('address + signMessage required'));
        return fetch(url + '/nonce?address=' + encodeURIComponent(addr)).then(function (r) { return r.json(); }).then(function (n) {
            if (!n || !n.message)
                throw new Error('login333 /nonce failed');
            return Promise.resolve(opts.signMessage(n.message)).then(function (sig) {
                var lk = opts.lookupName
                    ? Promise.resolve().then(function () { return opts.lookupName(); }).catch(function () { return null; })
                    : Promise.resolve(null);
                return lk.then(function (name) {
                    return fetch(url + '/verify', {
                        method: 'POST', headers: { 'content-type': 'application/json' },
                        body: JSON.stringify({ message: n.message, signature: sig, subname: name || null, mode: mode })
                    }).then(function (r) { return r.json(); });
                });
            });
        }).then(function (v) {
            if (!v || !v.tier)
                throw new Error(v && v.error ? v.error : 'login333 /verify failed');
            return { token: v.token, tier: v.tier, name: v.name || null };
        });
    }
    // ── signIn: connect + challenge + sign → verified bundle (ready for L2 / on-chain) ──
    function signIn(opts) {
        opts = opts || {};
        return connect(opts.wallet).then(function (conn) {
            if (conn.unverified) {
                // no signer present — return an unverified recognition (hint only)
                return { chain: conn.chain, address: conn.address, message: null, signature: null, nonce: null, verified: false, wallet: conn.wallet };
            }
            var ch = challenge({
                domain: opts.domain, uri: opts.uri, statement: opts.statement,
                chainId: conn.chainId, address: conn.address, resources: opts.resources, nonce: opts.nonce
            });
            return sign(ch.message, conn).then(function (sig) {
                return { chain: conn.chain, address: conn.address, message: ch.message, signature: sig, nonce: ch.nonce, verified: true, wallet: conn.wallet, chainId: conn.chainId };
            });
        });
    }
    var DVIdentity = {
        nonce: nonce,
        challenge: challenge,
        connect: connect,
        sign: sign,
        signIn: signIn,
        login333: login333,
        evmProvider: evmProvider,
        discoverProviders: discoverProviders
    };
    if (typeof module !== 'undefined' && module.exports)
        module.exports = DVIdentity;
    global.DVWalletIdentity = DVIdentity; // distinct from DeltaVerse.DVIdentity (name parser) in deltaverse.js
})(typeof window !== 'undefined' ? window : this);
