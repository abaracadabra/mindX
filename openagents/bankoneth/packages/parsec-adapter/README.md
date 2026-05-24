# @bankoneth/parsec-adapter

> PARSEC wallet-component bridge for bankoneth. First-class consumer surface
> — PARSEC adopts this contract shape.

PARSEC is a wallet shell that loads feature modules ("components"). bankoneth
is one such component: it offers `bankon.eth` subname issuance, `.eth`
purchase, and hosted-`.eth` subdomain issuance from inside the wallet.

## Component contract

```ts
import { BankonethComponent } from "@bankoneth/parsec-adapter";

// PARSEC's startup code:
parsec.registerComponent(new BankonethComponent());
```

PARSEC then surfaces the component as a tab/route. When the user opens it:

```ts
component.mount(elem, {
  chainId: 1,
  accountAddress: "0x...",
  client: bankonethClient,           // BankonethClient from @bankoneth/core
  emit: (ev) => { /* PARSEC consumes typed events */ },
});
```

Events PARSEC observes:

- `tx:submitted` — bankoneth submitted a tx; PARSEC shows it in tx history
- `tx:confirmed` / `tx:reverted`
- `subname:claimed` — a `bankon.eth` subname was minted
- `domain:purchased` — a `.eth` 2LD was purchased
- `listing:published` — agenticplace.pythai.net listing was created

## License

Apache-2.0
