#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
#
# Uninstall WordPress.agent from a VPS.
# Removes the service unit, install dir, and (with --purge) the env file and user.
#
# Usage:
#   sudo bash scripts/uninstall.sh           # leave env + user
#   sudo bash scripts/uninstall.sh --purge   # remove everything

set -euo pipefail

INSTALL_DIR="/opt/wordpress-agent"
ENV_DIR="/etc/wordpress-agent"
SERVICE_USER="wpagent"
SERVICE_GROUP="wpagent"
PURGE=0

for arg in "$@"; do
    case "${arg}" in
        --purge) PURGE=1 ;;
        *) echo "Unknown arg: ${arg}" >&2; exit 1 ;;
    esac
done

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "ERROR: must run as root" >&2
        exit 1
    fi
}

stop_service() {
    if systemctl list-unit-files | grep -q '^wordpress-agent.service'; then
        systemctl disable --now wordpress-agent.service || true
        rm -f /etc/systemd/system/wordpress-agent.service
        systemctl daemon-reload
    fi
}

remove_files() {
    rm -rf "${INSTALL_DIR}"
    if [[ "${PURGE}" -eq 1 ]]; then
        rm -rf "${ENV_DIR}"
        if id "${SERVICE_USER}" >/dev/null 2>&1; then
            userdel "${SERVICE_USER}" || true
        fi
        if getent group "${SERVICE_GROUP}" >/dev/null; then
            groupdel "${SERVICE_GROUP}" || true
        fi
    fi
}

main() {
    require_root
    stop_service
    remove_files
    echo "WordPress.agent uninstalled."
    if [[ "${PURGE}" -eq 0 ]]; then
        echo "Note: ${ENV_DIR} preserved. Pass --purge to remove."
    fi
}

main "$@"
