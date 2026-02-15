#!/usr/bin/env bash
# ============================================
# 🛠️  NeverOT Lab Pi — One-Shot Setup Script
# ============================================
# This script installs everything the Pi needs.
# Safe to run multiple times (idempotent).
#
# Usage:  chmod +x setup.sh && ./setup.sh
# ============================================

set -e  # Stop on errors

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

step() { echo -e "\n${BLUE}▶ $1${NC}"; }
ok()   { echo -e "  ${GREEN}✅ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════╗"
echo "║   🔬 NeverOT Lab Pi Setup               ║"
echo "║   This will take 15-30 minutes.          ║"
echo "║   Grab a coffee! ☕                       ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# -----------------------------------------------
# 1. Update system packages
# -----------------------------------------------
step "Updating system packages (this takes a few minutes)..."
sudo apt update -y && sudo apt upgrade -y
ok "System packages updated"

# -----------------------------------------------
# 2. Install required apt packages
# -----------------------------------------------
step "Installing required system packages..."
sudo apt install -y \
    python3 python3-pip python3-venv python3-dev \
    git curl wget \
    libcamera-tools v4l-utils \
    i2c-tools \
    screen htop \
    build-essential pkg-config libssl-dev \
    libjpeg-dev libopenjp2-7 \
    2>&1 | tail -3
ok "System packages installed"

# -----------------------------------------------
# 3. Enable I2C interface
# -----------------------------------------------
step "Enabling I2C interface..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null; then
    sudo raspi-config nonint do_i2c 0 2>/dev/null || warn "Could not auto-enable I2C. Enable manually: sudo raspi-config → Interface → I2C"
fi
ok "I2C enabled"

# -----------------------------------------------
# 4. Install Rust (needed for ZeroClaw)
# -----------------------------------------------
step "Installing Rust toolchain..."
if command -v rustc &>/dev/null; then
    ok "Rust already installed ($(rustc --version))"
else
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    ok "Rust installed ($(rustc --version))"
fi

# Make sure cargo is in PATH for rest of script
export PATH="$HOME/.cargo/bin:$PATH"

# -----------------------------------------------
# 5. Clone and build ZeroClaw
# -----------------------------------------------
step "Setting up ZeroClaw AI agent..."
if [ -f "$HOME/zeroclaw/target/release/zeroclaw" ]; then
    ok "ZeroClaw already built"
else
    if [ -d "$HOME/zeroclaw" ]; then
        cd "$HOME/zeroclaw" && git pull
    else
        git clone https://github.com/theonlyhennygod/zeroclaw.git "$HOME/zeroclaw"
    fi
    cd "$HOME/zeroclaw"
    echo "  Building ZeroClaw (this takes 5-10 minutes on a Pi 5)..."
    cargo build --release 2>&1 | tail -5
    ok "ZeroClaw built"
fi

# -----------------------------------------------
# 6. Create Python virtual environment
# -----------------------------------------------
step "Setting up Python environment..."
if [ -d "$HOME/lab-env" ]; then
    ok "Python venv already exists"
else
    python3 -m venv "$HOME/lab-env"
    ok "Python venv created at ~/lab-env"
fi

# Install Python packages
source "$HOME/lab-env/bin/activate"
pip install --upgrade pip 2>&1 | tail -1
pip install \
    pyserial \
    opencv-python-headless \
    smbus2 \
    requests \
    flask \
    pyyaml \
    2>&1 | tail -3
ok "Python packages installed"
deactivate

# -----------------------------------------------
# 7. Create data directories
# -----------------------------------------------
step "Creating data directories..."
mkdir -p "$HOME/lab-data/camera"
mkdir -p "$HOME/lab-data/sensors"
mkdir -p "$HOME/lab-data/logs"
ok "Data directories created at ~/lab-data/"

# -----------------------------------------------
# 8. Create config file (if not exists)
# -----------------------------------------------
step "Setting up configuration..."
if [ -f "$HOME/lab-config.yaml" ]; then
    ok "Config already exists at ~/lab-config.yaml"
else
    cp "$SCRIPT_DIR/lab-config.example.yaml" "$HOME/lab-config.yaml"
    ok "Config created at ~/lab-config.yaml — EDIT THIS with your settings!"
    warn "Run: nano ~/lab-config.yaml"
fi

# -----------------------------------------------
# 9. Install systemd services
# -----------------------------------------------
step "Installing systemd services..."
for svc in lab-camera lab-sensors lab-bridge lab-zeroclaw; do
    sudo cp "$SCRIPT_DIR/services/systemd/${svc}.service" /etc/systemd/system/
done
sudo systemctl daemon-reload

# Enable all services to start on boot
for svc in lab-camera lab-sensors lab-bridge lab-zeroclaw; do
    sudo systemctl enable "$svc" 2>/dev/null
    ok "Enabled ${svc}"
done

# Start the services
for svc in lab-camera lab-sensors lab-bridge lab-zeroclaw; do
    sudo systemctl restart "$svc" 2>/dev/null || warn "${svc} failed to start (check config)"
done
ok "Services installed and started"

# -----------------------------------------------
# Done!
# -----------------------------------------------
echo ""
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════╗"
echo "║   ✅ Setup Complete!                     ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "📋 What was installed:"
echo "   • System packages (python3, git, camera tools, i2c-tools, etc.)"
echo "   • Rust toolchain + ZeroClaw AI agent"
echo "   • Python venv at ~/lab-env with all dependencies"
echo "   • 4 systemd services (camera, sensors, bridge, zeroclaw)"
echo "   • Config at ~/lab-config.yaml"
echo ""
echo "📝 Next steps:"
echo "   1. Edit your config:    nano ~/lab-config.yaml"
echo "   2. Run the health check: ./check.sh"
echo "   3. Reboot to verify:    sudo reboot"
echo ""
echo "🌐 Lab Bridge API is at:  http://lab-pi.local:5555/status"
echo ""
