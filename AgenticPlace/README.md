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

## Run Locally

**Prerequisites:** Node.js

1. Install dependencies:
   `npm install`
2. Set `GEMINI_API_KEY` in [.env.local](.env.local) (and optionally `VITE_MINDX_API_URL` if mindX backend is not on localhost:8000).
3. Run the app:
   `npm run dev`
