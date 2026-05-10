# Source code dossier for AgenticPlace integration of Parsec, x402, A2A, MCP, and AP2

The most consequential finding up front: **"Parsec / parsec-wallet" does not exist as a public, discoverable codebase as of May 7, 2026.** Despite exhaustive searching across 20+ GitHub URL paths, every npm scope variant, every PyPI candidate, the Algorand Foundation grants/bounties index, and Google web/site searches against `pythai.net`, `agenticplace.pythai.net`, and `bankon.pythai.net`, no public organization, repository, package, or smart contract publishes under the "Parsec" name in the agentic-wallet/Algorand/x402 problem space. The functional substrate that matches every technical claim attributed to "Parsec" in the user's notes — branded abstraction over GoPlausible's `x402-avm` runtime, agentic wallet creation on Algorand, Vault-backed signing — is **GoPlausible's published stack**: `algorand-remote-mcp-lite` (the "Wallet Edition" agentic wallet) plus `x402-avm` (the AVM x402 reference implementation, whose Algorand support was upstreamed into `coinbase/x402` via PR #361). The pragmatic conclusion is that **"Parsec" in the AgenticPlace blueprint is best treated as an internal/unreleased branding layer over GoPlausible's public substrate**, and the integration should be wired directly to that substrate while preserving the Parsec brand surface in AgenticPlace's UX. Everything in this dossier proceeds from that conclusion. The YouTube transcript at `youtu.be/cS5RjkW4aoY` could not be retrieved through any of 15 attempted services, search engines, or transcript aggregators — the video appears unindexed and is documented as a gap. The `agenticplace.pythai.net/allchain.html` page also could not be fetched and does not appear in any public crawl, so the chain mapping is reconstructed from the user's architectural constants rather than from the live HTML.

## Parsec wallet — search exhaustion and the GoPlausible substitution

Twenty distinct GitHub paths were probed directly: `github.com/parsec`, `parsec-finance`, `parsec-network`, `parseclabs`, `parsec-wallet`, `parsec-protocol`, `parsec-cloud`, `parallaxsecond`, `parsecnode`, `Scille/parsec-cloud`, plus npm scope `@parsec/*`, `@parsec-wallet/*`, `@parsec-fi/*`, and PyPI names `parsec-wallet`, `parsec-sdk`, `parsec-algorand`. The hits divide cleanly into **four unrelated namespaces**, none of which match the AgenticPlace use case: `parsecbroadcast`/`parsec-cloud` is the gaming/remote-desktop product (parsec.app), `parallaxsecond/parsec` is the CNCF Sandbox "Platform AbstRaction for SECurity" hardware-crypto API in Rust, `parsecnode/parsec` is the defunct PARS CryptoNote-fork coin, `Scille/parsec-cloud` is end-to-end-encrypted file sharing, and `parsec.finance`/`parsec.fi` was a DeFi/NFT analytics terminal that publicly shut down ("After 5 years parsec is now offline"). No npm package under `@parsec*` and no PyPI package named `parsec-wallet`, `parsec-sdk`, or `parsec-algorand` exists. The `AgenticPlace` GitHub org **does** exist and is owned by the BANKON/pythai team, but contains exactly one public repository — `AgenticPlace/mcp.agent`, a GCS/BigQuery MCP server — with no `parsec`, `wallet`, `allchain`, or factory contract. The `pythaiml` org contains `automindx`, `funAGI`, a `nicegui` fork, a `pgvectorscale` fork, an `ai.pythai.net` site repo, and an `ollama` fork — again no Parsec asset. The word "Parsec" appears nowhere in any retrieved GoPlausible README, x402-avm documentation page, AgenticPlace marketing copy, or pythai/agenticplace repository.

The substrate the user describes — "branded abstraction with GoPlausible x402-avm as runtime fallback," "agentic wallet creation on Algorand," dual-chain topology with Algorand for constitutional state — is the **GoPlausible** stack point-for-point. `https://github.com/GoPlausible/algorand-remote-mcp-lite` is explicitly marketed in its README as a *"complete and comprehensive Agentic Wallet for Algorand Blockchain using OAuth+OIDC identity, access, authentication and authorization,"* TypeScript, MIT, 5 stars. Its sibling `algorand-remote-mcp` is the cloud (SSE) Cloudflare Worker variant exposing 75+ Algorand tools over OAuth 2.2 + OIDC, and `algorand-mcp` is the local stdio variant. The custody model documented across the `daoauth.org` (Decentralized OAuth, "dAoAuth") protocol is **custodial / KMS-backed via HashiCorp Vault Transit engine**: Web 2.0 OAuth login is bound through OIDC to a Web 3.0 Algorand wallet held in Vault Transit, signing on the user/agent's behalf. Account type is **standard Algorand ed25519 (58-character) accounts** — *not* MPC, *not* ARC-58 plugin smart wallets (Akita's model), *not* passkey self-custody (Algorand Foundation's Rocca model scheduled for 2026), and *not* rekey-to. There are **no Solidity smart-wallet factory contracts and no PyTeal/TEAL contracts** attributable to GoPlausible's wallet layer; the wallet is purely an OAuth+Vault-fronted standard account.

Clone what actually exists today and rebrand it as "Parsec" inside AgenticPlace's namespace if that is the architectural intent: `git clone https://github.com/GoPlausible/algorand-remote-mcp-lite.git` for the agentic wallet edition, `git clone https://github.com/GoPlausible/algorand-remote-mcp.git` for the Cloudflare Worker SSE variant, `git clone https://github.com/GoPlausible/openclaw-algorand-plugin.git` for the OpenClaw plugin that bundles wallet-lite plus x402 skills, and `git clone https://github.com/GoPlausible/.github.git` for the canonical `profile/algorand-x402-documentation/` directory containing complete TypeScript and Python integration examples. **If AgenticPlace's "Parsec" is in fact a private, unreleased internal codebase, this dossier cannot inspect it**; the user should disclose the private repository URL or paste source for further analysis. If it is conceptual, the GoPlausible stack is the production-ready foundation to brand against.

## x402 — the canonical Coinbase implementation and its AVM fork

The canonical x402 protocol now lives at `https://github.com/x402-foundation/x402`, jointly governed by Coinbase and Cloudflare; `https://github.com/coinbase/x402` is now self-described as "a development fork" with all issues and PRs transferred upstream. The repository is Apache-2.0, ~5.4k stars, ~1.1k forks, 193+ contributors, and breaks down as 44.2% TypeScript, 35.3% Python, 19.6% Go, 0.4% Java. Clone with `git clone https://github.com/coinbase/x402.git` or canonically `git clone https://github.com/x402-foundation/x402.git`. The root tree contains `docs/` (GitBook source), `e2e/`, `examples/`, `go/`, `java/`, `python/`, `specs/`, `static/`, `typescript/`, plus `ROADMAP.md`, `PROJECT-IDEAS.md`, `CONTRIBUTING.md`, `SECURITY.md`. The protocol specs live in `specs/x402-specification.md` (transport-agnostic), `specs/schemes/exact/scheme_exact_evm.md` (EIP-3009 + Permit2), `specs/schemes/exact/scheme_exact_solana.md`, `specs/schemes/upto/scheme_upto.md` (variable per-call pricing for LLM/API endpoints), and **`specs/schemes/exact/scheme_exact_algo.md`** — the Algorand exact scheme contributed by GoPlausible and merged via PR #361, making Algorand a first-class, upstream-supported network.

The V2 wire format uses three headers: `PAYMENT-REQUIRED` is the server's 402 response header carrying a base64 `PaymentRequired` object (replacing V1's body-only response), `PAYMENT-SIGNATURE` is the client's request header carrying a base64 `PaymentPayload`, and `PAYMENT-RESPONSE` is the server's 200 response header carrying a base64 Settlement Response. V1 used `X-PAYMENT` and `X-PAYMENT-RESPONSE` and many third-party tutorials still show those names; both Coinbase and GoPlausible packages support both for back-compat. Network IDs are CAIP-2: `eip155:8453` for Base mainnet, `eip155:84532` for Base Sepolia, `algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=` for Algorand mainnet, `algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=` for Algorand testnet, plus the standard `solana:` prefixes. The 12-step flow runs: client GETs the resource, server returns 402 with `PAYMENT-REQUIRED`, client picks a `PaymentRequirements` and builds a signed `PaymentPayload`, retries with `PAYMENT-SIGNATURE`, server forwards to facilitator's `POST /verify`, on success either fulfills locally or invokes `POST /settle`, then returns 200 with `PAYMENT-RESPONSE`. The facilitator never holds funds — it only verifies signatures and broadcasts pre-signed transactions. The two EVM transfer methods are EIP-3009 `transferWithAuthorization` for compliant tokens (USDC, EURC) which is fully gasless via facilitator submission, and Permit2 (Uniswap address `0x000000000022D473030F116dDEE9F6B43aC78BA3`) plus x402's vanity proxies `0x4020615294c913F045dc10f0a5cdEbd86c280001` (exact) and `0x4020633461b2895a48930Ff97eE8fCdE8E520002` (upto) as the universal ERC-20 fallback.

Install reference SDKs with `npm install @x402/core @x402/evm @x402/svm @x402/axios @x402/fetch @x402/express @x402/hono @x402/next @x402/paywall @x402/extensions` for TypeScript, `pip install x402` for Python, and `go get github.com/coinbase/x402/go` for Go. The Python module map is `x402.server` (`x402ResourceServer`, `x402ResourceServerSync`), `x402.http` (`HTTPFacilitatorClient`, `FacilitatorConfig`, `PaymentOption`), `x402.http.middleware.fastapi` (`PaymentMiddlewareASGI`, `payment_middleware_from_config`, `FastAPIAdapter`), `x402.http.middleware.flask` (`PaymentMiddleware` WSGI, `FlaskAdapter`), `x402.http.clients.httpx` (`x402HttpxClient`, `wrapHttpxWithPayment`, `x402AsyncTransport`), `x402.http.clients.requests` (`x402HTTPAdapter`), `x402.mechanisms.evm.exact` (`ExactEvmServerScheme`, `ExactEvmClientScheme`), and `x402.extensions.bazaar` for resource discovery.

A minimal FastAPI EVM resource server reads:

```python
from fastapi import FastAPI
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

app = FastAPI()
facilitator = HTTPFacilitatorClient(FacilitatorConfig(url="https://x402.org/facilitator"))
server = x402ResourceServer(facilitator)
server.register("eip155:84532", ExactEvmServerScheme())
routes: dict[str, RouteConfig] = {
    "GET /weather": RouteConfig(
        accepts=[PaymentOption(scheme="exact", pay_to="0xYourAddress",
                               price="$0.001", network="eip155:84532")],
        mime_type="application/json",
    ),
}
app.add_middleware(PaymentMiddlewareASGI, server=server, routes=routes)
```

The available facilitators are `https://x402.org/facilitator` (signup-free public, recommended for testnet), the **CDP (Coinbase Developer Platform)** facilitator at `https://api.developer.coinbase.com/x402/v2/facilitator` (production, 1,000 tx/month free, multi-network), Cloudflare's edge facilitator (deferred settlement, Workers-native), GoPlausible's Algorand facilitator at `https://facilitator.x402.goplausible.xyz`, and community options including Sperax, PayAI, thirdweb x402, and the production-grade Rust `x402-rs`. **No first-class PHP package exists** in `coinbase/x402` — only TypeScript, Python, Go, and Java. Searches for `"x402 php"`, `"x402-php"`, `composer x402`, GitHub topic `x402` and `x402protocol`, plus the `Merit-Systems/awesome-x402` and `xpaysh/awesome-x402` curated lists yield Ruby (`x402-rails`, QuickNode `x402-payments`), TypeScript, Python, Go, and Rust (`x402-rs`) implementations but no PHP. If the user has built a PHP port it appears unique; the simplest reference is the Python `x402` package since header parsing translates 1:1 (base64-decode `PAYMENT-SIGNATURE` → JSON → forward to facilitator `POST /verify`).

## GoPlausible x402-avm — the Algorand x402 reference

The Algorand x402 implementation lives at `https://github.com/GoPlausible/x402-avm` on branch `branch-algorand-v2`, Apache-2.0, forked from `coinbase/x402` so the file tree mirrors it. Clone with `git clone -b branch-algorand-v2 https://github.com/GoPlausible/x402-avm.git`; the Go module path is `go get github.com/GoPlausible/x402-avm/go@v0.5.1`. The npm scope is `@x402-avm/*` (current version 2.6.1 as of April 2026): `@x402-avm/core` (transport-agnostic client/server/facilitator), `@x402-avm/avm` (Algorand mechanism — signers, constants, exact scheme), `@x402-avm/evm`, `@x402-avm/svm`, `@x402-avm/axios`, `@x402-avm/fetch`, `@x402-avm/express`, `@x402-avm/hono` (Cloudflare Workers compatible), `@x402-avm/next`, `@x402-avm/paywall` (browser HTML generator wired to Pera/Defly/Lute via `@txnlab/use-wallet`), and `@x402-avm/extensions` (Bazaar discovery + Sign-in-with-X CAIP-122). The PyPI distribution name is **`x402-avm`** but the Python import name is **`x402`** (not `x402_avm`); install with `pip install "x402-avm[avm,fastapi]"`, `pip install "x402-avm[avm,flask]"`, `pip install "x402-avm[avm,httpx]"`, or `pip install "x402-avm[all]"`. A breaking change in v2.6+ removed `algosdk` as a direct dependency in favor of `@algorandfoundation/algokit-utils@10.0.0-alpha.39`.

The Algorand variant has a critical architectural property: **there are no PyTeal or TEAL smart contracts.** The mechanism uses **native ASAs (Algorand Standard Assets) plus atomic transaction groups** with optional LogicSig fee abstraction — no on-chain contract deploys, no upgradeable proxy logic, and the facilitator has zero ability to redirect funds because the signature scheme and `arcv` (asset receiver) field bind to `payTo`. This aligns precisely with the cypherpunk2048 standard the user enumerated (no admin keys, no upgradeable proxies). A canonical Algorand `paymentRequirements` block looks like:

```json
{
  "scheme": "exact",
  "network": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
  "amount": "5000000",
  "payTo": "RESOURCESERVERADDRESSAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALTSRPAE",
  "maxTimeoutSeconds": 60,
  "asset": "31566704",
  "extra": { "feePayer": "FACILITATORADDRESSAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALQCXBZE" }
}
```

The `asset` field is a stringified ASA ID (uint64), not an EVM contract address; USDC mainnet ASA is `31566704` and testnet ASA is `10458941`, both with 6 decimals. The optional `extra.feePayer` instructs the client to construct a 0-Algo `pay` transaction from the facilitator address with sufficient pooled fee, making the client's payment gasless by group economics. The matching `PAYMENT-SIGNATURE` payload contains a `paymentGroup` (up to 16 base64-msgpack-encoded transactions) and a `paymentIndex` pointing at the asset transfer the client signs; signature schemes accepted are Ed25519 single sig, k-of-n multisig, and LogicSig. Verification runs eight checks: `x402Version == 2`, `scheme == "exact"`, network match, `paymentGroup.length <= 16`, decoding succeeds, the txn at `paymentIndex` has `aamt == amount`, `arcv == payTo`, `xaid == asset`; for facilitator-sender txns `type == "pay"` with no `close`, `rekey`, or `amt` fields and a sane fee; and finally the entire group is dry-run through Algod's `simulate` endpoint before settlement via `v2/transactions`.

The TypeScript client signer interface is:

```ts
interface ClientAvmSigner {
  address: string;
  signTransactions(txns: Uint8Array[], indexesToSign?: number[]): Promise<(Uint8Array | null)[]>;
}
```

with a wallet-derived browser path that delegates to `wallet.features["algorand:signTransaction"].signTransaction({ txns, indexesToSign })`. The Python equivalent is a `Protocol` class `ClientAvmSigner` with `address: str` and `sign_transactions(unsigned_txns: list[bytes], indexes_to_sign: list[int]) -> list[bytes | None]`. The facilitator-side signer (`FacilitatorAvmSigner`) exposes `getAddresses`, `signTransaction`, `getAlgodClient`, `simulateTransactions`, `sendTransactions`, and `waitForConfirmation` — and a complete FastAPI facilitator implementation appears in `GoPlausible/.github/profile/algorand-x402-documentation/python/`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from x402 import x402Facilitator
from x402.mechanisms.avm.exact import register_exact_avm_facilitator
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2
from x402.mechanisms.avm.constants import NETWORK_CONFIGS
from algosdk import encoding, transaction
from algosdk.v2client import algod
import os, base64

app = FastAPI(title="x402-avm Facilitator Service")
SECRET_KEY  = base64.b64decode(os.environ["AVM_PRIVATE_KEY"])
ADDRESS     = encoding.encode_address(SECRET_KEY[32:])
SIGNING_KEY = base64.b64encode(SECRET_KEY).decode()

class FacilitatorSigner:
    def __init__(self): self._clients = {}
    def _client(self, network):
        if network not in self._clients:
            cfg = NETWORK_CONFIGS.get(network, {})
            url = cfg.get("algod_url", "https://testnet-api.algonode.cloud")
            self._clients[network] = algod.AlgodClient("", url)
        return self._clients[network]
    def get_addresses(self): return [ADDRESS]
    def sign_transaction(self, txn_bytes, fee_payer, network):
        b64 = base64.b64encode(txn_bytes).decode()
        txn_obj = encoding.msgpack_decode(b64)
        signed  = txn_obj.sign(SIGNING_KEY)
        return base64.b64decode(encoding.msgpack_encode(signed))
    def send_group(self, group_bytes, network):
        return self._client(network).send_raw_transaction(b''.join(group_bytes))

facilitator = x402Facilitator()
register_exact_avm_facilitator(facilitator, signer=FacilitatorSigner(),
                               networks=[ALGORAND_TESTNET_CAIP2])

@app.post("/verify")
async def verify(req: Request):
    body = await req.json()
    return JSONResponse(await facilitator.verify(body["paymentPayload"], body["paymentRequirements"]))

@app.post("/settle")
async def settle(req: Request):
    body = await req.json()
    return JSONResponse(await facilitator.settle(body["paymentPayload"], body["paymentRequirements"]))
```

A TypeScript Hono facilitator equivalent registers `registerExactAvmScheme(facilitator, { signer: toFacilitatorAvmSigner(process.env.AVM_PRIVATE_KEY!, { testnetUrl: "https://testnet-api.algonode.cloud" }), networks: ALGORAND_TESTNET_CAIP2 })`. The constants module exports `ALGORAND_MAINNET_CAIP2`, `ALGORAND_TESTNET_CAIP2`, `USDC_MAINNET_ASA_ID = 31566704`, `USDC_TESTNET_ASA_ID = 10458941`, `DEFAULT_DECIMALS = 6`, and the V1 alias map `V1_NETWORKS = ["algorand-mainnet", "algorand-testnet"]`. Adjacent GoPlausible repos worth pulling for a complete deployment are `x402-agents-add` (agent additions fork), `openclaw-algorand-plugin` (OpenClaw agent plugin embedding x402 skills/tools), `claude-algorand-plugin` (Claude Code plugin with embedded MCP + x402), and `falcon-signatures-js` (post-quantum NTRU lattice signatures used in dAoAuth, npm `falcon-signatures`).

## A2A — Linux Foundation Agent2Agent protocol stack

A2A was donated by Google to the **Linux Foundation (LF AI & Data)** on **June 23, 2025** at Open Source Summit North America (Denver), with founding members AWS, Cisco, Google, Microsoft, Salesforce, SAP, and ServiceNow. IBM's ACP (Agent Communication Protocol) was merged into A2A in **August 2025**, and >150 organizations now back the spec. The canonical org is `https://github.com/a2aproject` (legacy `github.com/google/A2A` and `github.com/google-a2a` redirect here). The spec lives at `https://a2a-protocol.org/latest/specification/` and mirrors in `a2aproject/A2A/specification/grpc/a2a.proto` (canonical Protobuf) plus markdown topics under `docs/`. License is **Apache 2.0** across every official repo, and the wire protocol is **JSON-RPC 2.0 over HTTPS** with optional gRPC and HTTP+JSON/REST transports; production deployments **must** use TLS 1.3+. JSON serializations use camelCase even though the proto uses snake_case.

The clone matrix is `git clone https://github.com/a2aproject/A2A.git` for spec and protos, `git clone https://github.com/a2aproject/a2a-python.git` for the official Python SDK (PyPI `a2a-sdk`, currently v1.0.2 released April 24 2026), `git clone https://github.com/a2aproject/a2a-js.git` for the official TypeScript SDK (npm `@a2a-js/sdk`, ~1M weekly downloads, 0.3.x line implementing spec v0.3.0 with v1.0 in progress), `git clone https://github.com/a2aproject/a2a-java.git` (Maven `io.github.a2asdk`), `git clone https://github.com/a2aproject/a2a-go.git`, `git clone https://github.com/a2aproject/a2a-dotnet.git` (NuGet `A2A`), `git clone https://github.com/a2aproject/a2a-rs.git` (Rust), `git clone https://github.com/a2aproject/a2a-samples.git`, `git clone https://github.com/a2aproject/a2a-inspector.git` (FastAPI + TS validator UI), and `git clone https://github.com/a2aproject/a2a-tck.git` (Test Compatibility Kit). Install Python with `pip install a2a-sdk` plus optional extras `[sql]`, `[grpc]`, `[http-server]`, `[telemetry,encryption,signing,postgresql,mysql,sqlite,all]`; requires Python 3.10+. Install TypeScript with `npm install @a2a-js/sdk express` (Express is a peer dep for `@a2a-js/sdk/server/express`), and add `@grpc/grpc-js @grpc/proto-loader` for gRPC transport.

A2A v1.0 introduced a breaking change critical for AgenticPlace's design: the `A2AStarletteApplication`, `A2AFastApiApplication`, and `A2ARESTFastApiApplication` wrapper classes were removed and replaced with **route factory functions** — `create_jsonrpc_routes()`, `create_rest_routes()`, `create_agent_card_routes()` — composed directly into Starlette/FastAPI apps. A v0.3 compatibility flag `enable_v0_3_compat=True` is available on the route factories. Wrapper Part types (`TextPart`, `FilePart`, `DataPart`) collapsed into a unified `Part` whose content fields are direct properties; `Part.DataPart.data` is now `Part.data` typed as `google.protobuf.Value`. Streaming `AgentExecutor` implementations **must** follow exactly one pattern: either a message-only stream (one `Message`, then stop) or a task-lifecycle stream (`Task` first, then `TaskStatusUpdateEvent`/`TaskArtifactUpdateEvent` until terminal); mixing raises `InvalidAgentResponseError`. Task states split into non-terminal (`submitted`, `working`, `input-required`, `auth-required`) and terminal (`completed`, `canceled`, `rejected`, `failed`); once terminal, a task **cannot restart** — refinements must open a new task within the same `contextId`. The four ID types are `messageId` (per-message UUID), `taskId` (server-assigned stateful unit), `contextId` (groups multi-turn conversation), and `referenceTaskIds` (links back to prior tasks).

A reference Python helloworld agent server (v0.x style still common in samples) is:

```python
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
import uvicorn

class HelloAgent:
    async def invoke(self): return 'Hello World'

class HelloExecutor(AgentExecutor):
    def __init__(self): self.agent = HelloAgent()
    async def execute(self, ctx: RequestContext, q: EventQueue):
        await q.enqueue_event(new_agent_text_message(await self.agent.invoke()))
    async def cancel(self, ctx, q): raise Exception('cancel not supported')

card = AgentCard(
    name='Hello World Agent', description='Just a hello world agent',
    url='http://localhost:9999/', version='1.0.0',
    default_input_modes=['text'], default_output_modes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    skills=[AgentSkill(id='hello_world', name='Returns hello world',
                       description='just returns hello world',
                       tags=['hello world'], examples=['hi','hello world'])],
)
handler = DefaultRequestHandler(agent_executor=HelloExecutor(),
                                task_store=InMemoryTaskStore())
server = A2AStarletteApplication(agent_card=card, http_handler=handler)
uvicorn.run(server.build(), host='0.0.0.0', port=9999)
```

The Agent Card lives at `GET /.well-known/agent-card.json` (v1.0; legacy v0.x used `/.well-known/agent.json`), must be served without authentication, and an authenticated extended card may be served at `GET /agent/authenticatedExtendedCard` behind Bearer auth. A canonical card declares `name`, `description`, `url`, `version`, `protocolVersion`, `provider` (org + url), `documentationUrl`, `capabilities` (`streaming`, `pushNotifications`, `stateTransitionHistory`), `defaultInputModes`/`defaultOutputModes`, a `skills[]` array (each with id/name/description/tags/examples/inputModes/outputModes), `securitySchemes` aligned with OpenAPI (Bearer, OAuth2, OIDC, API key, Basic), `security[]`, `additionalInterfaces[]` (transport variants `JSONRPC`, `HTTP+JSON`, `GRPC`), `preferredTransport`, `supportsAuthenticatedExtendedCard`, and an optional `extensions[]` URI list which clients opt into via the `X-A2A-Extensions` request header. The core JSON-RPC methods are `message/send`, `message/stream` (SSE), `tasks/get`, `tasks/cancel`, `tasks/resubscribe`, and `tasks/pushNotificationConfig/{set,get,list,delete}`. Push notifications post task updates to a webhook URL the client registers, and v1.0 added support for multiple push configs per task with new `push_notification_sender`/`push_notification_config_store` interfaces.

## MCP — specification, SDKs, FastMCP, and OAuth 2.1

The canonical MCP repo is `https://github.com/modelcontextprotocol/modelcontextprotocol` (the historical `modelcontextprotocol/specification` was consolidated here); the public spec is hosted at `https://modelcontextprotocol.io/specification/latest`. Spec versions are date-stamped: `2024-11-05` (initial), `2025-03-26` (Streamable HTTP transport added; SSE deprecated), **`2025-06-18`** (major auth overhaul reclassifying MCP servers as **OAuth 2.1 Resource Servers**, mandating RFC 9728 Protected Resource Metadata and RFC 8707 Resource Indicators, adding `outputSchema` for structured tool output and elicitation), and **`2025-11-25`** (current as of May 2026, refining authorization with optional Dynamic Client Registration, Step-Up Authorization Flow, Scope Selection, Sampling-with-Tools per SEP-1577, URL-mode elicitation per SEP-1036, tool-name validation per SEP-986, and JSON Schema 2020-12 field preservation). The schema is TypeScript-first at `schema/2025-11-25/schema.ts`; JSON Schema is generated. MCP was donated to the Linux Foundation in late 2025 (the AI Agent Interoperability Foundation, AAIF) in a Dec 9 2025 announcement reporting 10,000+ public servers, 75+ Claude connectors, and 97M monthly SDK downloads. MCP and A2A are governed under the same AAIF with an Interop Working Group bridging the specs; the consensus separation is **MCP = vertical (one agent ↔ tools/data), A2A = horizontal (agent ↔ agent)**, with the AP2/x402 stack layering payments orthogonally.

The Python SDK is at `https://github.com/modelcontextprotocol/python-sdk` (~22.3k stars), PyPI `mcp`, install with `pip install "mcp[cli]"` or `uv add "mcp[cli]"`; latest v1.26.0 (January 2026) on the `v1.x` branch with v2 in pre-alpha on `main`; license is MIT for existing code and Apache-2.0 for new contributions. **FastMCP 1.0** is built into this SDK as `mcp.server.fastmcp.FastMCP`. The standalone successor **FastMCP 2.0** by Jeremiah Lowin (Prefect) lives at `https://github.com/jlowin/fastmcp` (also branded `PrefectHQ/fastmcp` on some pages), PyPI `fastmcp`, `pip install fastmcp`. FastMCP 2.0 adds a client library, server proxying and composition, OpenAPI/FastAPI integration, middleware, transforms, tool search, Code Mode (3.1 release), and Prefab Apps integration; the v2 decorator syntax drops parens (`@mcp.tool` not `@mcp.tool()`). The TypeScript SDK is `https://github.com/modelcontextprotocol/typescript-sdk` (~12.3k stars), npm `@modelcontextprotocol/sdk`, install with `npm install @modelcontextprotocol/sdk zod`. The v2 split packages are `@modelcontextprotocol/server`, `@modelcontextprotocol/client`, with framework adapters `@modelcontextprotocol/node`, `@modelcontextprotocol/express`, and `@modelcontextprotocol/hono`. Reference servers live at `https://github.com/modelcontextprotocol/servers` and a hosted demo "Everything" server runs at `https://example-server.modelcontextprotocol.io/mcp`.

A minimal Python MCP server with FastMCP 1.0 reads:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("AgenticPlace Listing", json_response=True)

@mcp.tool()
def list_agents(skill_tag: str) -> list[dict]:
    """Search marketplace agents by skill tag."""
    return query_registry(skill_tag)

@mcp.resource("agentcard://{agent_id}")
def get_agent_card(agent_id: str) -> str:
    return fetch_agent_card_json(agent_id)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

The TypeScript equivalent uses `McpServer` from `@modelcontextprotocol/sdk/server/mcp.js` with `registerTool` and `StdioServerTransport` (or HTTP transport via `@modelcontextprotocol/express`). The MCP primitives split into **prompts** (user-controlled, slash commands), **resources** (app-controlled, GET-like data), and **tools** (model-controlled, POST-like side-effects), declared via Server Capabilities `prompts.listChanged`, `resources.subscribe/listChanged`, `tools.listChanged`, `logging`, `completions`. The 2025-06-18+ OAuth 2.1 flow returns `401 Unauthorized` with `WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource"`; the client fetches that metadata, then the AS metadata at `/.well-known/oauth-authorization-server` (RFC 8414), runs OAuth 2.1 with PKCE while passing the `resource` parameter (RFC 8707) bound to the MCP server URL, and presents `Authorization: Bearer <token>` with audience/scope/expiry validated locally. Critically, MCP servers **must not** pass user tokens to upstream APIs (confused deputy attack mitigated post-Sept 2025) — they must obtain separate tokens as OAuth clients to upstream. AgenticPlace's MCP exposure should configure `FastMCP` with `token_verifier=` and `auth=AuthSettings(issuer_url=..., resource_server_url=..., required_scopes=[...])`.

MCP↔A2A bridges that matter for AgenticPlace are `https://github.com/GongRzhe/A2A-MCP-Server` (PyPI `a2a-mcp-server`, run `uvx a2a-mcp-server` for stdio or `MCP_TRANSPORT=streamable-http MCP_PORT=8000 uvx a2a-mcp-server` for HTTP, exposing A2A operations `register_agent`, `send_message`, `send_message_stream`, `get_task_result` as MCP tools), `https://github.com/regismesquita/MCP_A2A` (lightweight Python bridge for Claude Desktop), `https://github.com/yw0nam/MCP-A2A-Gateway` (PyPI `mcp-a2a-gateway`, `uvx mcp-a2a-gateway`, with full register/unregister/stream/cancel/track), `https://github.com/themanojdesai/python-a2a` (Python lib with first-class MCP v2.0 baked in), and IBM ContextForge at `https://ibm.github.io/mcp-context-forge/using/agents/a2a/` (set `MCPGATEWAY_A2A_ENABLED=true`, POST `/a2a` to register A2A agents — they appear as MCP tools). Google ADK ships `google.adk.to_a2a()` to wrap an ADK agent as an A2A-exposed `uvicorn` server with auto-generated Agent Card.

## A2P — definitively Agent-to-Payment, which is Google AP2

The "A2P" reference in AgenticPlace's context is **Agent-to-Payment**, which Google brands as **AP2 (Agent Payments Protocol)**. The naming has fluctuated across press and dev posts as "A2P", "AP2", "Agent2Payment", and "Agents-to-Payments"; outlets like fintechbrainfood.com and the AWS/Coinbase ecosystem use "A2P" while Google's canonical brand is AP2. The traditional telecom "Application-to-Person" SMS meaning (Sinch, Twilio) is unrelated to agentic commerce and not applicable here. AP2 was announced **September 16, 2025** with 60+ partners including Coinbase, PayPal, Mastercard, American Express, Adyen, Etsy, Salesforce, ServiceNow, Worldpay, JCB, UnionPay, Mysten Labs, Intuit, Forter, and Revolut, and was donated to the FIDO Alliance per the blog.google announcement. The reference repo is `https://github.com/google-agentic-commerce/AP2` (Apache-2.0), spec sites at `https://ap2-protocol.org/` and `https://ap2-protocol.net/en/`, latest release v0.2.0 in April 2026 introducing "Human Not Present" autonomous payments. Clone with `git clone https://github.com/google-agentic-commerce/AP2.git`. The codebase is Python-majority with reference implementations in TypeScript, Kotlin, and Go.

AP2's architecture is an extension of A2A and MCP built around three cryptographically signed Verifiable Credentials called **Mandates**: an **Intent Mandate** (user signs upfront, e.g., "buy concert tickets ≤ $X"), a **Cart Mandate** (merchant agent signs the concrete cart at price), and a **Payment Mandate** (credentials provider signs the actual payment authorization). Crypto primitives are ECDSA P-256 plus SHA-256, threat-modeled with STRIDE/MAESTRO per the Cloud Security Alliance October 2025 analysis. The most relevant integration repo for AgenticPlace is `https://github.com/google-agentic-commerce/a2a-x402` — *"The A2A x402 Extension brings cryptocurrency payments to the Agent-to-Agent (A2A) protocol"* — with a functional-core/imperative-shell architecture, Python primary in `python/x402_a2a/` plus a community TypeScript port (`TheCrazyGM/x402-a2a-typescript`), middleware executors automating the payment flow, and a full spec at `spec/`. Production pilots include PayPal's Conversational Commerce Agent (October 27, 2025) and the Mastercard Agent Pay × PayPal pilot which uses AP2 payment mandates with Mastercard's Agent Pay Acceptance Framework. The clean mental model for AgenticPlace is: **MCP** answers "how do agents talk to tools," **A2A** answers "how do agents talk to other agents," **AP2/A2P** answers "did the user authorize this," and **x402** answers "how do funds actually move," with AP2 mandates flowing into x402 facilitator calls flowing into on-chain USDC transfers.

## YouTube transcript — gap statement and probable reference set

The video at `https://youtu.be/cS5RjkW4aoY` could not be retrieved through any of the following 15+ attempted endpoints: direct fetches against `youtu.be/cS5RjkW4aoY`, `www.youtube.com/watch?v=cS5RjkW4aoY`, `www.youtube.com/api/timedtext?v=cS5RjkW4aoY&lang=en`, `youtubetranscript.com/?server_vid2=cS5RjkW4aoY`, `youtubetotranscript.com/transcript?v=cS5RjkW4aoY`, `tactiq.io/tools/youtube-transcript?video=cS5RjkW4aoY`, `kome.ai/tools/youtube-transcript-generator?v=cS5RjkW4aoY`, `notegpt.io/youtube-transcript-generator`, `i.ytimg.com/vi/cS5RjkW4aoY/hqdefault.jpg`, the YouTube Data API endpoint, and the oEmbed endpoint. The web_fetch tool refuses these because the URLs were not surfaced in any prior search result, and Google web searches against the bare ID `"cS5RjkW4aoY"`, the full URL, and the watch URL — including site-restricted queries against reddit.com, dev.to, medium.com, and X/Twitter — return zero hits. The video appears to be unindexed, possibly unlisted, very new, or low-view; no metadata (title, channel, date, description, view count) is available through any accessible source. The user can unblock this either by re-issuing the video URL inline at the start of a follow-up turn (which whitelists it for direct fetch) or by supplying the title and channel for indirect reconstruction.

The **most probable** content of the video, given its topical signature (A2A + A2P + MCP + x402 in a single piece), is from the GoPlausible/Algorand Foundation orbit — the only public footprint that consistently bundles all four protocols. Candidate channels include GoPlausible (@GoPlausible on X, led by `emg110`/MG), the Algorand Foundation YouTube channel (which hosts adjacent videos `FnLy0cdx8FI` "x402 workshop", `tjzz4YS6Bdk` "Agentic Commerce: AP2, x402…", `aFEE9VEKjuM` "x402 Ideathon Berlin", and `f3VBjcwirZo`), Coinbase developer relations, Anthropic dev community uploads, and `AndreaRettaroli/m2m` which has the precise A2A + x402 + MCP + Base demo. The reference set the video almost certainly enumerates — drawn from the canonical four-protocol footprint — is captured in the rest of this dossier: the GoPlausible repos, `coinbase/x402` and `x402-foundation/x402`, the `a2aproject/*` family, `modelcontextprotocol/*`, `jlowin/fastmcp`, `google-agentic-commerce/AP2` and `google-agentic-commerce/a2a-x402`, `GongRzhe/A2A-MCP-Server`, the npm `@x402-avm/*` and `@x402/*` scopes, PyPI `x402-avm`/`x402`/`mcp`/`fastmcp`/`a2a-sdk`, and the standard endpoints `x402.goplausible.xyz`, `facilitator.x402.goplausible.xyz`, `x402.org/facilitator`, `algorand.co/agentic-commerce/x402`, `.well-known/agent-card.json`, `.well-known/x402`, and `.well-known/mcp.json`.

## AllChain mapping — gap statement and reconstructed model

The page at `https://agenticplace.pythai.net/allchain.html` could not be fetched (the same permissions/whitelist issue as the YouTube video) and does not appear in any search engine crawl — no snippet, no archive, no secondary reference. The page is either freshly deployed and not yet indexed, behind a `robots.txt` no-archive directive, or both. Reconstructing from the user's architectural constants (Ethereum mainnet as primary EVM anchor with reduced 2026 gas, Polygon and Base as support layers, Arc/Circle chain ID 5042002 with reserved adapter slots pending mainnet, Algorand for constitutional state, EVM/Polygon for economic state) yields the chain ID and CAIP-2 mapping AgenticPlace's adapter framework should target:

| Chain | Chain ID | CAIP-2 | Role | RPC reference |
|---|---|---|---|---|
| Ethereum mainnet | 1 | `eip155:1` | Primary EVM anchor, ERC-8004 agent identity, BANKON ENS subname registrar | `https://eth.llamarpc.com`, Alchemy, Infura |
| Polygon PoS | 137 | `eip155:137` | Economic state, Polygon Agent CLI tooling | `https://polygon-rpc.com` |
| Base mainnet | 8453 | `eip155:8453` | Coinbase x402 default network, USDC at `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | `https://mainnet.base.org` |
| Base Sepolia | 84532 | `eip155:84532` | x402 testnet default, USDC `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | `https://sepolia.base.org` |
| Arc (Circle) | 5042002 | `eip155:5042002` | Reserved adapter slot, awaiting mainnet | TBD |
| Algorand mainnet | n/a (genesis hash) | `algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=` | Constitutional state, x402-avm settlement, USDC ASA `31566704` | `https://mainnet-api.algonode.cloud` |
| Algorand testnet | n/a | `algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=` | Test, USDC ASA `10458941` | `https://testnet-api.algonode.cloud` |
| MegaETH | 4326 | `eip155:4326` | x402 CDP-supported | per CDP docs |
| Monad | 143 | `eip155:143` | x402 CDP-supported | per CDP docs |
| Solana mainnet | n/a | `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp` | x402 SVM mechanism via SPL Token + Token2022 | per `@x402/svm` |

The user should publish `allchain.html` as a structured JSON descriptor (e.g., `allchain.json`) so AgenticPlace's adapter loader can iterate it programmatically; each row should carry `caip2`, `chainId`, `role` (constitutional/economic/anchor/reserved), `rpcUrl`, `nativeAsset`, `usdcAddress` or `usdcAsaId`, `x402Mechanism` (`evm`/`avm`/`svm`/`stellar`), `x402Facilitator`, and `adapterStatus` (`live`/`reserved`/`deprecated`).

## Foundry scaffolding — what survives the cypherpunk2048 constraint

Because GoPlausible's Algorand path uses zero PyTeal/TEAL contracts (native ASAs and atomic transaction groups only), and the cypherpunk2048 standard forbids upgradeable proxies and admin keys, the **Solidity surface area is intentionally minimal** for AgenticPlace's deployment. The contracts that warrant Foundry-grade testing are: any AgenticPlace ERC-8004 agent identity registry deployed on Ethereum mainnet for global identity anchoring, any BANKON ENS subname registrar contract (CCIP-Read/wildcard resolver pattern), and any Permit2-based x402 vanity proxy if AgenticPlace operates its own (otherwise reuse Coinbase's `0x4020615294c913F045dc10f0a5cdEbd86c280001` for `exact` and `0x4020633461b2895a48930Ff97eE8fCdE8E520002` for `upto`). The standard Foundry workflow — `forge init`, `forge build`, `forge test --match-contract`, `forge script script/Deploy.s.sol --rpc-url $RPC --broadcast --verify` — applies; the cypherpunk2048 constraint forces all factories to be **immutable** with `CREATE2` for deterministic addresses across Ethereum/Polygon/Base, and tests must include `testFuzz_*` invariants asserting no admin role exists (`vm.expectRevert` against any setter) and no upgrade selector is reachable. EIP-3009 paths bypass contract deploys entirely on USDC since `transferWithAuthorization` is built into the token; the only contracts under your control are the agent identity and registrar layers. Verified deployments should be cross-referenced against `coinbase/x402`'s live addresses on Base, Polygon, and the EVM majors before duplicating any logic. No verified Parsec or AgenticPlace Solidity deployments were located in Etherscan/Polygonscan/BaseScan searches — consistent with the Parsec source-code gap.

## AgenticPlace integration architecture — concrete wiring

The deployable architecture for AgenticPlace stitches the four protocols into a layered topology that maps cleanly onto the user's PYTHAI/DELTAVERSE constants. **Layer 1 (constitutional state)** runs on Algorand: each agent listing's persistent identity, mandate history, and audit trail anchors as ASA-tagged transactions or note-field entries on Algorand mainnet, with the agentic wallet itself provisioned through `algorand-remote-mcp-lite` (the "Parsec" surface) — an OAuth+OIDC login through HashiCorp Vault Transit produces a standard 58-character ed25519 account bound to the AgenticPlace user/agent identity, and signing flows through the `ClientAvmSigner` interface either client-side (browser via `@txnlab/use-wallet` against Pera/Defly/Lute) or facilitator-side (Vault holds the private key, OIDC scope authorizes signing). **Layer 2 (economic state)** runs on EVM (Ethereum mainnet, Polygon, Base): ERC-8004 agent identity registries on Ethereum mainnet, BANKON ENS subname issuance for human-readable agent handles, and USDC settlement on Base via x402 EIP-3009 for the default fast-cheap path. **Layer 3 (payment rails)** uses x402 in two parallel modes — `@x402/evm` against Coinbase's CDP facilitator or `https://x402.org/facilitator` for EVM, and `@x402-avm/avm` against `https://facilitator.x402.goplausible.xyz` for Algorand — selected per-resource by the `network` field in `paymentRequirements`. **Layer 4 (authorization)** uses AP2 mandates: every agent transaction in AgenticPlace produces an Intent Mandate signed by the user, a Cart Mandate signed by the merchant agent, and a Payment Mandate signed by the credentials provider, with the resulting signed bundle posted as the body alongside the x402 `PAYMENT-SIGNATURE` header. **Layer 5 (agent communication)** uses A2A: each marketplace listing exposes `GET /.well-known/agent-card.json`, a JSON-RPC 2.0 endpoint at the listing root, and optionally `/agent/authenticatedExtendedCard` behind Bearer auth; AgenticPlace's central registry crawls and validates cards via `a2aproject/a2a-inspector` and `a2aproject/a2a-tck` before approving listings. **Layer 6 (tool exposure)** uses MCP: each agent internally consumes tools (filesystem, GitHub, Postgres, payment, x402 Bazaar discovery) via MCP servers; the marketplace registry itself is exposed as an MCP server through `GongRzhe/A2A-MCP-Server` so that Claude/ChatGPT users can discover and call AgenticPlace agents directly from their host clients.

The mindX cognitive system fits as the orchestrator within an agent (one mindX instance per registered agent, calling MCP tools and emitting A2A messages), while the GATERAGE retrieval engine acts as the agent's memory substrate. The cypherpunk2048 standard is preserved because every on-chain component is immutable, no admin keys are minted, the Solidity surface is minimal, the Algorand path is contractless, documentation stays in terse plain text (this dossier matches that constraint), and module names stay Latin (`x402`, `mcp`, `a2a`, `ap2`, `parsec` itself is Latin-derived). The dual-chain topology operates exactly as specified: Algorand carries constitutional state because its instant finality and contractless ASA flow give zero-rollback audit guarantees, while EVM/Polygon carries economic state because that is where ERC-8004 identity, ENS naming, and Permit2/EIP-3009 USDC liquidity live. Arc's reserved chain ID 5042002 plugs into the AllChain adapter as a third economic rail when Circle launches mainnet, with no architectural change required because every adapter implements the same `(verify, settle, sign)` triple.

## Conclusion — the deployable kernel

The integration is **buildable today** without Parsec ever shipping a public repo, because GoPlausible's `algorand-remote-mcp-lite` plus `x402-avm` plus `coinbase/x402` plus `a2aproject/*` plus `modelcontextprotocol/*` plus `google-agentic-commerce/AP2` plus `google-agentic-commerce/a2a-x402` constitutes the complete substrate. The single highest-leverage action is to **clone the seven repos above, brand `algorand-remote-mcp-lite` as Parsec inside AgenticPlace's UX, and treat its OAuth+Vault flow as the agentic wallet creation primitive** — that is the "Parsec" the user's prior architectural notes describe, whether or not the name ever ships publicly. The two unrecoverable artifacts in this research are the YouTube transcript at `cS5RjkW4aoY` (no service or search engine surfaced it) and the live `agenticplace.pythai.net/allchain.html` page (unindexed); both should be supplied directly in a follow-up turn to whitelist them for fetch. The single most useful technical correction to the user's framing is that the Algorand x402 path is **contractless** — there is no PyTeal factory to write, no Solidity wallet factory on Algorand, only signed atomic transaction groups against native ASAs — which is a significant simplification versus the EVM path and aligns better with cypherpunk2048 than the EVM equivalent does. The PHP x402 implementation the user has built appears genuinely unique in the public ecosystem; publishing it under `agenticplace/x402-php` or `goplausible/x402-php` would fill a documented gap in the canonical x402 language matrix.