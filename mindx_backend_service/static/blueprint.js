// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048.
// blueprint.js — the DEEP, WALLED admin diagnostics for the Gödel Machine Index.
//
// CLEAN-ROOM: this is mindX's own renderer for the *Gödel Eval Blueprint*
// (docs/GODEL_EVAL_BLUEPRINT.md). It is NOT Palantir's Blueprint UI toolkit
// (blueprintjs.com) — no React, no @blueprintjs/* package, no CDN, no import.
// Dependency-free vanilla JS, consistent with the house no-CDN / clean-room rule.
//
// Loaded by /machine only after an OVERLORD is recognized. Renders separated
// surfaces the public scoreboard hides: the full per-predicate evidence ledger,
// the coverage math against the blueprint thresholds, and live Gödel-choice
// telemetry. Presentation layer over /insight/godel/* — no secrets embedded.
(function(){
  "use strict";
  var GOLD="#e3b341", MUT="#8b949e", OK="#56d364", NO="#f85149", WAIT="#d9a441";
  function esc(s){return String(s==null?"":s).replace(/[&<>]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}
  function h(html){var d=document.createElement("div");d.innerHTML=html;return d.firstChild;}
  function auth(tok){return tok?{"Authorization":"Bearer "+tok}:{};}

  function panel(title, subtitle){
    return '<div class="bp-panel"><div class="bp-h"><span class="bp-t">'+esc(title)+'</span>'+
      (subtitle?'<span class="bp-s">'+esc(subtitle)+'</span>':'')+'</div><div class="bp-body"></div></div>';
  }

  // — surface 1: per-predicate evidence ledger (flatten every evidence key) —
  function evidenceLedger(gmi){
    var rows=(gmi.predicates||[]).map(function(p){
      var ev=p.evidence||{}, cls=(p.verdict||"").indexOf("PROVEN")>=0?OK:(p.verdict||"").indexOf("FALSIF")>=0?NO:WAIT;
      var kv=Object.keys(ev).map(function(k){
        var v=ev[k]; if(typeof v==="object")v=JSON.stringify(v);
        return '<tr><td class="k">'+esc(k)+'</td><td class="v">'+esc(v)+'</td></tr>';
      }).join("")||'<tr><td class="k" colspan="2" style="color:'+MUT+'">no evidence recorded</td></tr>';
      return '<div class="bp-pred"><div class="bp-pid"><b style="color:'+GOLD+'">'+esc(p.id)+'</b> '+
        esc((p.name||"").replace(/_/g," "))+' <span style="color:'+cls+'">— '+esc(p.verdict)+'</span></div>'+
        '<div class="bp-det">'+esc(p.detail)+'</div><table class="bp-tbl">'+kv+'</table></div>';
    }).join("");
    return rows;
  }

  // — surface 2: coverage math vs blueprint thresholds —
  function coverageMath(gmi){
    var pc=(gmi.proof_coverage||0), sc=(gmi.surrogate_coverage||0), pp=(gmi.predicates_proven||0);
    function row(label,val,thr,ok){return '<tr><td>'+label+'</td><td class="v">'+val+'</td><td class="v">'+thr+'</td>'+
      '<td style="color:'+(ok?OK:NO)+'">'+(ok?"PASS":"BELOW")+'</td></tr>';}
    return '<table class="bp-tbl bp-math"><thead><tr><th>metric</th><th>actual</th><th>threshold</th><th>gate</th></tr></thead><tbody>'+
      row("proof coverage",(pc*100).toFixed(1)+"%","≥ 50%",pc>=0.5)+
      row("surrogate coverage",(sc*100).toFixed(1)+"%","(context)",true)+
      row("predicates proven",pp+"/8","8/8",pp>=8)+
      '</tbody></table><div class="bp-note">Verdict flips to GODEL_MACHINE only when proof coverage clears 50% AND all eight predicates hold. '+
      'Constraint: '+esc(gmi.constraint||"")+'</div>';
  }

  // — surface 3: live Gödel-choice telemetry (gated pull, token-authed) —
  function telemetry(root, tok){
    var box=root.querySelector('[data-s="telemetry"] .bp-body');
    fetch('/insight/godel/recent?limit=25',{cache:"no-store",headers:auth(tok)})
      .then(function(r){return r.ok?r.json():null;}).then(function(d){
        var items=(d&&(d.choices||d.recent||d.events))||[];
        if(!items.length){box.innerHTML='<div style="color:'+MUT+'">No recent Gödel choices in the window.</div>';return;}
        box.innerHTML='<table class="bp-tbl"><thead><tr><th>when</th><th>choice</th><th>rationale</th></tr></thead><tbody>'+
          items.slice(0,25).map(function(e){
            var t=e.ts||e.timestamp||e.time||""; if(typeof t==="number")t=new Date(t*(t<1e12?1000:1)).toISOString().slice(5,16).replace("T"," ");
            return '<tr><td class="v" style="white-space:nowrap">'+esc(t)+'</td><td>'+esc(e.choice||e.decision||e.action||e.kind||"")+'</td>'+
              '<td style="color:'+MUT+'">'+esc((e.rationale||e.reason||e.detail||"").slice(0,160))+'</td></tr>';
          }).join("")+'</tbody></table>';
      }).catch(function(){box.innerHTML='<div style="color:'+NO+'">telemetry unavailable ('+esc("gated / offline")+').</div>';});
  }

  function styleOnce(){
    if(document.getElementById("bp-style"))return;
    var s=document.createElement("style");s.id="bp-style";
    s.textContent='#blueprint-root{padding:6px 0 8px}'+
      '.bp-panel{margin:0;border-top:1px solid rgba(255,255,255,.06)}'+
      '.bp-h{display:flex;align-items:baseline;gap:12px;padding:18px 24px 6px}'+
      '.bp-t{font-size:12px;letter-spacing:.2em;text-transform:uppercase;font-weight:700;color:#e6edf3}'+
      '.bp-s{font-size:10.5px;color:'+MUT+';letter-spacing:.04em}'+
      '.bp-body{padding:8px 24px 20px}'+
      '.bp-pred{padding:12px 0;border-bottom:1px dashed rgba(255,255,255,.06)}'+
      '.bp-pid{font-size:13px;font-weight:700}.bp-det{color:#b6bec9;font-size:12px;margin:5px 0 8px}'+
      '.bp-tbl{width:100%;border-collapse:collapse;font-size:11.5px}'+
      '.bp-tbl td,.bp-tbl th{text-align:left;padding:5px 10px 5px 0;vertical-align:top;border-bottom:1px solid rgba(255,255,255,.04)}'+
      '.bp-tbl th{color:'+GOLD+';font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:10px}'+
      '.bp-tbl td.k{color:'+MUT+';white-space:nowrap;width:1%;padding-right:22px}'+
      '.bp-tbl td.v{color:#e6edf3;font-variant-numeric:tabular-nums;word-break:break-word}'+
      '.bp-math td{padding:6px 14px 6px 0}.bp-note{margin-top:12px;font-size:11px;color:'+MUT+';line-height:1.6}'+
      '.bp-raw{margin:0 24px 22px;padding:14px;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.06);border-radius:9px;'+
      'font-size:10.5px;color:#9aa4b0;white-space:pre-wrap;word-break:break-word;max-height:340px;overflow:auto}';
    document.head.appendChild(s);
  }

  window.Blueprint={
    render:function(root, gmi, tok){
      if(!root)return; styleOnce();
      root.innerHTML=
        '<div data-s="ledger">'+panel("Predicate Evidence Ledger","every measured surface, G1–G8")+'</div>'+
        '<div data-s="math">'+panel("Coverage Math","actual vs blueprint thresholds")+'</div>'+
        '<div data-s="telemetry">'+panel("Gödel-Choice Telemetry","last 25 self-referential choices (live)")+'</div>'+
        '<div data-s="raw">'+panel("Raw Audit Payload","the verbatim /insight/godel/machine object")+'</div>';
      root.querySelector('[data-s="ledger"] .bp-body').innerHTML=evidenceLedger(gmi||{});
      root.querySelector('[data-s="math"] .bp-body').innerHTML=coverageMath(gmi||{});
      var raw=root.querySelector('[data-s="raw"] .bp-body');
      raw.innerHTML='<div class="bp-raw">'+esc(JSON.stringify(gmi||{},null,2))+'</div>';
      telemetry(root, tok);
    }
  };
})();
