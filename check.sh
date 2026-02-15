#!/usr/bin/env bash
# ============================================
# ✅ NeverOT Lab Pi — Health Check
# ============================================
# Run anytime to verify everything is working.
# Usage:  ./check.sh
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check_pass() { echo -e "  ${GREEN}✅ $1${NC}"; ((PASS++)); }
check_fail() { echo -e "  ${RED}❌ $1${NC}"; echo -e "     ${YELLOW}Try: $2${NC}"; ((FAIL++)); }

# Load config for server IP
SERVER_IP="192.168.1.100"
if [ -f "$HOME/lab-config.yaml" ]; then
    CONFIGURED_IP=$(grep 'neverot_server' "$HOME/lab-config.yaml" | head -1 | sed 's/.*"\(.*\)".*/\1/' | cut -d: -f1)
    [ -n "$CONFIGURED_IP" ] && SERVER_IP="$CONFIGURED_IP"
fi

echo ""
echo "🔍 NeverOT Lab Pi — Health Check"
echo "================================="
echo ""

# --- Python ---
echo "🐍 Python:"
if command -v python3 &>/dev/null; then
    check_pass "Python3 installed ($(python3 --version 2>&1))"
else
    check_fail "Python3 not found" "sudo apt install python3"
fi

if [ -d "$HOME/lab-env" ] && "$HOME/lab-env/bin/python" --version &>/dev/null; then
    check_pass "Virtual environment works (~/lab-env)"
else
    check_fail "Virtual environment missing or broken" "./setup.sh"
fi

# --- ZeroClaw ---
echo ""
echo "🤖 ZeroClaw:"
if [ -f "$HOME/zeroclaw/target/release/zeroclaw" ]; then
    check_pass "ZeroClaw binary exists"
else
    check_fail "ZeroClaw binary not found" "./setup.sh"
fi

# --- Camera ---
echo ""
echo "📷 Camera:"
if command -v v4l2-ctl &>/dev/null && v4l2-ctl --list-devices 2>/dev/null | grep -q "video"; then
    check_pass "USB camera detected"
elif ls /dev/video* &>/dev/null; then
    check_pass "Video device found ($(ls /dev/video* 2>/dev/null | head -1))"
else
    check_fail "No camera detected" "Plug in USB camera and check: v4l2-ctl --list-devices"
fi

# --- I2C ---
echo ""
echo "🌡️ I2C / Sensors:"
if command -v i2cdetect &>/dev/null; then
    if i2cdetect -y 1 &>/dev/null; then
        check_pass "I2C bus available"
    else
        check_fail "I2C bus not accessible" "sudo raspi-config → Interface Options → I2C → Enable, then reboot"
    fi
else
    check_fail "i2c-tools not installed" "sudo apt install i2c-tools"
fi

# --- Network ---
echo ""
echo "🌐 Network:"
if ping -c 1 -W 2 "$SERVER_IP" &>/dev/null; then
    check_pass "Can reach NeverOT server ($SERVER_IP)"
else
    check_fail "Cannot reach NeverOT server ($SERVER_IP)" "Check WiFi and verify server IP in ~/lab-config.yaml"
fi

if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    check_pass "Internet access works"
else
    check_fail "No internet access" "Check WiFi connection: nmcli d wifi list"
fi

# --- Systemd Services ---
echo ""
echo "⚙️ Services:"
for svc in lab-camera lab-sensors lab-bridge lab-zeroclaw; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        check_pass "$svc is running"
    else
        check_fail "$svc is NOT running" "sudo systemctl restart $svc && journalctl -u $svc -n 20"
    fi
done

# --- Disk Space ---
echo ""
echo "💾 Disk:"
FREE_KB=$(df / | tail -1 | awk '{print $4}')
FREE_GB=$((FREE_KB / 1024 / 1024))
if [ "$FREE_KB" -gt 1048576 ]; then
    check_pass "Disk space OK (${FREE_GB}GB free)"
else
    check_fail "Low disk space (${FREE_GB}GB free, need >1GB)" "sudo apt clean && rm -rf ~/lab-data/camera/*.jpg"
fi

# --- Config ---
echo ""
echo "📄 Config:"
if [ -f "$HOME/lab-config.yaml" ]; then
    check_pass "Config file exists (~/lab-config.yaml)"
else
    check_fail "Config file missing" "cp ~/lab-pi-setup/lab-config.example.yaml ~/lab-config.yaml && nano ~/lab-config.yaml"
fi

# --- Summary ---
echo ""
echo "================================="
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}🎉 All $TOTAL checks passed! Everything looks good.${NC}"
else
    echo -e "${YELLOW}Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC} out of $TOTAL checks"
    echo -e "${YELLOW}Fix the ❌ items above, then run ./check.sh again.${NC}"
fi
echo ""
