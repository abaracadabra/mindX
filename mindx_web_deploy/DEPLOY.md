# mindX Web Deploy — Hostinger, VPS, Public UI

This folder is a **complete web-based UI** for public consumption and agentic interaction. Deploy to **Apache** (e.g. Hostinger) or any static host. The UI talks to the mindX backend via configurable `API_BASE` in `js/config.js`.

**Recommended setup for your domains:**

- **agenticplace.pythai.net** — Public UI (this folder) on Hostinger or VPS.
- **mindx.pythai.net** — mindX backend (API) on a VPS. The UI calls this for health, bankon, agents, and full API.

---

## Quick reference

| Role        | Domain / URL              | Where it runs        | What to do |
|------------|----------------------------|----------------------|------------|
| **Public UI** | agenticplace.pythai.net   | Hostinger (static) or VPS | Upload this folder; set `API_BASE` to mindX backend URL. |
| **Backend API** | mindx.pythai.net          | VPS only             | Run mindX backend (uvicorn); expose 80/443 (and optionally 8000). |

---

## 1. Deploying the UI to Hostinger (agenticplace.pythai.net)

Use Hostinger for **static files only**. The backend must run elsewhere (e.g. VPS).

### 1.1 Upload files

1. In Hostinger **File Manager** (or FTP), go to the document root for **agenticplace.pythai.net** (e.g. `public_html` or the domain’s folder).
2. Upload the **entire** `mindx_web_deploy` folder contents so that:
   - `index.html` is at the site root (or in a subfolder you will use as the root).
   - `js/`, `css/` and any other assets are in the same relative structure.

### 1.2 Point the UI to the mindX backend

1. Open **`js/config.js`** in the Hostinger file editor (or edit locally and re-upload).
2. Set `API_BASE` to your **mindX backend URL** (no trailing slash), for example:
   - `https://mindx.pythai.net` — if the backend is behind Nginx/Apache on mindx.pythai.net (port 443).
   - `https://mindx.pythai.net:8000` — if you expose the backend on port 8000 with SSL.
3. Save and ensure the file is uploaded.

### 1.3 Apache / .htaccess (if needed)

- Hostinger usually has Apache with `AllowOverride All` for the domain.
- This folder includes an **`.htaccess`** for:
  - `DirectoryIndex index.html`
  - Disabling directory listing
  - Optional cache and security headers
- If your panel uses Nginx instead of Apache, `.htaccess` is ignored; configure equivalent rules in the panel or Nginx config.

### 1.4 DNS for agenticplace.pythai.net

- In Hostinger (or your DNS provider), add an **A** (or **CNAME**) record so **agenticplace.pythai.net** points to the Hostinger server IP (or the assigned hosting).
- Enable **SSL** (Let’s Encrypt) in the Hostinger panel for agenticplace.pythai.net so the UI is served over HTTPS.

---

## 2. Running the backend on a VPS (mindx.pythai.net)

The mindX backend (Python/uvicorn) and any long-running services **must** run on a **VPS** (or a server where you can execute custom commands).

### 2.1 Run the mindX backend

```bash
# From the mindX project root
./mindX.sh --backend-port 8000
# or
uvicorn mindx_backend_service.main_service:app --host 0.0.0.0 --port 8000
```

- Use **0.0.0.0** so the server is reachable from the internet (e.g. from agenticplace.pythai.net).

### 2.2 Expose mindx.pythai.net (reverse proxy recommended)

- **Option A — Reverse proxy (recommended)**  
  - Point **mindx.pythai.net** to your VPS IP with an A record.  
  - On the VPS, run Nginx (or Apache) and proxy `https://mindx.pythai.net` to `http://127.0.0.1:8000`.  
  - Then in the UI’s `config.js` use:  
    `API_BASE: "https://mindx.pythai.net"`  
  - No need to open port 8000 publicly; only 80/443.

- **Option B — Direct port**  
  - Open port **8000** in the firewall and (optionally) put the backend behind SSL (e.g. Nginx terminating SSL and proxying to 8000).  
  - Then: `API_BASE: "https://mindx.pythai.net:8000"` or your chosen URL.

### 2.3 CORS

- The mindX FastAPI app uses `allow_origins=["*"]`, so requests from **agenticplace.pythai.net** to **mindx.pythai.net** are allowed.
- For production you can restrict to your UI origin in `main_service.py` (e.g. `allow_origins=["https://agenticplace.pythai.net"]`).

### 2.4 Live VPS checklist

- [ ] mindX backend running (uvicorn, 0.0.0.0:8000 or behind proxy).
- [ ] DNS: **mindx.pythai.net** → VPS IP.
- [ ] SSL for mindx.pythai.net (e.g. Let’s Encrypt via Nginx/Apache or certbot).
- [ ] Firewall: 80, 443 open; 8000 only if you expose it directly.
- [ ] Environment: `.env` (or env vars) with required API keys (see project root `.env.sample`).

---

## 3. UI on the same VPS (optional)

If you serve the **same** UI from the VPS (e.g. at mindx.pythai.net or a path):

1. Copy this folder into the web server document root (e.g. `/var/www/html/agenticplace` or `/var/www/html/mindx/ui`).
2. In **config.js**:
   - If the UI is under the same host as the API and you proxy `/api` to the backend:  
     `API_BASE: ""` and configure the proxy to forward e.g. `/api` → `http://127.0.0.1:8000`.
   - Or set `API_BASE: "https://mindx.pythai.net"` (same host or different).

---

## 4. Domain summary: agenticplace ↔ mindx

- **agenticplace.pythai.net**  
  - **Public-facing UI** for consumption and interaction.  
  - Users open this in a browser; the page loads and calls the mindX API at **mindx.pythai.net** for health, help (bankon), and full API (e.g. `/docs`, agents, directives).  
  - Hosted on **Hostinger** (static) or on the **VPS** (static files only).

- **mindx.pythai.net**  
  - **mindX backend** (FastAPI).  
  - Serves `/health`, `/bankon`, `/docs`, agents, directives, etc.  
  - Must run on a **VPS** (or server with Python/custom services).

The UI’s **config.js** can auto-detect the host: when the site is opened from **agenticplace.pythai.net**, it can default `API_BASE` to **https://mindx.pythai.net** so minimal manual config is needed after upload.

---

## 5. Tauri + Web3D

- **Tauri** builds **desktop** apps (e.g. .exe / .app). They are not “deployed” like a website.
- On **Hostinger** you can host this **web** UI and (optionally) a download/update page for the Tauri app.
- **Tauri + Web3D:** Use Tauri as the desktop shell and load this UI (or a dedicated Web3D page) in its webview. The “Web3D” tab here is a placeholder; replace with Three.js/Babylon or your 3D stack. The same assets can be served from Apache for browser access.

### 5.1 Launchers and persona

This UI acts as a **template launcher**, **self launcher**, and **environment / model UI** driven by preset **personas** (and agents as personas). Tauri dapps are excellent cross-platform standalone web-enabled dapps.

In **`js/config.js`** you can set:

- **`MINDX_APP_URL`** — Full URL to the main mindX app (defaults to `API_BASE + '/app'` if unset).
- **`DAIO_URL`** — DAIO / agentic place URL (e.g. `https://daio.pythai.net`).
- **`BASEGEN_REPO_URL`** — [BaseGen](https://github.com/Web3dGuy/BaseGen) repo; point of departure for codebase → Markdown (AI-ready backups).
- **`TAURI_TEMPLATE_REPO_URL`** — [Tauri workflow template](https://github.com/Web3dGuy/tauri-workflow-template) repo; point of departure for Tauri v2 + React + TypeScript cross-platform dapps.
- **`DEFAULT_PERSONA`** — Initial persona filter: `"all"`, `"developer"`, `"analyst"`, `"agenticplace"`.

The **Launchers** tab shows persona pills and launcher cards (mindX app, login, DAIO, API docs, health, BaseGen, Tauri template, and a **Self launcher** that opens this UI in a new window). The **Interact** tab provides one-click fetch for health, agents, system status, registry tools, and an optional custom request (method + path + body).

---

## 6. Files in this folder

| File / folder   | Purpose |
|-----------------|--------|
| `index.html`    | Main page: Dashboard, Launchers, Interact, Web3D, Help. |
| `js/config.js`  | **API_BASE**, launcher URLs (MINDX_APP_URL, DAIO_URL, BASEGEN_REPO_URL, TAURI_TEMPLATE_REPO_URL), DEFAULT_PERSONA. |
| `js/app.js`     | Health check, launchers, persona filter, fetch buttons, custom request, copy API base, bankon, navigation. |
| `js/web3d-placeholder.js` | Web3D canvas placeholder. |
| `css/site.css`  | Styles for the deployable UI. |
| `.htaccess`     | Apache: DirectoryIndex, no listing, optional headers (Hostinger). |
| `DEPLOY.md`     | This file. |

---

## Summary

- **Hostinger (agenticplace.pythai.net):** Upload this folder, set `API_BASE` in `js/config.js` to `https://mindx.pythai.net` (or your backend URL), configure DNS and SSL.
- **VPS (mindx.pythai.net):** Run mindX backend (uvicorn), put Nginx/Apache in front with SSL, open 80/443.
- **Public consumption:** Users visit **agenticplace.pythai.net** to use the UI and interact with the mindX backend at **mindx.pythai.net**.

For detailed VPS setup (Nginx/Apache configs, systemd, SSL), you can extend this doc or add a separate `VPS_SETUP.md` when you’re ready.
