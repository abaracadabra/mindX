(function () {
  var config = window.MINDX_WEB_CONFIG || { API_BASE: "" };
  var apiBase = (config.API_BASE || "").replace(/\/$/, "");

  function apiUrl(path) {
    return apiBase + (path.startsWith("/") ? path : "/" + path);
  }

  function setBackendStatus(ok, text) {
    var el = document.getElementById("backend-status");
    if (!el) return;
    el.textContent = text || (ok ? "Backend OK" : "Backend unreachable");
    el.classList.toggle("ok", ok);
    el.classList.toggle("fail", !ok);
  }

  function checkHealth() {
    var url = apiUrl("/health");
    if (!url || url === "/health") {
      setBackendStatus(false, "Set API_BASE in js/config.js");
      return;
    }
    fetch(url, { method: "GET", mode: "cors" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(r.statusText)); })
      .then(function () { setBackendStatus(true); })
      .catch(function () { setBackendStatus(false); });
  }

  function wireApiLinks() {
    var base = apiBase || (typeof location !== "undefined" ? location.origin : "");
    var docsUrl = apiUrl("/docs");
    var healthUrl = apiUrl("/health");

    ["api-docs-link", "api-docs-link2", "api-docs-link-interact"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.href = docsUrl;
    });
    var healthEl = document.getElementById("health-link");
    if (healthEl) healthEl.href = healthUrl;

    var originLabel = document.getElementById("api-origin-label");
    var originLink = document.getElementById("api-origin-link");
    if (originLabel) originLabel.textContent = apiBase ? "API" : "API (same origin)";
    if (originLink) {
      originLink.href = base || "#";
      originLink.textContent = apiBase || location.origin || "—";
    }
  }

  function wireLaunchers() {
    var base = apiBase || (typeof location !== "undefined" ? location.origin : "");
    var mindxApp = config.MINDX_APP_URL || (apiBase ? apiBase + "/app" : "");
    var mindxLogin = apiBase ? apiBase + "/login" : "";
    var daioUrl = config.DAIO_URL || "https://daio.pythai.net";
    var docsUrl = apiUrl("/docs");
    var healthUrl = apiUrl("/health");
    var basegenUrl = config.BASEGEN_REPO_URL || "https://github.com/Web3dGuy/BaseGen";
    var tauriUrl = config.TAURI_TEMPLATE_REPO_URL || "https://github.com/Web3dGuy/tauri-workflow-template";

    var launcherMindxApp = document.getElementById("launcher-mindx-app");
    if (launcherMindxApp) { launcherMindxApp.href = mindxApp || "#"; }
    var launcherMindxLogin = document.getElementById("launcher-mindx-login");
    if (launcherMindxLogin) { launcherMindxLogin.href = mindxLogin || "#"; }
    var launcherDaio = document.getElementById("launcher-daio");
    if (launcherDaio) { launcherDaio.href = daioUrl; }
    var launcherDocs = document.getElementById("launcher-docs");
    if (launcherDocs) { launcherDocs.href = docsUrl; }
    var launcherHealth = document.getElementById("launcher-health");
    if (launcherHealth) { launcherHealth.href = healthUrl; }
    var launcherBasegen = document.getElementById("launcher-basegen");
    if (launcherBasegen) { launcherBasegen.href = basegenUrl; }
    var launcherTauri = document.getElementById("launcher-tauri-template");
    if (launcherTauri) { launcherTauri.href = tauriUrl; }

    var launcherSelf = document.getElementById("launcher-self");
    if (launcherSelf) {
      launcherSelf.addEventListener("click", function () { window.open(location.href, "_blank", "noopener"); });
    }
  }

  function wirePersona() {
    var pills = document.querySelectorAll(".persona-pill");
    var cards = document.querySelectorAll(".launcher-card");
    var defaultPersona = (config.DEFAULT_PERSONA || "all").toLowerCase();

    function filter(persona) {
      pills.forEach(function (p) {
        p.classList.toggle("active", (p.getAttribute("data-persona") || "") === persona);
      });
      cards.forEach(function (c) {
        var cardPersona = (c.getAttribute("data-persona") || "all").toLowerCase();
        var show = persona === "all" || cardPersona === persona;
        c.style.display = show ? "" : "none";
      });
    }

    pills.forEach(function (p) {
      p.addEventListener("click", function () {
        filter((p.getAttribute("data-persona") || "all").toLowerCase());
      });
    });
    filter(defaultPersona);
  }

  function fetchAndShow(url, outputId) {
    var out = document.getElementById(outputId);
    if (!out) return;
    if (!url || url.indexOf("/") === 0 && !apiBase) {
      out.textContent = "Error: Set API_BASE in js/config.js.";
      return;
    }
    out.textContent = "Loading…";
    fetch(url, { method: "GET", mode: "cors" })
      .then(function (r) { return r.json().catch(function () { return r.text(); }); })
      .then(function (data) {
        out.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
      })
      .catch(function (e) {
        out.textContent = "Error: " + (e.message || "Request failed");
      });
  }

  function wireFetchButtons() {
    var refreshHealthBtn = document.getElementById("refresh-health-btn");
    if (refreshHealthBtn) refreshHealthBtn.addEventListener("click", function () { checkHealth(); });

    var fetchHealth = document.getElementById("fetch-health-btn");
    if (fetchHealth) fetchHealth.addEventListener("click", function () { fetchAndShow(apiUrl("/health"), "health-output"); });
    var fetchAgents = document.getElementById("fetch-agents-btn");
    if (fetchAgents) fetchAgents.addEventListener("click", function () { fetchAndShow(apiUrl("/agents"), "agents-output"); });
    var fetchSystem = document.getElementById("fetch-system-btn");
    if (fetchSystem) fetchSystem.addEventListener("click", function () { fetchAndShow(apiUrl("/system/status"), "system-status-output"); });
    var fetchRegistry = document.getElementById("fetch-registry-btn");
    if (fetchRegistry) fetchRegistry.addEventListener("click", function () { fetchAndShow(apiUrl("/registry/tools"), "registry-output"); });

    var customMethod = document.getElementById("custom-method");
    var customPath = document.getElementById("custom-path");
    var customBody = document.getElementById("custom-body");
    var customSend = document.getElementById("custom-send-btn");
    var customOut = document.getElementById("custom-output");
    if (customSend && customOut) {
      customSend.addEventListener("click", function () {
        var path = (customPath && customPath.value.trim()) || "/health";
        var method = (customMethod && customMethod.value) || "GET";
        var url = apiUrl(path);
        if (!apiBase && path.charAt(0) === "/") {
          customOut.textContent = "Error: Set API_BASE in js/config.js.";
          return;
        }
        customOut.textContent = "Loading…";
        var opts = { method: method, mode: "cors" };
        if (method === "POST" && customBody && customBody.value.trim()) {
          opts.headers = { "Content-Type": "application/json" };
          opts.body = customBody.value.trim();
        }
        fetch(url, opts)
          .then(function (r) { return r.json().catch(function () { return r.text(); }); })
          .then(function (data) {
            customOut.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
          })
          .catch(function (e) {
            customOut.textContent = "Error: " + (e.message || "Request failed");
          });
      });
    }
  }

  function wireCopyApiBase() {
    var btn = document.getElementById("copy-api-base-btn");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var text = apiBase || (typeof location !== "undefined" ? location.origin : "");
      if (!text) return;
      navigator.clipboard.writeText(text).then(function () {
        var orig = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = orig; }, 1500);
      }).catch(function () {});
    });
  }

  function wireBankon() {
    var btn = document.getElementById("bankon-btn");
    var out = document.getElementById("bankon-output");
    var link = document.getElementById("bankon-link");
    var bankonPageUrl = apiUrl("/bankon/page");
    link.href = bankonPageUrl;
    link.target = "_blank";
    link.rel = "noopener";

    if (btn && out) {
      btn.addEventListener("click", function () {
        out.textContent = "Loading…";
        var url = apiUrl("/bankon");
        if (!url || url === "/bankon") {
          out.textContent = "Error: Set API_BASE in js/config.js to your mindX backend (e.g. https://mindx.pythai.net).";
          return;
        }
        fetch(url, { method: "GET", mode: "cors" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            out.textContent = JSON.stringify(data, null, 2);
          })
          .catch(function (e) {
            out.textContent = "Error: " + (e.message || "Could not reach backend. Set API_BASE in js/config.js to https://mindx.pythai.net (or your backend URL).");
          });
      });
    }
  }

  function wireNav() {
    var links = document.querySelectorAll(".nav-link");
    var panels = document.querySelectorAll(".panel");
    function show(id) {
      panels.forEach(function (p) {
        p.classList.toggle("active", p.id === id);
      });
      links.forEach(function (a) {
        a.classList.toggle("active", (a.getAttribute("href") || "").replace("#", "") === id);
      });
    }
    links.forEach(function (a) {
      a.addEventListener("click", function (e) {
        var href = a.getAttribute("href");
        if (href && href.startsWith("#")) {
          e.preventDefault();
          show(href.slice(1));
        }
      });
    });
    var hash = location.hash ? location.hash.slice(1) : "dashboard";
    show(hash);
  }

  wireApiLinks();
  wireLaunchers();
  wirePersona();
  wireFetchButtons();
  wireCopyApiBase();
  wireNav();
  wireBankon();
  checkHealth();
})();
