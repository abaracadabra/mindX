#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
#
# Install the wordpress-agent systemd unit on the mindX VPS. Idempotent.
#
# Topology: the service runs as User=mindx, WorkingDirectory=/home/mindx/mindX,
# using mindX's existing virtualenv (/home/mindx/mindX/.mindx_env). It shares
# mindX's BANKON vault — WP creds + the wordpress.agent wallet live in the
# isolated wordpress.agent.keys vault namespace and are decrypted on-demand
# per /publish. **No WP_APP_PASSWORD is rendered into any env file.**
#
# Run AS ROOT on the VPS:
#   sudo bash /home/mindx/mindX/agents/wordpress_agent/scripts/install.sh
#
# After install (one-time, as the mindx user, before starting the service):
#   sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python \
#       /home/mindx/mindX/scripts/vault/provision_wordpress_agent.py \
#       --wp-base-url https://rage.pythai.net --wp-user codephreak \
#       --publisher-addresses 0xAaa...,0xBbb...
#   sudo systemctl restart wordpress-agent.service
#   curl -s http://127.0.0.1:8765/healthz | jq

set -euo pipefail

INSTALL_DIR="/home/mindx/mindX"
ENV_DIR="/etc/wordpress-agent"
ENV_FILE="${ENV_DIR}/wordpress-agent.env"
SERVICE_USER="mindx"
SERVICE_GROUP="mindx"
UNIT_NAME="wordpress-agent.service"

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "ERROR: this script must be run as root" >&2
        exit 1
    fi
}

require_mindx_install() {
    if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
        echo "ERROR: user ${SERVICE_USER!r} does not exist. Install mindX first." >&2
        exit 1
    fi
    if [[ ! -d "${INSTALL_DIR}" ]]; then
        echo "ERROR: ${INSTALL_DIR} not found. mindX must be deployed there first." >&2
        exit 1
    fi
    if [[ ! -x "${INSTALL_DIR}/.mindx_env/bin/python" ]]; then
        echo "ERROR: ${INSTALL_DIR}/.mindx_env/bin/python not found." >&2
        exit 1
    fi
}

stage_env_file() {
    # Optional, dev/operator-only env file. No secrets belong here in production —
    # they live in the BANKON vault (wordpress.agent.keys namespace).
    install -d -m 0750 -o root -g "${SERVICE_GROUP}" "${ENV_DIR}"
    if [[ ! -f "${ENV_FILE}" ]]; then
        cat > "${ENV_FILE}" <<'EOF'
# wordpress-agent — environment file (PRODUCTION: NO SECRETS HERE).
# Secrets live in the BANKON vault under context=wordpress.agent.keys and are
# decrypted on-demand per /publish. This file is the place for non-secret
# operational overrides only (binding host/port, timeouts).
#
# WP_SERVER_HOST=127.0.0.1
# WP_SERVER_PORT=8765
# WP_TIMEOUT=30
EOF
        chmod 0640 "${ENV_FILE}"
        chown root:"${SERVICE_GROUP}" "${ENV_FILE}"
        echo "Staged ${ENV_FILE} (no secrets — see docs/WORDPRESS_PUBLISHING.md)"
    else
        echo "Env file already present at ${ENV_FILE} (left untouched)"
    fi
}

install_systemd_unit() {
    install -m 0644 \
        "${INSTALL_DIR}/agents/wordpress_agent/deploy/systemd/${UNIT_NAME}" \
        "/etc/systemd/system/${UNIT_NAME}"
    systemctl daemon-reload
    systemctl enable "${UNIT_NAME}"
    echo
    echo "Service installed. Provision the vault namespace (one-time) then start:"
    echo "  sudo -u ${SERVICE_USER} ${INSTALL_DIR}/.mindx_env/bin/python \\"
    echo "    ${INSTALL_DIR}/scripts/vault/provision_wordpress_agent.py \\"
    echo "    --wp-base-url https://rage.pythai.net --wp-user codephreak"
    echo "  sudo systemctl start ${UNIT_NAME}"
    echo "  curl http://127.0.0.1:8765/healthz"
}

main() {
    require_root
    require_mindx_install
    stage_env_file
    install_systemd_unit
    echo
    echo "wordpress-agent installation complete."
}

main "$@"
