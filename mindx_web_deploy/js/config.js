/**
 * mindX Web Deploy — API and deployment config.
 *
 * Public UI: agenticplace.pythai.net (Hostinger or VPS static).
 * Backend API: mindx.pythai.net (VPS only).
 *
 * When the UI is served from agenticplace.pythai.net, API_BASE defaults to
 * https://mindx.pythai.net so the public can interact with the mindX backend
 * without editing this file. Override below for custom setups.
 */
(function () {
  var host = typeof window !== "undefined" && window.location && window.location.hostname ? window.location.hostname.toLowerCase() : "";
  var defaultApiBase = (host === "agenticplace.pythai.net" || host === "www.agenticplace.pythai.net")
    ? "https://mindx.pythai.net"
    : "";

  window.MINDX_WEB_CONFIG = {
    /**
     * Base URL of mindX backend (no trailing slash).
     */
    API_BASE: defaultApiBase,

    /**
     * Optional: force a specific API base (ignore host-based default).
     */
    // API_BASE_OVERRIDE: "https://mindx.pythai.net",

    /**
     * Launcher URLs (filled at runtime if not set).
     * MINDX_APP_URL: full mindX app (default: API_BASE + '/app').
     * DAIO_URL: DAIO voting UI (default: https://daio.pythai.net).
     * BASEGEN_REPO_URL: BaseGen — codebase-to-Markdown CLI (point of departure).
     * TAURI_TEMPLATE_REPO_URL: Tauri v2 workflow template — cross-platform standalone dapps (point of departure).
     */
    MINDX_APP_URL: undefined,
    DAIO_URL: "https://daio.pythai.net",
    BASEGEN_REPO_URL: "https://github.com/Web3dGuy/BaseGen",
    TAURI_TEMPLATE_REPO_URL: "https://github.com/Web3dGuy/tauri-workflow-template",

    /**
     * Persona presets for launcher / environment model UI. Used to filter or highlight launchers.
     * developer | analyst | agenticplace | all
     */
    DEFAULT_PERSONA: "all",
  };

  /* Apply override if set */
  if (window.MINDX_WEB_CONFIG.API_BASE_OVERRIDE !== undefined && window.MINDX_WEB_CONFIG.API_BASE_OVERRIDE !== "") {
    window.MINDX_WEB_CONFIG.API_BASE = window.MINDX_WEB_CONFIG.API_BASE_OVERRIDE;
  }
})();
