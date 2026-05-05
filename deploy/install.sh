#!/usr/bin/env bash
# Installer for aimesh-optimizer.
# Run as root from inside the cloned repo:
#     sudo bash deploy/install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Please run as root: sudo bash deploy/install.sh" >&2
    exit 1
fi

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_USER="${SUDO_USER:-$(logname 2>/dev/null || echo nobody)}"
SERVICE_NAME="aimesh-optimizer"

echo "==> Install dir:    $INSTALL_DIR"
echo "==> Service user:   $SERVICE_USER"

# Make sure system Python + venv module are present
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found; install Python 3.11+ first." >&2
    exit 1
fi
if ! python3 -c 'import venv' >/dev/null 2>&1; then
    echo "==> Installing python3-venv"
    apt-get update -qq
    apt-get install -y python3-venv
fi

# venv + deps
if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
    echo "==> Creating virtualenv"
    sudo -u "$SERVICE_USER" python3 -m venv "$INSTALL_DIR/.venv"
fi
echo "==> Installing dependencies"
sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
sudo -u "$SERVICE_USER" "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"

# .env scaffolding
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    echo "==> Creating .env from template"
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    chown "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    echo "    !! Edit $INSTALL_DIR/.env and set ASUS_PASS before starting the service."
fi

# Render and install systemd unit
UNIT_SRC="$INSTALL_DIR/deploy/aimesh-optimizer.service"
UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"
echo "==> Installing $UNIT_DST"
sed \
    -e "s|__INSTALL_DIR__|$INSTALL_DIR|g" \
    -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
    "$UNIT_SRC" > "$UNIT_DST"
chmod 644 "$UNIT_DST"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null
echo
echo "Done."
echo
echo "Next steps:"
echo "  1. Edit credentials:   sudo -e $INSTALL_DIR/.env"
echo "  2. Start service:      sudo systemctl restart $SERVICE_NAME"
echo "  3. Test:               curl -sf http://127.0.0.1:8080/health"
echo "  4. Trigger optimize:   curl -sf http://127.0.0.1:8080/optimize"
echo "  5. Tail logs:          journalctl -u $SERVICE_NAME -f"
