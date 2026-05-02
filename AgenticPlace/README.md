<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# AgenticPlace // PYTHAI Mastermind

Multi-CEO orchestration UI and frontend for the mindX ecosystem. Run and deploy locally or as part of mindX.

View your app in AI Studio: https://ai.studio/apps/drive/1fGQO5iWNdVnlY-qiAcvWV5mMyQ_ncMxa

## mindX integration

AgenticPlace connects to the mindX backend (default `http://localhost:8000`). Configure via `VITE_MINDX_API_URL` in `.env.local` if the backend runs elsewhere.

- **API reference:** When the mindX backend is running, **http://localhost:8000/docs** (FastAPI Swagger UI) shows all API endpoints and lets you try requests—use it to explore AgenticPlace-related routes under the **AgenticPlace** tag (`/agenticplace/agent/call`, `/agenticplace/ollama/ingest`, `/agenticplace/ceo/status`, etc.).
- **Deep dive:** See [docs/AgenticPlace_Deep_Dive.md](../docs/AgenticPlace_Deep_Dive.md) in the mindX repo for architecture and agent ecosystem.

### Need USDC to call paid agents?

Paid AgenticPlace actions (`/p2p/agent/register`, `/p2p/job/create`) settle in USDC on Arc testnet via Circle Gateway. If your wallet is empty, hit `GET /p2p/onramp/providers` for the cheapest no-KYC route, then `POST /p2p/onramp/and-deposit` to receive the on-ramp instruction *and* the prepared EIP-3009 typed-data — sign once funds land on Arc, submit, and paid routes unlock. Default sources are CCTP (USDC from Ethereum / Base / Arbitrum / Polygon / Optimism / Avalanche, ~$0.003 + 30 bps) and a DEX path (native gas → USDC + CCTP). Configure with `PAY2PLAY_ONRAMP_URL`. See `pay2play/docs/onramp.md` for the full ladder.

## Run Locally

**Prerequisites:** Node.js

1. Install dependencies:
   `npm install`
2. Set `GEMINI_API_KEY` in [.env.local](.env.local) (and optionally `VITE_MINDX_API_URL` if mindX backend is not on localhost:8000).
3. Run the app:
   `npm run dev`
