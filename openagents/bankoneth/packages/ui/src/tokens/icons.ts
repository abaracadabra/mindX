// SPDX-License-Identifier: Apache-2.0
//
// @bankoneth/ui — inline SVG icon set.
//
// Phosphor-style strokes at 1.5px (lighter than Material, heavier than
// Heroicons) sized at a 24×24 viewbox. All icons take `currentColor` so they
// inherit the consumer's text color via CSS.
//
// Each export is a Lit-renderable string of SVG markup. Components use it via
// the `unsafeHTML` directive or by composing it into their template:
//
//   import { icon } from "../tokens/icons";
//   html`<span class="ico">${unsafeHTML(icon.check)}</span>`

const wrap = (body: string, viewBox = "0 0 24 24") =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" fill="none" ` +
  `stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" ` +
  `width="1em" height="1em" aria-hidden="true" focusable="false">${body}</svg>`;

export const icon = {
  check:    wrap(`<polyline points="5 13 9 17 19 7"/>`),
  cross:    wrap(`<line x1="6" y1="6" x2="18" y2="18"/><line x1="6" y1="18" x2="18" y2="6"/>`),
  arrowLeft:  wrap(`<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>`),
  arrowRight: wrap(`<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>`),
  spinner:  wrap(`<path d="M21 12a9 9 0 1 1-3.5-7.1"/>`),
  search:   wrap(`<circle cx="11" cy="11" r="7"/><line x1="20" y1="20" x2="16.65" y2="16.65"/>`),
  wallet:   wrap(`<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><circle cx="16.5" cy="14" r="1.2" fill="currentColor"/>`),
  shield:   wrap(`<path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z"/>`),
  link:     wrap(`<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>`),
  copy:     wrap(`<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>`),
  external: wrap(`<path d="M14 3h7v7"/><path d="M21 3l-9 9"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/>`),
  info:     wrap(`<circle cx="12" cy="12" r="9"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>`),
  warn:     wrap(`<path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>`),
  cog:      wrap(`<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>`),
  ethereum: wrap(`<polygon points="12 2 5 12.5 12 16 19 12.5 12 2" fill="currentColor" stroke="none"/><polygon points="12 17.5 5 14 12 22 19 14 12 17.5" fill="currentColor" stroke="none" opacity="0.65"/>`),
  algorand: wrap(`<path d="M5 19l5-9 2.5 4.3L17 19M9 19l1.5-3M14 19l-2-7M7 19l3-7"/>`),
  usdc:     wrap(`<circle cx="12" cy="12" r="9"/><path d="M12 7v1.2"/><path d="M12 15.8V17"/><path d="M9 9.5c0-1.1 1-1.8 2.5-1.8s3 .7 3 1.8c0 1.4-1.5 1.6-3 2-1.5.3-3 .6-3 2 0 1.2 1.5 1.8 3 1.8s3-.6 3-1.8"/>`),
  clock:    wrap(`<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>`),
  agent:    wrap(`<circle cx="12" cy="8" r="3.5"/><path d="M5 21c0-3.5 3-6 7-6s7 2.5 7 6"/><circle cx="12" cy="8" r="0.6" fill="currentColor"/>`),
  flame:    wrap(`<path d="M12 3c1.5 3 5 5 5 9a5 5 0 1 1-10 0c0-1.6.6-3 1.6-4C9 7 10 5 12 3z"/>`),
} as const;

export type IconName = keyof typeof icon;
