# @bankoneth/react

Production **React** component for the bankon.eth subdomain minter, agent
registry, and a generic ABI explorer. `.tsx` production surface (the `.js`
prototype is `packages/web/bankoneth.html`).

```tsx
import { BankonDeploy } from "@bankoneth/react";

export default function Page() {
  return <BankonDeploy publicBase="/bankon" />;
}
```

- Serve `packages/web/public/*` (`bankon.contracts.json`, `abis/`, `deployments/`)
  under the `publicBase` path (default `/bankon`).
- Uses raw `window.ethereum` + `ethers` v6 by default; pass `getProvider` to plug
  in wagmi / RainbowKit / any EIP-1193 source.
- Zero CSS setup — ships minimal inline styles; wrap with `className` to theme.

Peers: `react >=18`, `ethers ^6`. Build: `pnpm build` (tsc → `dist/`).

`src/bankon-forms.ts` is the shared call-construction core (mirror of
`packages/web/bankon-forms.js` and `packages/parsec-view/src/bankon-forms.ts`).
