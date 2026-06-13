/**
 * <personhood-card></personhood-card>
 *
 * Shows the current user's personhood status (none/pending/granted) with
 * actions: declare (if none/pending), vouch (target address input, if granted).
 * Reads/writes against /dojo-svc/personhood/*.
 */

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { Api, getToken } from '../api.js';
import type { PersonhoodStatus } from '../api.js';

@customElement('personhood-card')
export class PersonhoodCard extends LitElement {
  static styles = css`
    :host { display: block; font-family: var(--mono, monospace); padding: 12px; border: 1px solid var(--border, #2a2a2a); border-radius: 6px; }
    h3 { margin: 0 0 8px; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: var(--text2, #888); }
    .status-none    { color: var(--text2, #888); }
    .status-pending { color: var(--amber, #e3b341); }
    .status-granted { color: var(--green, #56d364); font-weight: 600; }
    .row { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
    input { background: var(--surface2, #161a22); color: var(--text, #ddd); border: 1px solid var(--border, #2a2a2a); padding: 6px 10px; border-radius: 4px; font-family: inherit; font-size: 12px; min-width: 280px; }
    button { background: var(--accent, #5a92ff); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 12px; }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    .msg { font-size: 11px; color: var(--text2, #888); margin-top: 6px; min-height: 14px; }
  `;

  @state() private _me: PersonhoodStatus | null = null;
  @state() private _msg = '';
  @state() private _vouchTarget = '';
  @state() private _busy = false;
  @state() private _myAddr = '';

  async connectedCallback() {
    super.connectedCallback();
    document.addEventListener('login', () => void this._refresh());
    document.addEventListener('logout', () => { this._me = null; this._myAddr = ''; });
    await this._refresh();
  }

  private async _refresh() {
    const tok = getToken('dojo');
    if (!tok) { this._me = null; this._myAddr = ''; return; }
    // Decode the JWT payload to learn our address. (No signature verification —
    // the server holds the truth; we just need the displayed value.)
    try {
      const payload = JSON.parse(atob(tok.split('.')[1] ?? ''));
      this._myAddr = String(payload?.address ?? '').toLowerCase();
    } catch { /* leave empty */ }
    if (!this._myAddr) return;
    try {
      this._me = await Api.personhood(this._myAddr);
    } catch (e) {
      this._msg = `lookup failed: ${(e as Error).message.slice(0, 80)}`;
    }
  }

  private async _declare() {
    if (this._busy) return;
    this._busy = true;
    try {
      await Api.declarePersonhood();
      await this._refresh();
      this._msg = 'declared — vouches needed';
    } catch (e) {
      this._msg = `declare failed: ${(e as Error).message.slice(0, 80)}`;
    } finally {
      this._busy = false;
    }
  }

  private async _vouch() {
    if (this._busy || !this._vouchTarget) return;
    this._busy = true;
    try {
      await Api.vouch(this._vouchTarget);
      this._msg = `vouched for ${this._vouchTarget.slice(0, 10)}…`;
      this._vouchTarget = '';
    } catch (e) {
      this._msg = `vouch failed: ${(e as Error).message.slice(0, 80)}`;
    } finally {
      this._busy = false;
    }
  }

  render() {
    if (!getToken('dojo')) {
      return html`<h3>Personhood</h3><p class="msg">Sign in to the dojo to see your status.</p>`;
    }
    const status = this._me?.status ?? 'unknown';
    return html`
      <h3>Personhood</h3>
      <div>
        <strong>${this._myAddr.slice(0, 6)}…${this._myAddr.slice(-4)}</strong>
        — status: <span class="status-${status}">${status}</span>
        (tier_score: ${this._me?.tier_score ?? '—'})
      </div>
      ${status === 'none' || status === 'pending' ? html`
        <div class="row">
          <button ?disabled=${this._busy} @click=${this._declare}>
            ${status === 'pending' ? 're-declare' : 'self-declare'}
          </button>
        </div>
      ` : ''}
      ${status === 'granted' ? html`
        <div class="row">
          <input
            placeholder="0x… vouch for another wallet"
            .value=${this._vouchTarget}
            @input=${(e: Event) => this._vouchTarget = (e.target as HTMLInputElement).value.trim().toLowerCase()}
          />
          <button ?disabled=${this._busy || !this._vouchTarget} @click=${this._vouch}>vouch</button>
        </div>
      ` : ''}
      <div class="msg">${this._msg}</div>
    `;
  }
}
