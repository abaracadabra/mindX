# mindX Web Deploy — Apache, Hostinger, VPS, Tauri

This folder is a **complete web-based UI** you can deploy to an **Apache** server (e.g. Hostinger shared hosting or a VPS). It talks to the mindX backend via configurable `API_BASE` in `js/config.js`.

---

## What to configure

### On Hostinger (shared hosting)

- You **only** host **static files**: upload this entire folder (e.g. into `public_html` or a subfolder).
- You **cannot** run the mindX backend (Python/uvicorn) or long-running processes on shared hosting.
- **Configure:** In `js/config.js`, set `API_BASE` to the **full URL** of your mindX backend, e.g.:
  - `https://your-vps-ip-or-domain:8000`  
  - or `https://api.yourdomain.com`  
  if the backend runs on a VPS or another server.
- Apache: usually already set up. If you use `.htaccess`, ensure `AllowOverride All` for this directory (Hostinger often allows this in the panel).

### On a VPS (in two days)

- You **can** run the mindX backend and custom services and execute commands.
- **Option A — Backend and UI on same VPS**
  1. Run mindX backend:  
     `./mindX.sh` or  
     `uvicorn mindx_backend_service.main_service:app --host 0.0.0.0 --port 8000`
  2. Serve this UI with Apache (or Nginx):
     - **Apache:** copy this folder into the document root (e.g. `/var/www/html/mindx`). In `js/config.js` you can set `API_BASE: ""` if you proxy `/api` to `http://127.0.0.1:8000`, or set `API_BASE: "http://localhost:8000"` for same-origin testing.
     - **Nginx:** serve the folder as static files and add a `location /api/` (or similar) proxy to `http://127.0.0.1:8000`.
  3. Open firewall for 80/443 (and 8000 only if you want direct API access).
- **Option B — UI on Hostinger, backend on VPS**  
  Upload this folder to Hostinger. Set `API_BASE` in `js/config.js` to your VPS backend URL. Ensure the mindX backend allows CORS from your Hostinger domain (mindX FastAPI app already uses CORS middleware; adjust origins if needed).

---

## Can I deploy a “Tauri UI” on my Hostinger account?

- **Tauri** builds **desktop applications** (installable .exe / .app / Linux binaries). They are **not** “deployed” like a website.
- **On Hostinger you can:**
  - Host this **web** UI (the HTML/JS/CSS in this folder) so users open it in a browser.
  - Optionally host a **download page** or **auto-update** files for your Tauri app; the app itself runs on the user’s machine.
- **Tauri + Web3D:** Use Tauri as the desktop shell and load this UI (or a dedicated Web3D page) inside its webview. The “Web3D” tab here is a placeholder; replace it with Three.js/Babylon or your 3D stack. Tauri delivers that experience as a **desktop app**; the same assets can be served from Apache for browser use.

---

## Summary

| Where        | What you configure |
|-------------|--------------------|
| **Hostinger** | Upload this folder; set `API_BASE` in `js/config.js` to your backend URL (e.g. VPS). Static only. |
| **VPS**       | Run mindX backend + Apache (or Nginx); put this folder in docroot; set `API_BASE` to backend URL or `""` if proxied. |
| **Tauri**     | Build desktop app; use this UI (or Web3D page) inside webview. Host the same static files on Apache for browser access if desired. |

You’ll need help with VPS setup later; this doc is the reference for what to configure where.
