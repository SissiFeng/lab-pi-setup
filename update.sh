#!/usr/bin/env bash
# ============================================
# 🔄 NeverOT Lab Pi — Update Script
# ============================================
# Pulls latest code, rebuilds if needed, restarts services.
# Usage:  ./update.sh
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step() { echo -e "\n${BLUE}▶ $1${NC}"; }
ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BLUE}🔄 Updating NeverOT Lab Pi...${NC}"

# Pull latest repo
step "Pulling latest lab-pi-setup..."
cd "$SCRIPT_DIR"
git pull
ok "Repo updated"

# Update ZeroClaw if source changed
step "Checking ZeroClaw for updates..."
if [ -d "$HOME/zeroclaw" ]; then
    cd "$HOME/zeroclaw"
    OLD_HASH=$(git rev-parse HEAD 2>/dev/null || echo "none")
    git pull
    NEW_HASH=$(git rev-parse HEAD 2>/dev/null || echo "none")
    if [ "$OLD_HASH" != "$NEW_HASH" ]; then
        echo "  Source changed, rebuilding..."
        export PATH="$HOME/.cargo/bin:$PATH"
        cargo build --release 2>&1 | tail -3
        ok "ZeroClaw rebuilt"
    else
        ok "ZeroClaw already up to date"
    fi
else
    warn "ZeroClaw not found. Run ./setup.sh first."
fi

# Update Python packages
step "Updating Python packages..."
source "$HOME/lab-env/bin/activate"
pip install --upgrade pyserial opencv-python-headless smbus2 requests flask pyyaml 2>&1 | tail -3
deactivate
ok "Python packages updated"

# Reinstall service files (in case they changed)
step "Updating systemd services..."
for svc in lab-camera lab-sensors lab-bridge lab-zeroclaw; do
    sudo cp "$SCRIPT_DIR/services/systemd/${svc}.service" /etc/systemd/system/
done
sudo systemctl daemon-reload

# Restart all services
step "Restarting services..."
for svc in lab-camera lab-sensors lab-bridge lab-zeroclaw; do
    sudo systemctl restart "$svc" 2>/dev/null || warn "${svc} failed to restart"
done
ok "All services restarted"

# Run health check
step "Running health check..."
cd "$SCRIPT_DIR"
bash ./check.sh
