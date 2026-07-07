# Understanding `.mjs`: ECMAScript Modules in the Node Runtime

*Professor Codephreak — rage.pythai.net — June 2026*

A single character of file extension carries a surprising amount of meaning. When a file in the PYTHAI Node surface ends in `.mjs` rather than `.js` or `.cjs`, it is making a declaration to the runtime about which of two incompatible module systems governs it. Most of the friction developers encounter with modern Node — the `Cannot use import statement outside a module` error, the `ERR_REQUIRE_ESM` wall, the mysterious absence of `__dirname` — traces back to a misunderstanding of what that extension actually does. This article is a deep dive into the `.mjs` file: what it is, why it exists, what changes inside one, and how it is used in practice across the daemons and clients that make up the mindX, AgenticPlace, and BANKON stack.

This is a companion to the file-level deep dives already published here, in the same spirit as [Understanding SocraticReasoning.py](https://rage.pythai.net/understanding-socraticreasoning-py/). Where that piece reads a single Python source file as an artifact, this one reads a single extension as a contract between author and runtime.

## What a `.mjs` file is

A `.mjs` file is a JavaScript source file that Node.js will always interpret as an **ECMAScript module** (ESM), the module system standardized by the ECMAScript committee in 2015 around the `import` and `export` keywords. It stands in contrast to **CommonJS** (CJS), the original Node module system built on `require()` and `module.exports`, which predates the language standard and was, for a decade, the only module format Node understood.

The extension exists because of an ambiguity problem. Node was born speaking CommonJS, and every `.js` file was a CommonJS module. When the standardized `import`/`export` syntax arrived, the runtime needed a way to tell the two formats apart, because they differ in ways that cannot be reconciled at parse time — one resolves dependencies synchronously and dynamically, the other resolves them statically and asynchronously. Rather than overload `.js` and guess, Node introduced two unambiguous extensions: `.mjs`, which is *always* an ES module, and `.cjs`, which is *always* CommonJS. The `.mjs` extension was added experimentally in Node v8.5.0 and stabilized in v13.2.0, at which point it no longer required an experimental flag.

The practical consequence is that `.mjs` is the one way to write an ES module that is correct regardless of project configuration. A `.js` file's meaning depends on surrounding context; a `.mjs` file's meaning does not.

## How Node decides which module system a file uses

Node resolves the module system of any file through a small, deterministic set of rules. There are three inputs: the file extension, the nearest `package.json`, and — in recent versions — the syntax of the file itself.

| File | Module system |
| --- | --- |
| `*.mjs` | Always ESM |
| `*.cjs` | Always CommonJS |
| `*.js` | ESM if the nearest `package.json` has `"type": "module"`; CommonJS if `"type": "commonjs"` or the field is absent |

The `"type"` field was introduced alongside the extensions in v13.2.0 and is the project-level lever. Setting `"type": "module"` flips every `.js` file in that package to ESM, after which `.cjs` becomes the escape hatch for any file that still needs CommonJS. Leaving the field out — still the default — keeps `.js` as CommonJS, and `.mjs` becomes the escape hatch in the other direction. Either way, the `.mjs` and `.cjs` extensions override the `"type"` field; they are absolute.

Recent Node versions add a fourth path: when a `.js` file is genuinely ambiguous, the runtime can inspect it for module syntax and, if it finds `import`/`export`, run it as ESM, otherwise fall back to CommonJS. This syntax detection is convenient, but it is a fallback for ambiguity, not a substitute for intent. Naming a file `.mjs` states the intent directly and spares the runtime — and the next engineer to read the tree — the guesswork. For a flat `snake_case` layout where a single directory mixes settlement contracts, agent clients, and a payment daemon, that explicitness is worth more than the keystrokes it costs.

## What the syntax looks like

Inside a `.mjs` file you use `import` and `export` rather than `require` and `module.exports`. A module may expose any number of *named* exports and at most one *default* export.

```js
// chain_registry.mjs
export const SETTLEMENT_CHAIN_ID = 16661; // 0G Aristotle mainnet

export function resolveRpc(chainId) {
  return RPC_MAP[chainId] ?? null;
}

export default class ChainRegistry {
  constructor(map) { this.map = map; }
}
```

A consumer imports them by name, by default binding, or both, and — this is the part that trips up engineers arriving from CommonJS — the file extension on a relative import is **mandatory**:

```js
// agent.mjs
import ChainRegistry, { SETTLEMENT_CHAIN_ID, resolveRpc } from './chain_registry.mjs';
```

CommonJS allowed `require('./chain_registry')` with the extension elided and the resolution algorithm filling in the blank. ESM does not. Relative specifiers such as `./chain_registry.mjs` must carry their extension; bare specifiers such as `algosdk` continue to resolve to a package's entry point through `node_modules`. This strictness is deliberate: it makes module resolution statically analyzable, which is what enables bundler tree-shaking and ahead-of-time tooling to reason about a dependency graph without executing it.

Imports are also *static and hoisted*. An `import` statement is not a function call that runs when control reaches it; it is a declaration the runtime resolves before the module body executes. When you need conditional or lazy loading — load a chain adapter only if a transaction targets that chain — you reach for the dynamic `import()` form, which returns a promise and is legal in both ESM and CommonJS:

```js
const { ThrusterVault } = await import('./adapters/thruster.mjs');
```

## What changes inside an ES module

Switching a file to ESM changes more than two keywords. Several runtime behaviors differ, and each one accounts for a class of migration bug.

An ES module is **strict mode by default**. There is no `'use strict'` pragma to add and no sloppy-mode fallback; the stricter semantics simply apply.

An ES module supports **top-level `await`**. You can await a promise at the outermost scope of the file, without wrapping it in an async function. This is genuinely useful for modules whose very initialization is asynchronous — reading a chain map off disk, fetching an oracle snapshot, opening a wallet — because the module's exports can depend on work that only a promise can express:

```js
// allchain.mjs — the data layer behind agenticplace.pythai.net/allchain.html
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

export const chains = JSON.parse(
  await readFile(join(here, 'allchain.json'), 'utf8'),
);
```

That example also shows the most common surprise of all: **`__dirname` and `__filename` do not exist in an ES module**, and neither does `require`. The replacement is `import.meta.url`, a URL string pointing at the current module, which you convert to a filesystem path with `fileURLToPath`. On Node 20.11 and later (and 21.2 and later), the runtime offers the shortcuts `import.meta.dirname` and `import.meta.filename`, which collapse the three-line dance above into a single property access. When you genuinely need a CommonJS `require` inside an ES module — to pull in a legacy package that only ships CommonJS — you synthesize one with `createRequire`:

```js
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const legacy = require('some-old-cjs-only-package');
```

## Interoperability, and the change that finally landed

For most of ESM's life on Node, interop ran in one direction cleanly and one direction badly. An ES module could always `import` a CommonJS module — the default export maps to `module.exports`, and Node's lexer extracts named exports where it can. The reverse was the problem. A CommonJS file could not `require()` an ES module; the attempt threw `ERR_REQUIRE_ESM`, and the only workaround was the asynchronous dynamic `import()`. Because `require()` is synchronous and `import()` is not, a large body of CommonJS code simply could not reach into the ESM ecosystem without restructuring around promises. That asymmetry, more than any other single factor, kept CommonJS entrenched as the *shipping* format even for packages authored in ESM.

That has now changed. Node 22 introduced the ability to `require()` an entire ES module graph from CommonJS, initially behind a flag; Node 23 turned it on by default; the capability was backported to the v20 line in v20.19.0; and at the end of 2025 it was marked **stable**. The implementation history is documented in Joyee Cheung's [require(esm): from experiment to stability](https://joyeecheung.github.io/blog/2025/12/30/require-esm-in-node-js-from-experiment-to-stability/), which is worth reading if you maintain dual-format packages. The one durable constraint is that a module graph reached through `require()` must not use top-level `await` — synchronous `require()` cannot wait on a promise, so a module that suspends at load is still off-limits to it. For those graphs, `import()` remains the path.

The strategic reading of this, for a stack that targets mainnet and ships Apache-2.0 packages, is that ESM is now safe to ship *directly*, without the defensive CommonJS transpile that used to be the price of broad compatibility. New packages can be ESM-only; the dual-package hazard that produced subtle duplicate-instance bugs is receding.

## Writing and running one in practice

There is nothing to install. Any file you name `.mjs` runs as an ES module under any current Node:

```bash
node wisdom.mjs
```

If you would rather not annotate individual files, declare the whole package as ESM in `package.json` and let `.js` carry the meaning, reserving `.cjs` for the exceptions:

```json
{
  "name": "wisdom-daemon",
  "type": "module",
  "exports": {
    ".": "./wisdom.js",
    "./x402": "./x402_gate.js"
  }
}
```

The `"exports"` field is the modern public surface of a package. It supersedes the old `"main"` entry point, lets you publish named subpaths, and supports *conditional* exports — different files for `import` versus `require` consumers — which is how a dual-format library serves both worlds from one published package:

```json
{
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.cjs"
    }
  }
}
```

TypeScript mirrors all of this with `.mts` (always an ES module) and `.cts` (always CommonJS), which compile down to `.mjs` and `.cjs` respectively. The mental model is identical; only the source extension differs.

## A worked example from the payment surface

The WISDOM daemon is built on pure `node:http` with no framework underneath it, which makes it a clean illustration of `.mjs` in anger. The payment logic lives in one module and the server in another, and the boundary between them is nothing more than `export` and `import`.

```js
// x402_gate.mjs — the payment-required contract
export const SCHEME = 'exact';
export const USDC_ASA = 31566704n; // Algorand mainnet USDC

export function paymentRequired(amount, asset = USDC_ASA) {
  return {
    x402Version: 1,
    accepts: [{
      scheme: SCHEME,
      network: 'algorand',
      asset: asset.toString(),
      amount: amount.toString(),
    }],
  };
}

export async function verifyReceipt(receipt, indexerUrl) {
  const res = await fetch(`${indexerUrl}/v2/transactions/${receipt.txid}`);
  if (!res.ok) return false;
  const tx = await res.json();
  return tx?.transaction?.['confirmed-round'] > 0;
}
```

```js
// wisdom.mjs — the daemon
import http from 'node:http';
import { paymentRequired, verifyReceipt } from './x402_gate.mjs';

const INDEXER = 'https://mainnet-idx.algonode.cloud';

const server = http.createServer(async (req, res) => {
  const header = req.headers['x-payment'];
  if (!header) {
    res.writeHead(402, { 'content-type': 'application/json' });
    res.end(JSON.stringify(paymentRequired(333_000n)));
    return;
  }
  const settled = await verifyReceipt(JSON.parse(header), INDEXER);
  res.writeHead(settled ? 200 : 402, { 'content-type': 'application/json' });
  res.end(JSON.stringify(settled ? { ok: true } : paymentRequired(333_000n)));
});

server.listen(9876);
```

Two things in this pair are pure ESM and would not work in a CommonJS file without rework: the `import` statements with their explicit `.mjs` extensions, and the `await` inside the request handler reaching for `verifyReceipt`. The `node:` prefix on the `http` import is an ESM-era convention worth adopting everywhere — it states unambiguously that you mean the built-in module and not some `http` package that happens to sit in `node_modules`. A parsec wallet client, a chain adapter resolved from `allchain.json`, or a Foundry-tested contract's TypeScript binding all slot into this same shape: small, single-purpose `.mjs` modules with explicit boundaries, each testable in isolation.

## When to reach for `.mjs`

The guidance reduces to a few clear cases. For a new package, declare `"type": "module"` and write `.js`, using `.mjs` only when you want a file to be ESM inside a package that is otherwise CommonJS. For a single script or a file that must be unambiguously an ES module regardless of where it lands — a standalone daemon, a migration utility, a one-off — name it `.mjs` and move on. For a library meant to be consumed widely, ship ESM directly now that `require(esm)` is stable, and offer a conditional `"exports"` map only if you still support Node versions that predate it. The throughline is that `.mjs` is the format with no hidden dependencies on configuration: it means exactly one thing, in every project, forever.

---

## References

- Node.js — *Modules: ECMAScript modules*: <https://nodejs.org/api/esm.html>
- Node.js — *Modules: Packages* (the `type` field and `exports` map): <https://nodejs.org/api/packages.html>
- Node.js — *Modules: CommonJS modules*: <https://nodejs.org/api/modules.html>
- MDN — *JavaScript modules*: <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules>
- Joyee Cheung — *require(esm) in Node.js: from experiment to stability*: <https://joyeecheung.github.io/blog/2025/12/30/require-esm-in-node-js-from-experiment-to-stability/>

## Related reading on rage.pythai.net

- [Understanding SocraticReasoning.py](https://rage.pythai.net/understanding-socraticreasoning-py/) — a sibling file-level deep dive in the mindX corpus
- [funAGI workflow](https://rage.pythai.net/funagi-workflow-fundamental-autonomous-general-intelligence-framework/) — the reasoning pipeline and the mindXtrain MI300X probe
- [Introducing Kuntai: DeepDive](https://rage.pythai.net/introducing-kuntai-deepdive/) — the long-form AI and blockchain analysis series
