// SPDX-License-Identifier: Apache-2.0
//
// Shared helper for the disconnected-preview pattern (Phase C of the
// connection-refit plan). Every component with a write CTA imports this
// to keep the per-file diff tiny.
//
// Usage in a Lit component's render:
//
//   ${this.client
//     ? html`<b-button @click=${this._submit}>Save records</b-button>`
//     : html`<b-button variant="secondary"
//                      @click=${() => requestConnect(this)}
//             >Connect to save records</b-button>`}

/**
 * Bubble a `request-connect` CustomEvent from the host element. The shell
 * (main.ts / manage-page.ts) listens on the document root and calls
 * `session.connect()` in response.
 */
export function requestConnect(host: HTMLElement): void {
  host.dispatchEvent(new CustomEvent("request-connect", {
    bubbles: true,
    composed: true,
  }));
}

/** Helper used by `${connectLabel(this.client, "Save records")}`. */
export function connectLabel(client: unknown, action: string): string {
  return client ? action : `Connect to ${action.toLowerCase()}`;
}
