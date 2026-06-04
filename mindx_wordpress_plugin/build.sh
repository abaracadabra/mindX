#!/usr/bin/env bash
# Reproducible build of mindx-publish-auth.zip.
# Excludes build artifacts, VCS, and the repo-only docs/ tree.
set -euo pipefail
cd "$(dirname "$0")"
rm -f mindx-publish-auth.zip
mkdir -p .build/mindx-publish-auth
rsync -a \
    --exclude '.git' \
    --exclude '.build' \
    --exclude 'mindx-publish-auth.zip' \
    --exclude 'build.sh' \
    --exclude '.gitignore' \
    --exclude 'docs/' \
    ./ .build/mindx-publish-auth/
( cd .build && zip -qr ../mindx-publish-auth.zip mindx-publish-auth )
rm -rf .build
sha256sum mindx-publish-auth.zip
