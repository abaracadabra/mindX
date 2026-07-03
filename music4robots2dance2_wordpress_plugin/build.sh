#!/usr/bin/env bash
# Build a distributable zip of the Music 4 Robots 2 Dance 2 plugin.
# take · own · use · share — GPL-3.0-or-later.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SLUG="music4robots2dance2"
OUT="${HERE}/${SLUG}.zip"

cd "${HERE}/.."
rm -f "${OUT}"
zip -r "${OUT}" "$(basename "${HERE}")" \
  -x "*/.git/*" "*/.DS_Store" "*/*.zip" "*/build.sh" >/dev/null

echo "built ${OUT}"
