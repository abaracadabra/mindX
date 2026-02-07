# mindX Dapp frontend template

Template for wallet-connected / API-backed UIs: **use `.js` for prototypes and hacks**, then **migrate to `.ts` and `.tsx` for production and financial services**.

## Layout

```
dapp-template/
├── index.html      # Entry HTML
├── dapp.js         # Prototype logic (plain JS)
├── styled.css      # Prototype styles
├── README.md       # This file
├── ts/             # Production: TypeScript entry and types
│   ├── main.ts
│   └── config.ts
└── src/            # Production: TSX components
    ├── App.tsx
    ├── Wallet.tsx
    └── theme.ts
```

## Workflow

### 1. Prototype (current files)

- **index.html** – Shell: one app root, script/style links.
- **dapp.js** – All logic in one file; globals or IIFE; quick DOM/API/wallet hacks.
- **styled.css** – CSS variables and layout; keep naming consistent for later theme.

Use these to validate flows (connect wallet, call backend, render) without build steps.

### 2. Migrate to production and financial services

For production and financial services (compliance, audits, maintainability):

1. **TypeScript (`.ts`)**
   - Move config and API client to `ts/config.ts`, `ts/api.ts`.
   - Add types for backend payloads and wallet (e.g. `ts/types.ts`).
   - Entry: `ts/main.ts` that mounts the app and sets globals (e.g. `window.MINDX_API_URL`).

2. **React + TSX (`.tsx`)**
   - Move UI into components under `src/`: e.g. `App.tsx`, `Wallet.tsx`, `Content.tsx`.
   - Use a shared theme (e.g. `src/theme.ts`) that mirrors `styled.css` variables.
   - Build with Vite + `@vitejs/plugin-react` and `tsc`; output to a single bundle or use the same `index.html` with a script tag to the built JS.

3. **What to keep**
   - **styled.css** – Can stay as the single stylesheet; or replace with CSS-in-JS / Tailwind in TSX, reusing the same design tokens.
   - **index.html** – Keep as entry; point the script to the built `main.ts` output (e.g. `assets/main.js`) for production.

### 3. Checklist for production/financial

- [ ] All user-facing and API-facing logic in `.ts` / `.tsx` with strict types.
- [ ] No critical secrets or keys in frontend; use backend auth (e.g. challenge–response with wallet).
- [ ] API base and feature flags from env or config, not hardcoded.
- [ ] Error handling and logging suitable for support and audits.
- [ ] Build and lint: `tsc --noEmit`, ESLint, and a single production bundle (or chunked) for deployment.

## Running the prototype

Serve the folder (e.g. from `mindx_frontend_ui` or backend). Open `index.html`; ensure `dapp.js` and `styled.css` load. Set `window.MINDX_BACKEND_PORT` or `window.MINDX_API_URL` if the API is not on `localhost:8000`.

## Building the production bundle

For the `.ts` / `.tsx` version: use Vite + React + TypeScript (e.g. `npm create vite@latest . -- --template react-ts` in a copy of this folder, then move `ts/*` and `src/*` into the Vite `src/`). Ensure `ts/types.d.ts` (or a global `*.d.ts`) declares `window.ethereum` and `MINDX_*` so TypeScript and ESLint are satisfied.

## mindX integration

- Wallet auth can follow the same challenge–response flow as `login.html` (viem + backend `/users/challenge`, `/users/authenticate`).
- API base should point at the mindX backend (e.g. `http://localhost:8000`); use `/mindterm/static/xterm/` for local xterm assets if the UI embeds a terminal.
