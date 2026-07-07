#!/usr/bin/env bash
# install_forgejo.sh — stand up a self-hosted Forgejo forge for gitmind on the VPS.
#
# Forgejo (https://forgejo.org) is the GPLv3 community fork of Gitea. This installs
# it as the web-accessible git origin mindX owns at https://git.pythai.net — the
# live, browseable leg of gitmind's origin triad (bare self.git + permaweb THlNK).
#
# Design choices (locked with the operator 2026-06-28):
#   - binary + systemd  (matches the VPS's other services; no Docker)
#   - reuse Postgres    (mindX already runs pgvector/Postgres here)
#   - bind 127.0.0.1:3000, front with Apache vhost for git.pythai.net + Let's Encrypt
#
# Idempotent: safe to re-run. Makes NO Apache/DNS/cert changes itself — it prints the
# exact next steps so the operator stays in control of the public surface.
#
# Run on the VPS as root (or a sudo-capable user):
#   sudo bash scripts/install_forgejo.sh
#
# Override anything via env, e.g.:
#   FORGEJO_VERSION=11.0.1 DOMAIN=git.pythai.net DB_NAME=forgejo bash scripts/install_forgejo.sh
set -euo pipefail

# ── config (override via env) ──────────────────────────────────────────────
FORGEJO_VERSION="${FORGEJO_VERSION:-11.0.1}"
FORGEJO_ARCH="${FORGEJO_ARCH:-linux-amd64}"
DOMAIN="${DOMAIN:-git.pythai.net}"
HTTP_ADDR="${HTTP_ADDR:-127.0.0.1}"        # bind localhost; Apache is the public face
HTTP_PORT="${HTTP_PORT:-3000}"
GIT_USER="${GIT_USER:-git}"
WORK_DIR="${WORK_DIR:-/var/lib/forgejo}"
CONF_DIR="${CONF_DIR:-/etc/forgejo}"
BIN_PATH="${BIN_PATH:-/usr/local/bin/forgejo}"
# Postgres (reused). DB_PASSWORD auto-generated on first run and saved to CONF_DIR.
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-forgejo}"
DB_USER="${DB_USER:-forgejo}"
# Admin + push identity for gitmind. Token is printed at the end → deposit in vault.
CREATE_ADMIN="${CREATE_ADMIN:-1}"
ADMIN_USER="${ADMIN_USER:-mindx}"
ADMIN_EMAIL="${ADMIN_EMAIL:-mindx@pythai.net}"

DL_URL="https://codeberg.org/forgejo/forgejo/releases/download/v${FORGEJO_VERSION}/forgejo-${FORGEJO_VERSION}-${FORGEJO_ARCH}"

c_grn='\033[0;32m'; c_yel='\033[1;33m'; c_red='\033[0;31m'; c_nc='\033[0m'
info() { echo -e "${c_grn}[forgejo]${c_nc} $*"; }
warn() { echo -e "${c_yel}[forgejo]${c_nc} $*"; }
die()  { echo -e "${c_red}[forgejo]${c_nc} $*" >&2; exit 1; }

# Run privileged commands directly when root, else via sudo.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi
run() { $SUDO "$@"; }
# Run a command as the postgres role, whether we are root or a sudo-capable user.
as_pg() {
  if command -v sudo >/dev/null 2>&1; then sudo -u postgres "$@";
  else su -s /bin/sh postgres -c "$(printf '%q ' "$@")"; fi
}
# Run the forgejo CLI as the git user against the config.
forgejo_cli() {
  if command -v sudo >/dev/null 2>&1; then sudo -u "${GIT_USER}" "${BIN_PATH}" --config "${CONF_DIR}/app.ini" "$@";
  else su -s /bin/sh "${GIT_USER}" -c "$(printf '%q ' "${BIN_PATH}" --config "${CONF_DIR}/app.ini" "$@")"; fi
}

[ "$(uname -s)" = "Linux" ] || die "this installer is Linux-only"
command -v psql >/dev/null 2>&1 || warn "psql not on PATH — ensure Postgres is installed/running (scripts/db_installer.sh)"

# ── 1. dependencies ─────────────────────────────────────────────────────────
info "installing git + git-lfs"
run apt-get update -qq || true
run apt-get install -y git git-lfs >/dev/null

# ── 2. binary ───────────────────────────────────────────────────────────────
if [ -x "${BIN_PATH}" ] && "${BIN_PATH}" --version 2>/dev/null | grep -q "${FORGEJO_VERSION}"; then
  info "binary already at v${FORGEJO_VERSION} — skipping download"
else
  info "downloading Forgejo v${FORGEJO_VERSION} (${FORGEJO_ARCH})"
  tmp="$(mktemp)"
  curl -fsSL "${DL_URL}" -o "${tmp}" || die "download failed: ${DL_URL}"
  run install -m 0755 "${tmp}" "${BIN_PATH}"
  rm -f "${tmp}"
  info "installed $(${BIN_PATH} --version | head -1)"
fi

# ── 3. git system user ──────────────────────────────────────────────────────
if id "${GIT_USER}" >/dev/null 2>&1; then
  info "user '${GIT_USER}' exists"
else
  info "creating system user '${GIT_USER}'"
  run adduser --system --shell /bin/bash --gecos 'Git Version Control' \
      --group --disabled-password --home "/home/${GIT_USER}" "${GIT_USER}"
fi

# ── 4. directory layout ─────────────────────────────────────────────────────
info "creating ${WORK_DIR} and ${CONF_DIR}"
run mkdir -p "${WORK_DIR}"/{custom,data,log}
run chown -R "${GIT_USER}:${GIT_USER}" "${WORK_DIR}"
run chmod -R 750 "${WORK_DIR}"
run mkdir -p "${CONF_DIR}"
run chown root:"${GIT_USER}" "${CONF_DIR}"
run chmod 770 "${CONF_DIR}"

# ── 5. Postgres database + role (reused instance) ───────────────────────────
PW_FILE="${CONF_DIR}/db_password"
if run test -f "${PW_FILE}"; then
  DB_PASSWORD="$(run cat "${PW_FILE}")"
  info "reusing saved DB password"
else
  DB_PASSWORD="${DB_PASSWORD:-$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)}"
  echo "${DB_PASSWORD}" | run tee "${PW_FILE}" >/dev/null
  run chown root:"${GIT_USER}" "${PW_FILE}"; run chmod 640 "${PW_FILE}"
  info "generated + saved DB password to ${PW_FILE}"
fi
info "ensuring Postgres role '${DB_USER}' and database '${DB_NAME}'"
as_pg psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  as_pg psql -c "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';"
# keep password in sync with the saved file on re-run
as_pg psql -c "ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
as_pg psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  as_pg psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

# ── 6. app.ini ──────────────────────────────────────────────────────────────
if run test -f "${CONF_DIR}/app.ini"; then
  info "app.ini exists — leaving it untouched (delete it to regenerate)"
else
  info "generating app.ini (+ secrets)"
  SECRET_KEY="$(${BIN_PATH} generate secret SECRET_KEY)"
  INTERNAL_TOKEN="$(${BIN_PATH} generate secret INTERNAL_TOKEN)"
  LFS_JWT_SECRET="$(${BIN_PATH} generate secret JWT_SECRET)"
  tmp_ini="$(mktemp)"
  cat > "${tmp_ini}" <<EOF
APP_NAME = mindX Forge (Forgejo)
RUN_USER = ${GIT_USER}
RUN_MODE = prod
WORK_PATH = ${WORK_DIR}

[server]
DOMAIN           = ${DOMAIN}
SSH_DOMAIN       = ${DOMAIN}
ROOT_URL         = https://${DOMAIN}/
HTTP_ADDR        = ${HTTP_ADDR}
HTTP_PORT        = ${HTTP_PORT}
DISABLE_SSH      = false
START_SSH_SERVER = false
LFS_START_SERVER = true
APP_DATA_PATH    = ${WORK_DIR}/data
LFS_JWT_SECRET   = ${LFS_JWT_SECRET}

[database]
DB_TYPE  = postgres
HOST     = ${DB_HOST}:${DB_PORT}
NAME     = ${DB_NAME}
USER     = ${DB_USER}
PASSWD   = ${DB_PASSWORD}
SSL_MODE = disable

[repository]
ROOT = ${WORK_DIR}/data/forgejo-repositories

[security]
INSTALL_LOCK   = true
SECRET_KEY     = ${SECRET_KEY}
INTERNAL_TOKEN = ${INTERNAL_TOKEN}

[service]
DISABLE_REGISTRATION              = true
REQUIRE_SIGNIN_VIEW               = true
DEFAULT_KEEP_EMAIL_PRIVATE        = true
ENABLE_NOTIFY_MAIL                = false

[log]
MODE      = file
LEVEL     = info
ROOT_PATH = ${WORK_DIR}/log

[session]
PROVIDER = file

[lfs]
PATH = ${WORK_DIR}/data/lfs
EOF
  run install -o root -g "${GIT_USER}" -m 640 "${tmp_ini}" "${CONF_DIR}/app.ini"
  rm -f "${tmp_ini}"
fi

# ── 7. systemd unit ─────────────────────────────────────────────────────────
info "writing systemd unit (forgejo.service)"
unit="$(mktemp)"
cat > "${unit}" <<EOF
[Unit]
Description=Forgejo (mindX self-hosted forge)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=${GIT_USER}
Group=${GIT_USER}
WorkingDirectory=${WORK_DIR}
ExecStart=${BIN_PATH} web --config ${CONF_DIR}/app.ini
Restart=always
RestartSec=3
Environment=USER=${GIT_USER} HOME=/home/${GIT_USER} GITEA_WORK_DIR=${WORK_DIR}
# hardening
NoNewPrivileges=true
ProtectSystem=full
PrivateDevices=true

[Install]
WantedBy=multi-user.target
EOF
run install -m 0644 "${unit}" /etc/systemd/system/forgejo.service
rm -f "${unit}"
run systemctl daemon-reload
run systemctl enable forgejo.service >/dev/null 2>&1 || true
run systemctl restart forgejo.service
sleep 2
run systemctl is-active --quiet forgejo.service && info "forgejo.service is active" || warn "forgejo.service not active — check: journalctl -u forgejo"

# ── 8. admin user + gitmind push token ──────────────────────────────────────
TOKEN=""
if [ "${CREATE_ADMIN}" = "1" ]; then
  if forgejo_cli admin user list 2>/dev/null | awk '{print $2}' | grep -qx "${ADMIN_USER}"; then
    info "admin '${ADMIN_USER}' already exists"
  else
    ADMIN_PW="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)"
    info "creating admin '${ADMIN_USER}' (password saved to ${CONF_DIR}/admin_password)"
    echo "${ADMIN_PW}" | run tee "${CONF_DIR}/admin_password" >/dev/null
    run chown root:"${GIT_USER}" "${CONF_DIR}/admin_password"; run chmod 640 "${CONF_DIR}/admin_password"
    forgejo_cli admin user create --admin --username "${ADMIN_USER}" \
      --email "${ADMIN_EMAIL}" --password "${ADMIN_PW}" --must-change-password=false || \
      warn "admin create failed — create it via the web UI"
  fi
  TOKEN="$(forgejo_cli admin user generate-access-token --username "${ADMIN_USER}" \
            --scopes write:repository,write:user --raw 2>/dev/null || true)"
fi

# ── 9. next steps ───────────────────────────────────────────────────────────
cat <<EOF

$(info "Forgejo is up on ${HTTP_ADDR}:${HTTP_PORT} (private; behind Apache).")

NEXT STEPS (operator — public surface stays in your hands):

1) DNS: point ${DOMAIN} A record at this VPS (168.231.126.58).

2) Apache vhost + SSL:
     sudo cp deploy/apache/git-pythai-net.conf /etc/apache2/sites-available/
     sudo a2enmod proxy proxy_http headers
     sudo a2ensite git-pythai-net
     sudo systemctl reload apache2
     sudo certbot --apache -d ${DOMAIN}

3) Wire gitmind → Forgejo (deposit the push token in the BANKON vault):
EOF
if [ -n "${TOKEN}" ]; then
  echo "     python manage_credentials.py store forgejo_token \"${TOKEN}\""
  echo "     python manage_credentials.py store forgejo_url \"https://${DOMAIN}\""
  echo "     python manage_credentials.py store forgejo_user \"${ADMIN_USER}\""
  echo "     python manage_credentials.py store forgejo_repo \"${ADMIN_USER}/mindX\""
  warn "^ access token shown ONCE — store it now, it is not recoverable."
else
  echo "     # generate a token in the web UI (Settings → Applications, scope write:repository), then:"
  echo "     python manage_credentials.py store forgejo_token \"<token>\""
  echo "     python manage_credentials.py store forgejo_url \"https://${DOMAIN}\""
fi
cat <<EOF

4) First push + verify:
     python scripts/gitmind.py forgejo --status
     python scripts/gitmind.py forgejo
     # then browse: https://${DOMAIN}/${ADMIN_USER}/mindX

EOF
