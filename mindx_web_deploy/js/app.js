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
    fetch(url, { method: "GET", mode: "cors" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error(r.statusText)); })
      .then(function () { setBackendStatus(true); })
      .catch(function () { setBackendStatus(false); });
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
        fetch(apiUrl("/bankon"), { method: "GET", mode: "cors" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            out.textContent = JSON.stringify(data, null, 2);
          })
          .catch(function (e) {
            out.textContent = "Error: " + (e.message || "Could not reach backend. Set API_BASE in js/config.js.");
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
    if (location.hash) show(location.hash.slice(1));
  }

  wireNav();
  wireBankon();
  checkHealth();
})();
