# @mindx/boardroom-ui

Public-facing UI for **boardroom-service**, **dojo-service**, and
**warcouncil-service**. Single Lit-element app; the same bundle renders
under three different Apache vhost paths and self-orients based on
hostname.

## Components

- `<wallet-login svc>` — MetaMask connect → personal_sign challenge → JWT
- `<room-list svc>`    — public room directory, private rooms shown when signed in
- `<convene-panel svc room-id>` — WebSocket-driven live convene with vote.delta streaming + verdict.final
- `<personhood-card>`  — declare self / vouch / view status (dojo)
- `<boardroom-app>`    — hash router + nav (`#/`, `#/dojo`, `#/warcouncil`, `#/room/{svc}/{id}`)

## Hostname detection

The shell picks the "primary service" from `location.hostname`:

- `mindx.pythai.net` → primary = `boardroom`
- `mastermind.pythai.net` (or `warcouncil.*`) → primary = `warcouncil`

The dojo is always accessible via `#/dojo`. War-council is a tab when
rendered from mindx (and the primary when rendered from mastermind).

## Run

```bash
cd openagents/dapp_kit/templates/boardroom-ui
npm install
npm run dev
# → http://127.0.0.1:5173
```

Vite proxy in `vite.config.ts` forwards `/boardroom-svc`, `/dojo-svc`,
`/warcouncil-svc` to the local Node services for dev.

## Build for deploy

```bash
npm run build
# dist/ → copy to /var/www/mindx.pythai.net/boardroom-ui/
```

Apache fragment (deploy/apache/boardroom-ui.conf):

```apache
Alias /boardroom    /var/www/mindx.pythai.net/boardroom-ui/dist
Alias /dojo         /var/www/mindx.pythai.net/boardroom-ui/dist
<Directory /var/www/mindx.pythai.net/boardroom-ui/dist>
  Require all granted
  Options -Indexes
</Directory>
```

The same `dist/` bundle serves both `/boardroom` and `/dojo` (hash router
decides which view). For the war-council, deploy under
`mastermind.pythai.net` with the same `dist/`.

## Wallet auth flow

1. User clicks "sign in to boardroom".
2. `<wallet-login>` calls `window.ethereum.request('eth_requestAccounts')`.
3. UI calls `POST /boardroom-svc/auth/challenge { wallet }`.
4. UI calls `window.ethereum.request('personal_sign', [message, wallet])`.
5. UI calls `POST /boardroom-svc/auth/verify { challenge_id, signature }`.
6. JWT stored in localStorage under `boardroom_jwt`.
7. All subsequent requests carry `Authorization: Bearer <jwt>`.

Each service has an independent token slot (`boardroom_jwt`, `dojo_jwt`,
`warcouncil_jwt`). Signing into one does not authorize the others — a
hostile boardroom token cannot read the war-council, and vice versa.
