/**
 * <wallet-login svc="boardroom|dojo|warcouncil"></wallet-login>
 *
 * Connect wallet → fetch challenge → sign → POST verify → store JWT.
 * Emits a 'login' CustomEvent with detail = VerifyResponse on success.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { authChallenge, authVerify, setToken, getToken, clearToken } from '../api.js';
import { connectWallet, signMessage } from '../wallet.js';
import type { Service, VerifyResponse } from '../api.js';

@customElement('wallet-login')
export class WalletLogin extends LitElement {
  static styles = css`
    :host { display: inline-block; font-family: var(--mono, monospace); }
    button {
      background: var(--accent, #5a92ff);
      color: white;
      border: none;
      padding: 8px 14px;
      border-radius: 4px;
      cursor: pointer;
      font-family: inherit;
      font-size: 13px;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    .status { font-size: 11px; color: var(--text2, #888); margin-top: 4px; }
    .addr { color: var(--accent, #5a92ff); font-weight: 600; }
    .tier { color: var(--green, #56d364); }
  `;

  @property() svc: Service = 'boardroom';
  @state() private _busy = false;
  @state() private _status = '';
  @state() private _session: VerifyResponse | null = null;

  connectedCallback() {
    super.connectedCallback();
    // Rehydrate from existing token. We don't decode the JWT (would need a
    // verify-side roundtrip); we just show that we have a token.
    if (getToken(this.svc)) {
      this._status = 'signed-in (cached token)';
    }
  }

  private async _login() {
    if (this._busy) return;
    this._busy = true;
    this._status = 'connecting wallet…';
    try {
      const wallet = await connectWallet();
      this._status = `connected ${wallet.slice(0, 6)}…${wallet.slice(-4)} — fetching challenge…`;
      const ch = await authChallenge(this.svc, wallet);
      this._status = 'signing challenge…';
      const sig = await signMessage(wallet, ch.message);
      this._status = 'verifying…';
      const verified = await authVerify(this.svc, ch.challenge_id, sig);
      setToken(this.svc, verified.session_token);
      this._session = verified;
      this._status = '';
      this.dispatchEvent(new CustomEvent('login', { detail: verified, bubbles: true, composed: true }));
    } catch (e) {
      this._status = `failed: ${(e as Error).message.slice(0, 80)}`;
    } finally {
      this._busy = false;
    }
  }

  private _logout() {
    clearToken(this.svc);
    this._session = null;
    this._status = '';
    this.dispatchEvent(new CustomEvent('logout', { bubbles: true, composed: true }));
  }

  render() {
    if (this._session) {
      return html`
        <span class="status">
          <span class="addr">${this._session.address.slice(0, 6)}…${this._session.address.slice(-4)}</span>
          · <span class="tier">tier ${this._session.tier} (${this._session.tier_name})</span>
          · <button @click=${this._logout}>sign out</button>
        </span>
      `;
    }
    return html`
      <button ?disabled=${this._busy} @click=${this._login}>
        ${this._busy ? '…' : `sign in to ${this.svc}`}
      </button>
      ${this._status ? html`<div class="status">${this._status}</div>` : ''}
    `;
  }
}
