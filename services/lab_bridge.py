#!/usr/bin/env python3
"""
🔗 Lab Bridge API — NeverOT Lab Pi
=====================================
Lightweight Flask API that exposes Pi data to the NeverOT server.

Endpoints:
  GET  /status           — Overall Pi health
  GET  /camera/latest    — Latest camera frame (JPEG)
  GET  /sensors/latest   — Latest sensor reading (JSON)
  GET  /sensors/history  — CSV of recent readings (?hours=24)
  POST /alert            — Receive alert from server

Runs on port 5555 as a systemd service (lab-bridge).
"""

import os
import csv
import glob
import time
import shutil
import logging
import datetime
import subprocess
import yaml
from flask import Flask, jsonify, send_file, request, Response

# ----- Configuration -----

CONFIG_PATH = os.path.expanduser("~/lab-config.yaml")
CAMERA_DIR = os.path.expanduser("~/lab-data/camera")
SENSOR_CSV = os.path.expanduser("~/lab-data/sensors/readings.csv")
LOG_DIR = os.path.expanduser("~/lab-data/logs")

app = Flask(__name__)

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

# ----- Helper Functions -----

def get_uptime():
    """Get system uptime as a string."""
    try:
        with open("/proc/uptime", "r") as f:
            secs = float(f.readline().split()[0])
        hours = int(secs // 3600)
        mins = int((secs % 3600) // 60)
        return f"{hours}h {mins}m"
    except Exception:
        return "unknown"

def get_disk_free_gb():
    """Get free disk space in GB."""
    try:
        total, used, free = shutil.disk_usage("/")
        return round(free / (1024 ** 3), 1)
    except Exception:
        return -1

def is_service_running(name):
    """Check if a systemd service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False

def get_latest_image_path():
    """Get the path to the most recent camera image."""
    images = sorted(glob.glob(os.path.join(CAMERA_DIR, "*.jpg")))
    return images[-1] if images else None

def get_latest_sensor_reading():
    """Get the last line of the sensor CSV as a dict."""
    try:
        with open(SENSOR_CSV, "r") as f:
            rows = list(csv.DictReader(f))
        if rows:
            return rows[-1]
    except FileNotFoundError:
        pass
    return None

# ----- Routes -----

@app.route("/status")
def status():
    """Overall Pi health status."""
    return jsonify({
        "lab_pi": True,
        "timestamp": datetime.datetime.now().isoformat(),
        "uptime": get_uptime(),
        "disk_free_gb": get_disk_free_gb(),
        "services": {
            "lab-camera": is_service_running("lab-camera"),
            "lab-sensors": is_service_running("lab-sensors"),
            "lab-bridge": True,  # We're running right now!
            "lab-zeroclaw": is_service_running("lab-zeroclaw"),
        },
        "latest_image": get_latest_image_path() is not None,
        "latest_sensor": get_latest_sensor_reading(),
    })

@app.route("/camera/latest")
def camera_latest():
    """Return the latest camera frame as JPEG."""
    path = get_latest_image_path()
    if path and os.path.exists(path):
        return send_file(path, mimetype="image/jpeg")
    return jsonify({"error": "No camera images found"}), 404

@app.route("/sensors/latest")
def sensors_latest():
    """Return the latest sensor reading as JSON."""
    reading = get_latest_sensor_reading()
    if reading:
        return jsonify(reading)
    return jsonify({"error": "No sensor readings found"}), 404

@app.route("/sensors/history")
def sensors_history():
    """Return sensor readings as CSV. Query param: ?hours=24"""
    hours = request.args.get("hours", 24, type=int)
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

    try:
        with open(SENSOR_CSV, "r") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                try:
                    ts = datetime.datetime.fromisoformat(row["timestamp"])
                    if ts >= cutoff:
                        rows.append(row)
                except (ValueError, KeyError):
                    continue

        # Return as CSV
        if not rows:
            return Response("timestamp,ph,temp_c\n", mimetype="text/csv")

        lines = ["timestamp,ph,temp_c"]
        for r in rows:
            lines.append(f"{r.get('timestamp','')},{r.get('ph','')},{r.get('temp_c','')}")
        return Response("\n".join(lines) + "\n", mimetype="text/csv")

    except FileNotFoundError:
        return Response("timestamp,ph,temp_c\n", mimetype="text/csv")

@app.route("/alert", methods=["POST"])
def receive_alert():
    """Receive an alert from the NeverOT server."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "Unknown alert")
    logging.warning(f"🔔 Alert received from server: {message}")

    # Log alert to file
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "alerts.log"), "a") as f:
        ts = datetime.datetime.now().isoformat()
        f.write(f"{ts} | {message}\n")

    return jsonify({"status": "received", "message": message})

# ----- Main -----

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("🔗 Lab Bridge API starting on port 5555...")
    app.run(host="0.0.0.0", port=5555, debug=False)
