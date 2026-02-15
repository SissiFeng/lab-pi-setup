# 🔬 NeverOT Lab Pi Setup

> **Hey Geneva!** 👋 This guide will walk you through setting up the Raspberry Pi for our self-driving lab. No coding experience needed — just follow each step and copy-paste the commands.

---

## 📖 What Does This Pi Do?

The Raspberry Pi is the "eyes and ears" of our lab bench. It sits next to the OT-2 robot and:

```
┌─────────────────────────────────────────────────────────┐
│                    NeverOT Lab Bench                     │
│                                                         │
│   💻 Laptop (Brain 🧠)          🍓 Raspberry Pi (Eye 👁️) │
│   ├── NeverOT server            ├── 📷 USB Camera       │
│   ├── Nexus (optimization)      ├── 🌡️ pH Sensor        │
│   ├── 🤖 OT-2 (USB)            ├── 🌡️ Temp Sensor      │
│   ├── ⚡ Squidstat (USB)        ├── 🤖 ZeroClaw agent   │
│   └── 🔌 PLC Relays (USB)      └── 🔔 Watchdog         │
│                                         │               │
│          ◄── same WiFi ──►              │               │
│                                         ▼               │
│                              Alerts if laptop goes down │
│                              Sends photos + sensor data │
└─────────────────────────────────────────────────────────┘
```

The **laptop** controls all instruments (OT-2, Squidstat, PLC) via USB.
The **Pi** is an independent monitor — the lab's eyes, ears, and watchdog.

- **📷 Camera** — Takes a photo every 30 seconds so you can check experiments remotely
- **🌡️ Sensors** — Reads pH and temperature every 10 seconds, alerts if something's wrong
- **🤖 ZeroClaw** — Lightweight AI agent that monitors, sends alerts, and does edge processing
- **🔔 Watchdog** — Pings the laptop; if it goes down, the Pi sends you an alert
- **🌐 Web API** — Lets the main server pull data from the Pi over the network

---

## 🛒 Hardware Shopping List

| Item | Specs | Approx. Price |
|------|-------|--------------|
| Raspberry Pi 5 (8GB) | 8GB RAM model | ~$80 |
| USB-C Power Supply | Official Pi 5 supply, 27W / 5.1V 5A | ~$12 |
| microSD Card | 64GB or larger, Class 10 / A2 (e.g. Samsung EVO Select) | ~$12 |
| USB Webcam | Logitech C920 or C270 (1080p, USB-A) | ~$30-70 |
| Micro-HDMI to HDMI cable | For first-time setup (can remove after) | ~$8 |
| USB keyboard + mouse | For first-time setup (can remove after) | borrow any |
| Ethernet cable (optional) | If WiFi is unreliable | ~$5 |
| pH Sensor + ADC board | Atlas Scientific EZO-pH or similar I2C sensor | varies |
| Temperature sensor | DS18B20 or I2C temp sensor | ~$5-10 |

> 💡 **Tip:** You only need the HDMI cable, keyboard, and mouse for the initial setup. After that, everything is done remotely over SSH.

---

## 🚀 Setup Guide (Step by Step)

### Step 1: Flash the SD Card 💾

You need to put the Raspberry Pi operating system onto the SD card.

1. **On your laptop/desktop**, download **Raspberry Pi Imager** from:
   👉 https://www.raspberrypi.com/software/

2. Insert the **microSD card** into your laptop (use an adapter if needed)

3. Open **Raspberry Pi Imager** and:
   - Click **"Choose Device"** → select **Raspberry Pi 5**
   - Click **"Choose OS"** → select **Raspberry Pi OS (64-bit)** (the first/recommended one)
   - Click **"Choose Storage"** → select your SD card

4. **IMPORTANT:** Before clicking Write, click the **⚙️ gear icon** (or "Edit Settings") and set:
   - ✅ **Set hostname:** `lab-pi`
   - ✅ **Enable SSH** → Use password authentication
   - ✅ **Set username:** `pi`
   - ✅ **Set password:** (ask your lab lead for the standard password)
   - ✅ **Configure WiFi:** Enter your lab WiFi name and password
   - ✅ **Set locale:** Your timezone and keyboard layout

5. Click **"Write"** and wait (takes ~5 minutes)

6. When done, eject the SD card safely

### Step 2: First Boot 🔌

1. Insert the SD card into the Pi's slot (on the bottom)
2. Plug in the USB camera, sensors, and any other USB devices
3. Plug in the power cable — the Pi will start automatically
4. Wait about 60-90 seconds for it to boot

> If you connected a monitor + keyboard, you'll see the desktop. But we'll do everything via SSH from now on.

### Step 3: Connect to the Pi via SSH 🖥️

SSH lets you control the Pi from your laptop without a monitor.

**On macOS** — open the **Terminal** app (search for "Terminal" in Spotlight):
```bash
ssh pi@lab-pi.local
```

**On Windows** — open **PowerShell** or **Command Prompt**:
```bash
ssh pi@lab-pi.local
```

- Type `yes` when asked about fingerprint
- Enter the password you set in Step 1
- You should see a command prompt like: `pi@lab-pi:~ $`

> ❌ **Can't connect?** See [Troubleshooting](#-troubleshooting) below.

### Step 4: Download This Repo 📥

Copy-paste this command (all one line):
```bash
git clone https://github.com/theonlyhennygod/lab-pi-setup.git ~/lab-pi-setup && cd ~/lab-pi-setup
```

### Step 5: Run the Setup Script 🛠️

This installs everything automatically. It takes about 15-30 minutes.

```bash
chmod +x setup.sh && ./setup.sh
```

You'll see colored messages telling you what's happening. **Green = good, red = problem.**

☕ Go grab a coffee — this takes a while because it's installing a lot of software.

### Step 6: Edit Your Config ⚙️

```bash
nano ~/lab-config.yaml
```

Update these values (ask your lab lead if unsure):
- `neverot_server` — the IP address of the main NeverOT computer
- `zeroclaw_api_key` — the AI API key
- `lab_name` — your lab bench name

To save: press `Ctrl+O`, then `Enter`, then `Ctrl+X` to exit.

### Step 7: Verify Everything Works ✅

```bash
cd ~/lab-pi-setup && ./check.sh
```

You should see a checklist with ✅ for each item. If anything shows ❌, the script will tell you what to try.

### Step 8: Reboot and Done! 🎉

```bash
sudo reboot
```

Wait 60 seconds, then SSH back in. All services will start automatically on boot.

---

## 🔄 How to Restart / Update Things

### Restart a specific service:
```bash
sudo systemctl restart lab-camera
sudo systemctl restart lab-sensors
sudo systemctl restart lab-bridge
sudo systemctl restart lab-zeroclaw
```

### Check if a service is running:
```bash
sudo systemctl status lab-camera
```

### View logs for a service:
```bash
journalctl -u lab-camera -f
```
(Press `Ctrl+C` to stop watching logs)

### Update everything to the latest version:
```bash
cd ~/lab-pi-setup && ./update.sh
```

### Restart the whole Pi:
```bash
sudo reboot
```

---

## ❓ Troubleshooting

### "I can't SSH / connection refused"
1. Make sure you're on the **same WiFi** as the Pi
2. Try using the IP address instead:
   - Check your router's admin page for the Pi's IP, or
   - Connect a monitor to the Pi and run `hostname -I`
   ```bash
   ssh pi@192.168.1.XXX
   ```
3. Make sure the Pi is powered on (green LED should be blinking)

### "Camera not detected"
1. Unplug and replug the USB camera
2. Check if it shows up:
   ```bash
   v4l2-ctl --list-devices
   ```
3. Try a different USB port
4. Make sure it's a **USB camera**, not a Pi Camera Module (those use a ribbon cable)

### "Sensors not reading"
1. Check I2C is enabled:
   ```bash
   sudo raspi-config
   ```
   Go to → Interface Options → I2C → Enable
2. Check if sensors are detected:
   ```bash
   i2cdetect -y 1
   ```
   You should see addresses (numbers) in the grid

### "ZeroClaw won't start"
1. Check if it's built:
   ```bash
   ls ~/zeroclaw/target/release/zeroclaw
   ```
2. Check the service log:
   ```bash
   journalctl -u lab-zeroclaw -n 50
   ```
3. Make sure `~/lab-config.yaml` has a valid API key

### "Disk space is full"
```bash
# Check disk space
df -h

# Manually clean old camera images
rm -rf ~/lab-data/camera/*.jpg

# Clean apt cache
sudo apt clean
```

### "Everything was working and now it's not"
```bash
# Run the health check first
cd ~/lab-pi-setup && ./check.sh

# Try restarting all services
sudo systemctl restart lab-camera lab-sensors lab-bridge lab-zeroclaw

# Nuclear option: reboot
sudo reboot
```

---

## 📞 Lab Support

If you're stuck, reach out to:

- **Lab Lead:** _[name]_ — _[email/slack]_
- **IT Support:** _[name]_ — _[email/slack]_
- **This repo:** https://github.com/SissiFeng/lab-pi-setup/issues

---

## 📁 What's in This Repo?

```
lab-pi-setup/
├── README.md              ← You are here!
├── setup.sh               ← One-time setup (run once)
├── check.sh               ← Health check (run anytime)
├── update.sh              ← Update everything
├── lab-config.example.yaml ← Config template
├── services/
│   ├── camera_monitor.py  ← Takes photos every 30s
│   ├── sensor_reader.py   ← Reads pH + temperature
│   ├── lab_bridge.py      ← Web API (port 5555)
│   └── systemd/           ← Auto-start service files
│       ├── lab-camera.service
│       ├── lab-sensors.service
│       ├── lab-bridge.service
│       └── lab-zeroclaw.service
└── .gitignore
```
