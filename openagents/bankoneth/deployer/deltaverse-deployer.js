/* DeltaVerse × BANKON Deployer — the participant experience.
 *
 * Weaves the DeltaVerse fabric into the deployer: the changing story is woven
 * from the participant's deploy interaction. Identity is recognized from the
 * deployer's own on-chain authority (NameWrapper.ownerOf(bankon.eth) ==
 * connected wallet → overlord). The HANDOFF step is made visible: deployed
 * contracts hand admin to the bankon.eth overlord (the `from="owner"` wiring).
 * bankon.eth is overlord of the DeltaVerse until renounced to DAIO.
 *
 * Non-invasive: reads window.Deployer.state; never modifies deployer.js.
 * Zero new dependencies. (c) BANKON / PYTHAI.
 */
(function () {
  "use strict";
  if (typeof window === "undefined" || !window.DeltaVerse || !window.DeltaVerse.Fabric) return;

  var fabric = null;
  var last = { account: null, controller: null, armed: null, deployedN: 0 };

  function ticker(text, label) {
    var t = document.getElementById("dv-ticker");
    if (!t) return;
    t.style.opacity = "0";
    setTimeout(function () { t.textContent = "“" + text + "” — " + label; t.style.opacity = ".75"; }, 300);
  }

  // Derive the DeltaVerse role from the deployer's resolved authority.
  // overlord = the connected wallet controls bankon.eth (mainnet) or the
  // rehearsal controller (testnet, relaxed). Otherwise public.
  function roleFor(S) {
    var a = (S.account || "").toLowerCase();
    var c = ((S.authority && S.authority.controller) || "").toLowerCase();
    if (a && c && a === c) return "overlord";
    return "public";
  }

  function renderRoleChip(S) {
    var id = document.getElementById("identity");
    if (!id) return;
    var role = roleFor(S);
    var relaxed = !!(S.authority && S.authority.relaxed);
    var existing = id.querySelector(".dvrole");
    if (existing) existing.remove();
    if (!S.account) return;
    var chip = document.createElement("span");
    chip.className = "dvrole " + role;
    chip.textContent = " · " + role + (relaxed && role === "overlord" ? " (rehearsal)" : "");
    chip.title = "DeltaVerse role — overlord = controls bankon.eth";
    id.appendChild(chip);
  }

  // Make the handoff visible: authority → bankon.eth (overlord) + sovereignty.
  function renderHandoff(S) {
    var bar = document.getElementById("feebar");
    if (!bar) return;
    var ctrl = (S.authority && S.authority.controller) || null;
    var note = bar.querySelector(".dv-handoff");
    if (!note) {
      note = document.createElement("div");
      note.className = "dv-handoff";
      note.style.cssText = "font-family:var(--mono);font-size:10px;color:var(--dim);margin-top:6px";
      bar.appendChild(note);
    }
    var who = ctrl ? (ctrl.slice(0, 6) + "…" + ctrl.slice(-4)) : "bankon.eth";
    note.innerHTML =
      "authority → <b style='color:var(--gold)'>bankon.eth</b> (overlord · " + who + ") · " +
      "deployed admin hands off to the overlord · " +
      "<span title='renounceRole + transfer bankon.eth to the DAIO Governor'>sovereign until <b style='color:var(--green)'>renounced to DAIO</b></span>";
  }

  // Poll the deployer state (it emits no events) and react to changes.
  function tick() {
    try {
      var S = (window.Deployer && window.Deployer.state) || {};
      if (S.account !== last.account) {
        last.account = S.account || null;
        renderRoleChip(S);
        if (fabric && S.account) {
          var role = roleFor(S);
          fabric.recognize(S.account, { role: role });
          ticker("the field recognizes you · " + role, "DeltaVerse");
        }
      }
      var ctrl = (S.authority && S.authority.controller) || null;
      if (ctrl !== last.controller) { last.controller = ctrl; renderHandoff(S); }

      // Deploy interaction → the changing story.
      var armedId = S.armed && (S.armed.id || S.armed.name);
      if (armedId && armedId !== last.armed) {
        last.armed = armedId;
        if (fabric) fabric.addParticipant({ who: "deploy:" + armedId, role: roleFor(S),
          label: (S.armed.label || armedId), lines: ["armed " + (S.armed.label || armedId)] });
        ticker("DEPLOY armed · " + (S.armed.label || armedId), "the field");
      }
      var dn = S.deployed ? Object.keys(S.deployed).length : 0;
      if (dn > last.deployedN) {
        last.deployedN = dn;
        if (fabric) fabric.addParticipant({ who: "launched:" + dn, role: roleFor(S),
          label: "launch #" + dn, lines: ["a contract entered the chain — handed to bankon.eth"] });
        ticker("LAUNCH → HANDOFF to bankon.eth · contract " + dn, "the story changes");
      }
    } catch (e) { /* never break the deployer */ }
  }

  function boot() {
    try {
      fabric = new window.DeltaVerse.Fabric({ canvas: "#dv-fabric", onQuote: ticker });
      fabric.start();
      ticker("the DeltaVerse is the substrate of the changing story — woven from your will and intent", "DeltaVerse");
      setInterval(tick, 1000);
      tick();
    } catch (e) { /* fabric optional — deployer works without it */ }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
