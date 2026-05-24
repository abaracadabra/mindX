// SPDX-License-Identifier: Apache-2.0
//
// @bankoneth/ui — Lit 3 Web Components for bankoneth.
//
// Two layers:
//   - primitives/  — token-driven building blocks (b-button, b-input, …)
//                    consumers can use directly to build custom flows
//   - hero forms   — the three high-level claim flows (claim, purchase, host)
//
// All components share the design-token foundation in src/tokens/, which
// exposes CSS custom properties on :host. Override `--b-color-accent` etc.
// globally to re-skin every component at once.

// ── Design tokens ────────────────────────────────────────────────
export { tokens, motion, icon, type IconName } from "./tokens";

// ── Primitives ───────────────────────────────────────────────────
export * from "./primitives";

// ── Hero flows ───────────────────────────────────────────────────
export { BankonethClaim }       from "./claim-form";
export { BankonethPurchase }    from "./eth-purchase-form";
export { BankonethHost }        from "./host-domain-form";

// ── Secondary components ─────────────────────────────────────────
export { BankonethPricing }     from "./pricing-panel";
export { BankonethInftToggle }  from "./inft-toggle";
export { BankonethPaymentTabs, type PaymentRail } from "./payment-tabs";
export { BankonethFlowTabs }    from "./flow-tabs";
export { BankonethAgenticPlaceToggle } from "./agenticplace-toggle";
