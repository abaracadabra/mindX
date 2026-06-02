// SPDX-License-Identifier: Apache-2.0
//
// payment-tabs.ts — preserved for backward compatibility.
//
// The new <b-rail-switcher> primitive supersedes this; consumers using the
// legacy <bankoneth-payment-tabs> tag get a thin shim that re-uses the new
// component's internals (same events, same `selected` semantics).

import "./primitives/b-rail-switcher";

export {
  BRailSwitcher as BankonethPaymentTabs,
  type Rail as PaymentRail,
} from "./primitives/b-rail-switcher";
