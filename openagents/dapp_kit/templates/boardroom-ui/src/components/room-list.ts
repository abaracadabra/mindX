/**
 * <room-list svc="boardroom|warcouncil"></room-list>
 *
 * Public room directory. Loads /rooms from the chosen service. If the user
 * is signed in, also shows private rooms they have access to.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { Api, getToken } from '../api.js';
import type { Service, Room } from '../api.js';

@customElement('room-list')
export class RoomList extends LitElement {
  static styles = css`
    :host { display: block; font-family: var(--mono, monospace); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--border, #2a2a2a); }
    th { color: var(--text2, #888); text-transform: uppercase; font-size: 10px; letter-spacing: 1px; }
    tr.protected td:first-child::before { content: '★ '; color: var(--accent, #5a92ff); }
    .empty { color: var(--text2, #666); padding: 14px 0; font-style: italic; }
    .err { color: var(--red, #f55); padding: 14px 0; }
    .mode-private    { color: var(--violet, #d2a8ff); }
    .mode-public_invite { color: var(--amber, #e3b341); }
    .mode-public_open   { color: var(--green, #56d364); }
  `;

  @property() svc: Service = 'boardroom';
  @state() private _rooms: Room[] = [];
  @state() private _err = '';
  @state() private _loading = true;

  async connectedCallback() {
    super.connectedCallback();
    await this._reload();
    // Refresh on login/logout events.
    document.addEventListener('login', () => void this._reload());
    document.addEventListener('logout', () => void this._reload());
  }

  private async _reload() {
    this._loading = true;
    this._err = '';
    try {
      const r = await Api.rooms(this.svc);
      this._rooms = r.rooms;
    } catch (e) {
      this._err = (e as Error).message;
    } finally {
      this._loading = false;
    }
  }

  render() {
    if (this._loading) return html`<div class="empty">loading rooms…</div>`;
    if (this._err) return html`<div class="err">${this._err}</div>`;
    if (!this._rooms.length) return html`<div class="empty">No rooms visible. ${getToken(this.svc) ? '' : 'Sign in to see private rooms.'}</div>`;
    return html`
      <table>
        <thead>
          <tr><th>Room</th><th>Mode</th><th>Seats</th><th>Created</th><th></th></tr>
        </thead>
        <tbody>
          ${this._rooms.map(r => html`
            <tr class=${r.protected ? 'protected' : ''}>
              <td>${r.name}</td>
              <td class="mode-${r.mode}">${r.mode}</td>
              <td>${r.seat_count}</td>
              <td>${new Date(r.created_at * 1000).toISOString().slice(0, 10)}</td>
              <td><a href=${`#/room/${this.svc}/${r.room_id}`}>open →</a></td>
            </tr>
          `)}
        </tbody>
      </table>
    `;
  }
}
