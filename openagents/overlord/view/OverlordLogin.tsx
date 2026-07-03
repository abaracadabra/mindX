// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — OverlordLogin.tsx
//
// A thin React reference view for the overlord/overseer login. Pure viem via
// @openagents/wallet (EIP-6963), no RainbowKit dependency (RainbowKit-style UX
// only). It connects, signs the canonical challenge, and resolves privilege
// CLIENT-SIDE for preview. The authoritative resolution + session belongs to
// the server (POST to `verifyUrl`); this view shows the same state the server
// will compute, so UX and policy never disagree.

import { useCallback, useState } from "react";
import {
  createPublicClient,
  http,
  type Address,
  type Hex,
  type PublicClient,
} from "viem";
import { connect, signMessage, type ConnectedAccount } from "@openagents/wallet";
import {
  buildChallenge,
  resolvePrivilege,
  type OverlordConfig,
  type Privilege,
} from "../src/index.js";

export interface OverlordLoginProps {
  config: OverlordConfig;
  /** Scope embedded in the challenge (e.g. service or room id). */
  scope?: string;
  /**
   * PublicClient bound to `config.holding.chainId` for holdings reads. If
   * omitted, one is built from `rpcUrl` (or the connected account's client).
   */
  publicClient?: PublicClient;
  rpcUrl?: string;
  /** Fired with the client-side preview resolution. */
  onResolved?: (p: Privilege) => void;
  /**
   * Optional authoritative endpoint. POSTs {address, message, signature, scope}
   * for the server to re-resolve and issue a session.
   */
  verifyUrl?: string;
}

const ROLE_COLOR: Record<string, string> = {
  public: "#6b7280",
  member: "#2563eb",
  overseer: "#7c3aed",
  overlord: "#d4af37",
};

function randomNonce(): string {
  const b = new Uint8Array(16);
  (globalThis.crypto ?? ({} as Crypto)).getRandomValues?.(b);
  return "0x" + Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
}

export function OverlordLogin(props: OverlordLoginProps): JSX.Element {
  const { config, scope = config.domain, onResolved, verifyUrl } = props;
  const [account, setAccount] = useState<ConnectedAccount | null>(null);
  const [priv, setPriv] = useState<Privilege | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readClient = useCallback(
    (acc: ConnectedAccount): PublicClient => {
      if (props.publicClient) return props.publicClient;
      if (props.rpcUrl) return createPublicClient({ transport: http(props.rpcUrl) });
      return acc.publicClient; // best-effort: connected chain
    },
    [props.publicClient, props.rpcUrl],
  );

  const onLogin = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const acc = account ?? (await connect());
      setAccount(acc);
      const address = acc.address as Address;
      const message = buildChallenge({
        domain: config.domain,
        address,
        scope,
        nonce: randomNonce(),
      });
      const signature = (await signMessage(acc, message)) as Hex;

      const resolved = await resolvePrivilege({
        claimed: address,
        message,
        signature,
        config,
        publicClient: readClient(acc),
      });
      setPriv(resolved);
      onResolved?.(resolved);

      if (verifyUrl) {
        // Authoritative resolution + session lives server-side.
        await fetch(verifyUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ address, message, signature, scope }),
        }).catch(() => undefined);
      }
    } catch (e) {
      setError((e as Error)?.message?.slice(0, 160) ?? "login failed");
    } finally {
      setBusy(false);
    }
  }, [account, config, scope, onResolved, verifyUrl, readClient]);

  const color = priv ? ROLE_COLOR[priv.role] ?? "#6b7280" : "#6b7280";

  return (
    <div className="overlord-login" style={{ fontFamily: "ui-sans-serif, system-ui", maxWidth: 420 }}>
      <button
        onClick={onLogin}
        disabled={busy}
        style={{
          width: "100%",
          padding: "12px 16px",
          borderRadius: 8,
          border: `1px solid ${color}`,
          background: busy ? "#11151c" : "#0b0e13",
          color: "#e6edf3",
          fontWeight: 700,
          letterSpacing: ".06em",
          cursor: busy ? "wait" : "pointer",
        }}
      >
        {busy ? "SIGNING…" : priv ? "RE-VERIFY" : "CONNECT WALLET"}
      </button>

      {error && <p style={{ color: "#f87171", fontSize: 13 }}>{error}</p>}

      {priv && (
        <div style={{ marginTop: 12, padding: "12px 14px", border: `1px solid ${color}`, borderRadius: 8, fontSize: 13, color: "#9aa4b2" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <strong style={{ color, textTransform: "uppercase", letterSpacing: ".06em" }}>
              {priv.role} · L{priv.level}
            </strong>
            <span style={{ color: priv.privileged ? "#22c55e" : "#6b7280" }}>
              {priv.privileged ? "privileged" : "public"}
            </span>
          </div>
          <div style={{ marginTop: 6, wordBreak: "break-all" }}>{priv.address}</div>
          <div style={{ marginTop: 4 }}>{priv.reason}</div>
          {priv.holding && (
            <div style={{ marginTop: 4 }}>
              holding {priv.holding.amount.toString()} ·{" "}
              {priv.holding.tenureSec != null
                ? `held ${Math.floor(priv.holding.tenureSec / 86400)}d`
                : "tenure unknown"}
            </div>
          )}
          <div style={{ marginTop: 4, opacity: 0.8 }}>
            time: {priv.asOf.promisedBy} · {priv.asOf.consensus}
          </div>
        </div>
      )}
    </div>
  );
}

export default OverlordLogin;
