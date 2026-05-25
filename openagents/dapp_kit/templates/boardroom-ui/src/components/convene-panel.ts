/**
 * <convene-panel svc="boardroom|warcouncil" room-id="..."></convene-panel>
 *
 * WebSocket-driven convene UI:
 *   - Opens WSS connection to /<svc>-svc/rooms/{id}/ws with the JWT
 *   - Renders live vote.delta streams per seat
 *   - Submits a convene frame when the user types a directive
 *   - Shows verdict.final when it lands
 *
 * Demonstrates the WS protocol end-to-end. Read-only observers can use
 * the SSE /observe endpoint instead; this component is for participants.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { getToken } from '../api.js';
import type { Service } from '../api.js';

interface SeatTrace { role: string; deltas: string[]; complete: boolean; vote?: 'accept' | 'reject' | 'abstain' }

@customElement('convene-panel')
export class ConvenePanel extends LitElement {
  static styles = css`
    :host { display: block; font-family: var(--mono, monospace); }
    .row { display: flex; gap: 8px; margin-bottom: 12px; align-items: flex-start; }
    textarea { flex: 1; min-height: 60px; background: var(--surface2, #161a22); color: var(--text, #ddd); border: 1px solid var(--border, #2a2a2a); padding: 8px; border-radius: 4px; font-family: inherit; font-size: 13px; }
    button { background: var(--accent, #5a92ff); color: white; border: none; padding: 10px 18px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 13px; align-self: flex-start; }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    .ws-status { font-size: 11px; color: var(--text2, #888); margin-bottom: 8px; }
    .ws-status.open { color: var(--green, #56d364); }
    .ws-status.err  { color: var(--red, #f55); }
    .seat { border-left: 3px solid var(--border, #2a2a2a); padding: 8px 12px; margin: 8px 0; }
    .seat.complete-accept  { border-left-color: var(--green, #56d364); }
    .seat.complete-reject  { border-left-color: var(--red, #f55); }
    .seat.complete-abstain { border-left-color: var(--text2, #888); }
    .seat h4 { margin: 0 0 4px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
    .delta { font-size: 12px; color: var(--text, #ddd); white-space: pre-wrap; line-height: 1.4; }
    .verdict { margin-top: 16px; padding: 12px; border: 2px solid var(--accent, #5a92ff); border-radius: 6px; font-size: 14px; }
    .verdict.PASSED   { border-color: var(--green, #56d364); }
    .verdict.REJECTED, .verdict.VETOED { border-color: var(--red, #f55); }
    .verdict.TIED     { border-color: var(--amber, #e3b341); }
  `;

  @property() svc: Service = 'boardroom';
  @property({ attribute: 'room-id' }) roomId = '';
  @state() private _ws: WebSocket | null = null;
  @state() private _wsStatus: 'idle' | 'connecting' | 'open' | 'err' | 'closed' = 'idle';
  @state() private _wsMsg = '';
  @state() private _seats = new Map<string, SeatTrace>();
  @state() private _verdict: { value: string; accept_weight: number; reject_weight: number; veto_by: string[] } | null = null;
  @state() private _directive = '';
  @state() private _running = false;

  connectedCallback() { super.connectedCallback(); this._connect(); }
  disconnectedCallback() { super.disconnectedCallback(); this._ws?.close(); }

  private _connect() {
    const tok = getToken(this.svc);
    if (!tok) { this._wsStatus = 'err'; this._wsMsg = 'sign in first'; return; }
    if (!this.roomId) { this._wsStatus = 'err'; this._wsMsg = 'no room_id'; return; }
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/${this.svc}-svc/rooms/${this.roomId}/ws?token=${encodeURIComponent(tok)}`;
    this._wsStatus = 'connecting';
    this._wsMsg = '';
    const ws = new WebSocket(url);
    ws.onopen = () => { this._wsStatus = 'open'; this._wsMsg = 'connected'; };
    ws.onerror = () => { this._wsStatus = 'err'; this._wsMsg = 'connection error'; };
    ws.onclose = () => { this._wsStatus = 'closed'; this._wsMsg = 'closed'; };
    ws.onmessage = (ev) => this._handle(JSON.parse(ev.data));
    this._ws = ws;
  }

  private _handle(frame: { type: string; [k: string]: unknown }) {
    if (frame.type === 'hello') {
      const seats = frame.seats as Array<{ role: string }>;
      const m = new Map<string, SeatTrace>();
      for (const s of seats) m.set(s.role, { role: s.role, deltas: [], complete: false });
      this._seats = m;
    } else if (frame.type === 'vote.start') {
      this._verdict = null;
      this._running = true;
      // reset deltas
      for (const v of this._seats.values()) { v.deltas = []; v.complete = false; v.vote = undefined; }
      this.requestUpdate();
    } else if (frame.type === 'vote.delta') {
      const seat = String(frame.seat);
      const delta = String(frame.content_delta ?? '');
      const t = this._seats.get(seat);
      if (t) { t.deltas.push(delta); this.requestUpdate(); }
    } else if (frame.type === 'vote.complete') {
      const seat = String(frame.seat);
      const t = this._seats.get(seat);
      if (t) {
        t.complete = true;
        t.vote = frame.vote as SeatTrace['vote'];
        this.requestUpdate();
      }
    } else if (frame.type === 'verdict.final') {
      this._verdict = frame.verdict as typeof this._verdict;
      this._running = false;
      this.requestUpdate();
    } else if (frame.type === 'error') {
      this._wsMsg = `error: ${frame.code}`;
      this._wsStatus = 'err';
    }
  }

  private _submit() {
    if (!this._ws || this._ws.readyState !== WebSocket.OPEN) return;
    if (!this._directive.trim()) return;
    this._ws.send(JSON.stringify({
      type: 'convene',
      directive: this._directive.trim(),
      importance: 'standard',
    }));
  }

  render() {
    return html`
      <div class="ws-status ${this._wsStatus}">${this._wsStatus} — ${this._wsMsg}</div>
      <div class="row">
        <textarea
          placeholder="Directive for the room…"
          .value=${this._directive}
          @input=${(e: Event) => this._directive = (e.target as HTMLTextAreaElement).value}
        ></textarea>
        <button
          ?disabled=${this._wsStatus !== 'open' || !this._directive.trim() || this._running}
          @click=${this._submit}
        >convene</button>
      </div>
      ${Array.from(this._seats.values()).map(s => html`
        <div class="seat ${s.complete && s.vote ? 'complete-' + s.vote : ''}">
          <h4>${s.role}${s.vote ? ` — vote: ${s.vote}` : ''}</h4>
          <div class="delta">${s.deltas.join('')}</div>
        </div>
      `)}
      ${this._verdict ? html`
        <div class="verdict ${this._verdict.value}">
          <strong>${this._verdict.value}</strong> — accept: ${this._verdict.accept_weight} · reject: ${this._verdict.reject_weight}
          ${this._verdict.veto_by.length ? html` · veto by ${this._verdict.veto_by.join(', ')}` : ''}
        </div>
      ` : ''}
    `;
  }
}
