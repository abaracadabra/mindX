/**
 * mindX Web Deploy — API and deployment config.
 * On Hostinger: set API_BASE to your mindX backend URL (e.g. on a VPS).
 * On VPS: set API_BASE to same origin or your backend URL.
 */
(function () {
  window.MINDX_WEB_CONFIG = {
    // Base URL of mindX backend (no trailing slash). Use "" for same-origin when UI is served behind same Apache proxy.
    API_BASE: "",
    // Optional: override for CORS / different host (e.g. "https://api.yourdomain.com")
    // API_BASE: "https://your-vps-ip:8000",
  };
})();
