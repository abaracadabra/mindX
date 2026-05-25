/**
 * Entry — registers all custom elements + minimal hash router.
 *
 * Routes:
 *   #/                      → boardroom landing
 *   #/dojo                  → dojo standings + personhood
 *   #/warcouncil            → war-council landing
 *   #/room/{svc}/{id}       → single room view with convene panel
 */

import './components/wallet-login.js';
import './components/room-list.js';
import './components/personhood-card.js';
import './components/convene-panel.js';

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';

@customElement('boardroom-app')
class BoardroomApp extends LitElement {
  static styles = css`
    :host { display: block; max-width: 960px; margin: 0 auto; padding: 24px 20px; font-family: var(--mono, monospace); color: var(--text, #ddd); }
    header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid var(--border, #2a2a2a); margin-bottom: 24px; }
    h1 { font-size: 22px; margin: 0; }
    h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: var(--text2, #888); margin: 24px 0 12px; }
    nav { display: flex; gap: 12px; margin-bottom: 24px; }
    nav a { color: var(--text2, #888); text-decoration: none; padding: 4px 8px; border-radius: 4px; }
    nav a.active { color: var(--text, #ddd); background: var(--surface2, #161a22); }
    a { color: var(--accent, #5a92ff); }
  `;

  @state() private _route = window.location.hash || '#/';

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('hashchange', () => { this._route = window.location.hash || '#/'; });
  }

  private _renderRoom() {
    const m = this._route.match(/^#\/room\/(boardroom|warcouncil|dojo)\/(.+)$/);
    if (!m) return html`<p>invalid room link</p>`;
    const svc = m[1] as 'boardroom' | 'warcouncil' | 'dojo';
    const id = m[2]!;
    return html`
      <h2>Room: ${id}</h2>
      <convene-panel svc=${svc} room-id=${id}></convene-panel>
      <p><a href="#/${svc === 'boardroom' ? '' : svc}">← back</a></p>
    `;
  }

  private _renderHome(svc: 'boardroom' | 'warcouncil') {
    return html`
      <h2>${svc === 'boardroom' ? 'Boardroom Rooms' : 'War-Council Rooms'}</h2>
      <p style="color: var(--text2, #888); font-size: 12px;">
        ${svc === 'boardroom'
          ? html`mindX's default room is <b>mindx-private-boardroom</b> — CEO + 7 soldiers. Public rooms are created by anyone with personhood.`
          : html`mastermind's default room is <b>mastermind-warcouncil</b> — 13 original seats. Sun Tzu, Miyamoto Musashi, and DAIO are <em>opt-in seats</em> a cabinet member can add per session.`}
      </p>
      <room-list svc=${svc}></room-list>
    `;
  }

  private _renderDojo() {
    return html`
      <h2>Dojo — Reputation & Personhood</h2>
      <personhood-card></personhood-card>
    `;
  }

  render() {
    // pick which service this hostname is "primary" for — Apache vhosts will set
    // location.hostname; default to boardroom on mindx, warcouncil on mastermind.
    const isWar = location.hostname.startsWith('warcouncil') || location.hostname.startsWith('mastermind');
    const primary = isWar ? 'warcouncil' : 'boardroom';

    let body;
    if (this._route.startsWith('#/room/')) body = this._renderRoom();
    else if (this._route === '#/dojo') body = this._renderDojo();
    else if (this._route === '#/warcouncil') body = this._renderHome('warcouncil');
    else body = this._renderHome(primary);

    const active = (r: string) => this._route === r || (r === '#/' && (this._route === '' || this._route === '#/'));
    return html`
      <header>
        <h1>${primary === 'warcouncil' ? 'War Council' : 'mindX Boardroom'}</h1>
        <wallet-login svc=${primary}></wallet-login>
      </header>
      <nav>
        <a class=${active('#/') ? 'active' : ''} href="#/">${primary}</a>
        <a class=${active('#/dojo') ? 'active' : ''} href="#/dojo">dojo</a>
        ${!isWar ? html`<a class=${active('#/warcouncil') ? 'active' : ''} href="#/warcouncil">war-council</a>` : ''}
      </nav>
      ${body}
    `;
  }
}
