// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// EIP-6963 Multi-Injected Provider Discovery.
// Port of the discovery loop already running in production at
// mindx_frontend_ui/login.html. Browser-only API; the Tauri shell
// uses the same logic inside its webview.
//
// Spec: https://eips.ethereum.org/EIPS/eip-6963
// Contract: docs/services/wallet_connection_as_a_service.md §3.

export interface EIP1193Provider {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>;
  on?(event: string, listener: (...args: unknown[]) => void): void;
  removeListener?(event: string, listener: (...args: unknown[]) => void): void;
}

export interface ProviderInfo {
  uuid: string;
  name: string;
  icon: string;
  rdns: string;
}

export interface AnnouncedProvider {
  info: ProviderInfo;
  provider: EIP1193Provider;
}

/**
 * Discover EIP-6963-compatible providers.
 *
 * Emits `eip6963:requestProvider`, listens for `eip6963:announceProvider`
 * events for `waitMs` milliseconds, dedupes by `info.rdns`, and returns
 * the list. Falls back to wrapping `window.ethereum` as a synthetic
 * provider with `rdns: "legacy.injected"` when no events fire.
 *
 * @param waitMs how long to listen for announcements (default 500ms)
 * @returns deduped list of announced providers
 */
export async function discoverProviders(waitMs = 500): Promise<AnnouncedProvider[]> {
  if (typeof window === "undefined") return [];

  const seen = new Map<string, AnnouncedProvider>(); // dedup by rdns

  const handler = (event: Event) => {
    const detail = (event as CustomEvent).detail as AnnouncedProvider | undefined;
    if (!detail || !detail.info || !detail.provider) return;
    const rdns = detail.info.rdns;
    if (!rdns) return;
    // Keep the first announcement per rdns; later duplicates are ignored.
    if (!seen.has(rdns)) seen.set(rdns, detail);
  };

  window.addEventListener("eip6963:announceProvider", handler as EventListener);
  window.dispatchEvent(new Event("eip6963:requestProvider"));

  await new Promise((resolve) => setTimeout(resolve, waitMs));

  window.removeEventListener("eip6963:announceProvider", handler as EventListener);

  // Legacy fallback: wrap window.ethereum if nothing announced.
  if (seen.size === 0) {
    const eth = (window as unknown as { ethereum?: EIP1193Provider }).ethereum;
    if (eth) {
      seen.set("legacy.injected", {
        info: {
          uuid: "legacy-injected",
          name: "Injected Wallet",
          icon: "",
          rdns: "legacy.injected",
        },
        provider: eth,
      });
    }
  }

  return Array.from(seen.values());
}

/**
 * Pick a provider by preferred rdns, falling back to the first available.
 *
 * @param providers list returned by discoverProviders()
 * @param preferredRdns optional rdns to prefer (e.g. "io.metamask")
 * @returns the matched provider, or undefined when the list is empty
 */
export function pickProvider(
  providers: AnnouncedProvider[],
  preferredRdns?: string,
): AnnouncedProvider | undefined {
  if (providers.length === 0) return undefined;
  if (preferredRdns) {
    const match = providers.find((p) => p.info.rdns === preferredRdns);
    if (match) return match;
  }
  return providers[0];
}
