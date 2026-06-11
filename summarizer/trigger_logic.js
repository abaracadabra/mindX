/*
 * trigger_logic.js — de-minified, annotated reconstruction of how Claude Code
 * decides WHEN to compact (and at what window size).
 *
 * Source: strings + raw byte slices extracted from the Bun-compiled binary
 *   /home/hacker/.local/share/claude/versions/2.1.168   (Claude Code v2.1.168)
 *
 * The original is heavily minified single-line JS. Identifiers below keep the
 * binary's mangled names (cn, wh$, hE4, ot6, ...) so you can grep the bundle,
 * with readable aliases in comments. Logic is verbatim; only whitespace,
 * comments, and a few inferred constant names were added.
 *
 * Numeric constants recovered from the binary:
 *   NE4 = 13000   // compact head-room: fire compaction this many tokens
 *                 //   before the window is completely full
 *   EE4 = 3000    // hard-block head-room below the configured ceiling
 *   lt6 = 0.2     // default precomputeBufferFraction (tengu_amber_rokovoko)
 *   IE4           // cap applied to the "used tokens" estimate (uAH)
 *   rt6 / CE4     // min / max allowed window (lower & upper clamps)
 *   RE4           // model-default window used when model max < 1,000,000
 *   at6           // turn-counter ceiling for "rapid refill" detection
 *
 * Relevant environment variables:
 *   CLAUDE_CODE_AUTO_COMPACT_WINDOW   override the auto-compact window ("auto"|"500k"|"1m"|<tokens>)
 *   CLAUDE_AUTOCOMPACT_PCT_OVERRIDE   force the compact threshold to a % of the window (test)
 *   CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE  force the hard-block token limit (test)
 *   CLAUDE_CODE_COLD_COMPACT          enable "cold" compaction (also clears REPL/VM state)
 */

// ---------------------------------------------------------------------------
// ot6(str)  —  parse a window-size string into a token count (or "auto").
//   "auto"            -> "auto"
//   "1m" / "2.5m"     -> *1_000_000
//   "500k"            -> *1_000
//   "120000"          -> literal token count
//   "100".."1000"     -> treated as thousands (so "500" means 500k)
// Returns undefined if the result is non-finite or outside [rt6, CE4].
// ---------------------------------------------------------------------------
function ot6(H /* str */) {
  let $ = H.trim().toLowerCase();
  if ($ === "auto") return "auto";
  let q;
  if ($.endsWith("m")) q = parseFloat($) * 1e6;
  else if ($.endsWith("k")) q = parseFloat($) * 1000;
  else {
    let K = parseInt($, 10);
    q = (K >= 100 && K <= 1000) ? K * 1000 : K; // bare 100..1000 read as "k"
  }
  if (!Number.isFinite(q) || q < rt6 || q > CE4) return;
  return Math.round(q);
}

// ---------------------------------------------------------------------------
// cn(model, settingsWindow)  —  RESOLVE the effective auto-compact window.
// Precedence (highest first):
//   1. env  CLAUDE_CODE_AUTO_COMPACT_WINDOW
//   2. settings value ($)
//   3. A/B experiment value (bE4, opus-4-8 only)
//   4. model-default (RE4) when the model's real max context < 1M
//   5. "auto" — a per-model tuned window (y1A[model]) or the model max
// Everything is finally clamped by the model's true max context K = tv(model).
// Returns { window, configured, source }.
// ---------------------------------------------------------------------------
function cn(H /* model */, $ /* settingsWindow */) {
  let q = eK(H);                 // normalized model id
  let K = tv(H, QZ());           // model's true max context window (hard ceiling)

  // (1) environment override
  if (process.env.CLAUDE_CODE_AUTO_COMPACT_WINDOW) {
    let f = r6H("CLAUDE_CODE_AUTO_COMPACT_WINDOW",
                process.env.CLAUDE_CODE_AUTO_COMPACT_WINDOW, rt6, CE4);
    if (f.status !== "invalid") {
      let Y = Math.max(rt6, f.effective);
      return { window: Math.min(K, Y), configured: Y, source: "env" };
    }
  }
  // (2) settings.json value
  if ($ !== void 0)
    return { window: Math.min(K, $), configured: $, source: "settings" };
  // (3) gated experiment (only claude-opus-4-8)
  let _ = bE4(q);
  if (_ !== void 0)
    return { window: Math.min(K, _), configured: _, source: "experiment" };
  // (4) model default when the model is sub-1M context
  if (K < 1e6 && h1A.has(q))
    return { window: Math.min(K, RE4), configured: RE4, source: "model-default" };
  // (5) "auto" — tuned per model, else the model max
  let z = (fT() ? y1A[q] : void 0) ?? K;
  return { window: Math.min(K, z), configured: z, source: "auto" };
}

// ---------------------------------------------------------------------------
// z7H(model, settingsWindow)  —  tokens REMAINING before the window is hit.
//   remaining = effectiveWindow - min(usedTokens, IE4)
// (uAH = current used-token estimate; capped by IE4)
// ---------------------------------------------------------------------------
function z7H(H, $) {
  let q = Math.min(uAH(H), IE4);
  let K = fT() ? $ : void 0;
  let { window: _ } = cn(H, K);
  return _ - q;
}

// ---------------------------------------------------------------------------
// wh$(window, opts)  —  the COMPACT THRESHOLD, expressed in tokens.
// Compaction fires once usage crosses (window - 13000), i.e. 13k tokens of
// head-room. A test override (CLAUDE_AUTOCOMPACT_PCT_OVERRIDE) can instead set
// it to a percentage of the window.
// ---------------------------------------------------------------------------
function wh$(H /* window */, $ /* opts */) {
  let q = H - 13000;                  // NE4 = 13000
  let K = $.testPctOverride;
  if (K !== void 0 && !isNaN(K) && K > 0 && K <= 100)
    return Math.min(Math.floor(H * (K / 100)), q);
  return q;
}

// He6()  —  assemble the opts object wh$/hE4 consume from env + experiment.
function He6() {
  let H = process.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE;
  let $ = process.env.CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE;
  return {
    enabled: fT(),                        // is auto-compact globally enabled?
    precomputeBufferFraction: C1A(),      // default 0.2 (lt6)
    testPctOverride: H ? parseFloat(H) : void 0,
    testBlockingOverride: $ ? parseInt($, 10) : void 0,
  };
}

// wv8(model, settings) — threshold expressed against tokens-remaining.
function wv8(H, $) { return wh$(z7H(H, $), He6()); }

// ---------------------------------------------------------------------------
// hE4(used, window, opts, configured)  —  the LEVEL state machine.
// Maps current usage onto one of: "ok" | "warn" | "compact" | "blocked".
//   blocked  : used >= (configured - 3000)  [or testBlockingOverride] -> stop, must compact
//   compact  : auto-compact enabled AND used >= compactThreshold       -> fire summarizer
//   warn     : used >= compactThreshold - 20000                        -> "Context low" UI
//   ok       : otherwise
// pctLeft is the % of the (enabled) window still free, shown in the UI.
// ---------------------------------------------------------------------------
function hE4(H /* used */, $ /* window */, q /* opts */, K = $ /* configured */) {
  let _ = wh$($, q);                         // compact threshold (tokens)
  let A = q.enabled ? _ : $;                  // active ceiling
  let z = A - 20000;                          // warn band starts 20k before compact
  let f = q.testBlockingOverride;
  let Y = (f !== void 0 && !isNaN(f) && f > 0) ? f : K - 3000;  // EE4 = 3000
  let O = Math.max(0, Math.round((A - H) / A * 100));           // pctLeft

  if (H >= Y) return { level: "blocked", pctLeft: O };
  if (q.enabled && H >= _) return { level: "compact", pctLeft: O };
  if (H >= z) return { level: "warn", pctLeft: O };
  return { level: "ok" };
}

// ---------------------------------------------------------------------------
// I1A(messages, ...)  —  prefix-token accounting used to decide what can be
// dropped/snipped, and to surface counts (documents, images, tool_results)
// that the compaction step reports on. Returns null when nothing exceeds the
// threshold (Y = wv8(...)).
// ---------------------------------------------------------------------------
function I1A(H /* messages */, $, q, K = 0 /* snipTokensFreed */) {
  let _ = UoH(H);
  if (!_) return null;
  let A = _.input_tokens + _.cache_read_input_tokens + _.cache_creation_input_tokens;
  let z = xW(H, $G($));                       // messages token estimate
  let f = Math.max(0, A - K - z);             // prefix tokens
  let Y = wv8($, q);                          // threshold (tokens remaining)
  if (f <= Y) return null;

  let O = 0 /* documents */, M = 0 /* images */;
  let w = (j) => {
    for (let D of j) {
      let J = D;
      if (J.type === "document") O++;
      else if (J.type === "image") M++;
      else if (J.type === "tool_result" && Array.isArray(J.content)) w(J.content);
    }
  };
  for (let j of H) {
    let D = j.message?.content;
    if (Array.isArray(D)) w(D);
  }
  return {
    prefixTokens: f, thresholdTokens: Y, totalInputTokens: A,
    messagesEstimate: z, snipTokensFreed: K,
    documentBlockCount: O, imageBlockCount: M,
  };
}

// st6(state)  —  "rapid refill" guard: counts consecutive compactions that
// happened again within at6 turns, used to back off from compaction loops.
function st6(H) {
  return (H?.compacted === true && H.turnCounter < at6)
    ? (H?.consecutiveRapidRefills ?? 0) + 1
    : 0;
}
