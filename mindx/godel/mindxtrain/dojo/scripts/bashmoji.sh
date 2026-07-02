#!/usr/bin/env bash
# ┌──────────────────────────────────────────────────────────────────────────┐
# │  bashmoji — emoji glyphs for the Dojo's shell output.                       │
# └──────────────────────────────────────────────────────────────────────────┘
#
# Vendored from github.com/cryptoagi/bashmoji (shellmoji.sh) so the Dojo always
# has glyphs offline, with an OPTIONAL network refresh that pulls the latest
# upstream set. Source it; it exposes BM_* variables (BM_-prefixed so they never
# clash with the caller's own names).
#
#   source scripts/bashmoji.sh              # use the vendored set (offline)
#   DOJO_BASHMOJI_REFRESH=1 source scripts/bashmoji.sh   # try upstream first
#
# The network path downloads to a cache and imports ONLY `NAME="value"`
# assignment lines (no `$`/backticks), so a tampered remote can't run code.

# ── vendored defaults (a curated subset of cryptoagi/bashmoji) ───────────────
BM_OK="✅";  BM_WARN="⚠️";  BM_ERR="❌";  BM_INFO="ℹ️";  BM_DONE="☑️"
BM_INSTALL="📥"; BM_PKG="📦"; BM_PY="🐍"; BM_NODE="📦"; BM_RUST="⚡"
BM_GEAR="⚙️"; BM_BUILD="👷"; BM_ROCKET="🚀"; BM_NET="🌐"; BM_GPU="🎮"
BM_BRAIN="🧠"; BM_TRAIN="🚂"; BM_SERVER="🖥️"; BM_LLAMA="🦙"; BM_SPARK="✨"
BM_DOJO="道"; BM_SEARCH="🔍"; BM_CLOCK="⏱️"; BM_SKIP="⏭️"; BM_SWORDS="⚔️"

# ── optional network refresh ─────────────────────────────────────────────────
BASHMOJI_URL="${BASHMOJI_URL:-https://raw.githubusercontent.com/cryptoagi/bashmoji/master/shellmoji.sh}"
_bm_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
BASHMOJI_CACHE="${BASHMOJI_CACHE:-${_bm_dir}/.cache/shellmoji.sh}"

# Fetch the upstream emoji file to the cache. Returns non-zero on any failure so
# the caller silently keeps the vendored set.
bashmoji_refresh() {
  local tmp
  mkdir -p "$(dirname "$BASHMOJI_CACHE")" 2>/dev/null || return 1
  tmp="$(mktemp 2>/dev/null)" || return 1
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 15 "$BASHMOJI_URL" -o "$tmp" 2>/dev/null || { rm -f "$tmp"; return 1; }
  elif command -v wget >/dev/null 2>&1; then
    wget -q -T 15 "$BASHMOJI_URL" -O "$tmp" 2>/dev/null || { rm -f "$tmp"; return 1; }
  else
    rm -f "$tmp"; return 1
  fi
  grep -q 'CHECK=' "$tmp" || { rm -f "$tmp"; return 1; }   # sanity-check the payload
  mv "$tmp" "$BASHMOJI_CACHE" 2>/dev/null || { rm -f "$tmp"; return 1; }
}

# Import the cached upstream set safely (assignment lines only) and map a few of
# its names onto our BM_* aliases.
bashmoji_load_upstream() {
  [ -f "$BASHMOJI_CACHE" ] || return 1
  local safe
  safe="$(grep -E '^[A-Z_][A-Z0-9_]*="[^"`$]*"$' "$BASHMOJI_CACHE" 2>/dev/null)" || return 1
  [ -n "$safe" ] || return 1
  eval "$safe"
  [ -n "${CHECK:-}" ]   && BM_OK="$CHECK"
  [ -n "${WARNING:-}" ] && BM_WARN="$WARNING"
  [ -n "${CROSS:-}" ]   && BM_ERR="$CROSS"
  [ -n "${INFO:-}" ]    && BM_INFO="$INFO"
  [ -n "${INSTALL:-}" ] && BM_INSTALL="$INSTALL"
  [ -n "${ROCKET:-}" ]  && BM_ROCKET="$ROCKET"
  [ -n "${PYTHON:-}" ]  && BM_PY="$PYTHON"
  [ -n "${GEAR:-}" ]    && BM_GEAR="$GEAR"
  [ -n "${BUILD:-}" ]   && BM_BUILD="$BUILD"
  return 0
}

if [ "${DOJO_BASHMOJI_REFRESH:-0}" = 1 ]; then
  bashmoji_refresh && bashmoji_load_upstream || true   # network → fall back silently
elif [ -f "$BASHMOJI_CACHE" ]; then
  bashmoji_load_upstream || true                        # reuse a prior refresh
fi
unset _bm_dir
