# Record Editing — Phase 3.1

`<b-records-editor>` ([source](../packages/ui/src/manage/b-records-editor.ts))
edits any name's resolver records in a single transaction via the resolver's
`multicall(bytes[])` method.

## User flow

1. User opens their name's profile.
2. Editor pre-populates from `NameLookup.records` (fetched via
   [`lookupName()`](../packages/core/src/lookup.ts)).
3. User edits any of the supported keys across the **Identity** group
   (avatar / description / url / email / com.twitter / com.github) and
   the **Agentic edge** group (mindx.endpoint / bonafide.attestation /
   agent.capabilities / inft.uri / agenticplace.listing / x402.endpoint /
   algoid.did).
4. Click **Save records**. The editor builds one `setText(node, key, value)`
   call per changed record, bundles them into a single
   `multicall(bytes[])` call on the resolver, prompts the wallet, awaits
   confirmation.

## Contract path

- Resolver: `BankonSubnameResolver` (v1) or `BankonSubnameResolverV2`.
- Method: `multicall(bytes[] data) → bytes[]`.
- Per-element selector: `setText(bytes32 node, string key, string value)`
  selector `0x10f13a8c`.
- Gas: ~30k per `setText` + multicall overhead.

The editor only includes calls where the draft value differs from the
on-chain value — a no-op submit is impossible.

## Authorization

The resolver's `setText` is gated by `REGISTRAR_ROLE`. When the editor
is used from the registrar's UI (claim flow), the registrar holds the
role. When used from the manage flow by the end-user, the resolver
needs an additional `isAuthorised(node, sender)` hook — not present in
V1 or V2 today; deferred to a later iteration.

## Custom keys

Add a new spec to the `IDENTITY` or `AGENTIC` arrays in
`b-records-editor.ts` — `{ key, label, placeholder? }` — and the editor
will pick it up. The canonical text-record keys from
[ENSIP-5](https://docs.ens.domains/ensip/5) are recommended for cross-
client compatibility.

## Failure modes

- **No client wired.** The editor errors at submit if `client` prop is
  unset. Always pass the multicall client (see `manage-page.ts`).
- **REGISTRAR_ROLE missing.** The resolver's `setText` reverts. The
  editor surfaces the revert reason as `error` state.
- **Resolver doesn't support multicall.** V1/V2 both ship multicall via
  delegatecall — but a legacy PublicResolver pre-multicall would error.

## Further reading

- [ENSIP-5 text records](https://docs.ens.domains/ensip/5)
- [Resolver interfaces](https://docs.ens.domains/resolvers/interfaces)
- [`<b-records-editor>`](../packages/ui/src/manage/b-records-editor.ts)
- [`BankonSubnameResolverV2.md`](../contracts/BankonSubnameResolverV2.md)
