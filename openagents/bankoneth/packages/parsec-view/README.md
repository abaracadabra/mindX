# @bankoneth/parsec-view

Native **parsec-wallet** view-module for the bankon.eth subdomain minter, agent
registry, and a generic ABI explorer — EVM, vanilla TS, **no Lit, no iframe**.

It renders entirely through a `ParsecHost` (parsec's own `el`/`btn`/`input`/`toast`
+ `store` + `ethers`), so the result is a first-class parsec view with Blueprint
styling and the parsec router. This supersedes the Lit `@bankoneth/parsec-adapter`
(parsec is vanilla-TS + Blueprint, not Lit).

## Shape

- `createBankonDeployView(host: ParsecHost): { render(): HTMLElement }` — the factory.
- `bankon-forms.ts` — the typed (production) port of the prototype `packages/web/bankon-forms.js`.
- `host.ts` — the `ParsecHost` seam.

## Drop into parsec-wallet

1. `pnpm add @bankoneth/parsec-view` (or vendor `dist/`).
2. Copy `src/parsec-adapter.example.ts` → `parsec-wallet/src/views/bankon-deploy.ts`
   (it wires parsec's real `el/btn/input/toast/store` + `ethers` into the factory).
3. Register the route in `parsec-wallet/src/main.ts`:
   ```ts
   registerView('bankon-deploy',
     lazyView(async () => (await import('./views/bankon-deploy')).bankonDeployView));
   ```
   and link to it from the dashboard with `store.navigate('bankon-deploy')`.
4. Serve the contract surface: copy `packages/web/public/*`
   (`bankon.contracts.json`, `abis/`, `deployments/`) into
   `parsec-wallet/public/bankon/` and set `publicBase: "/bankon"` in the adapter.

The `bankon` namespace already exists in
`parsec-wallet/src/lib/namespaces/registry` (used by the `name-*` views, which
are Algorand/NFD-centric); this view adds the **EVM bankon.eth** surface
alongside it.

## Build / typecheck

```bash
pnpm i && pnpm build      # tsc → dist/
pnpm typecheck
```

`ethers` v6 is a peer dependency (parsec already ships it).
