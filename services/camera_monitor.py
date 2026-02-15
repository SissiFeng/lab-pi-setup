#!/usr/bin/env python3
"""
📷 Camera Monitor — NeverOT Lab Pi
===================================
Captures a frame from the USB camera every N seconds,
saves it with a timestamp, and cleans up old images.

Runs as a systemd service (lab-camera).
"""

import os
import sys
import time
import glob
import logging
import datetime
import yaml

# Try OpenCV for USB camera capture
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ----- Configuration -----

CONFIG_PATH = os.path.expanduser("~/lab-config.yaml")
CAMERA_DIR = os.path.expanduser("~/lab-data/camera")
LOG_DIR = os.path.expanduser("~/lab-data/logs")

def load_config():
    """Load settings from lab-config.yaml, with sensible defaults."""
    defaults = {
        "camera": {
            "device": "/dev/video0",
            "interval_seconds": 30,
            "keep_hours": 24,
            "upload_to_server": False,
        },
        "neverot_server": "192.168.1.100:8000",
    }
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = yaml.safe_load(f) or {}
        # Merge with defaults
        cam = {**defaults["camera"], **(cfg.get("camera") or {})}
        return {
            "camera": cam,
            "neverot_server": cfg.get("neverot_server", defaults["neverot_server"]),
        }
    except FileNotFoundError:
        logging.warning(f"Config not found at {CONFIG_PATH}, using defaults")
        return defaults

def setup_logging():
    """Set up logging to file and stdout."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, "camera.log")),
            logging.StreamHandler(sys.stdout),
        ],
    )

def capture_frame(device_path):
    """Capture a single frame from the USB camera. Returns image bytes (JPEG) or None."""
    if not HAS_CV2:
        logging.error("opencv-python-headless not installed. Try: pip install opencv-python-headless")
        return None

    # Extract device index from path like /dev/video0 → 0
    try:
        dev_index = int(device_path.replace("/dev/video", ""))
    except ValueError:
        dev_index = 0

    cap = cv2.VideoCapture(dev_index)
    if not cap.isOpened():
        logging.error(f"Cannot open camera at {device_path}")
        return None

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        logging.error("Failed to capture frame")
        return None

    # Encode as JPEG
    success, buf = cv2.imencode(".jpg", frame)
    if not success:
        logging.error("Failed to encode frame as JPEG")
        return None

    return buf.tobytes()

def save_frame(image_bytes):
    """Save JPEG bytes to the camera directory with a timestamp filename."""
    os.makedirs(CAMERA_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(CAMERA_DIR, f"{ts}.jpg")
    with open(path, "wb") as f:
        f.write(image_bytes)
    logging.info(f"Saved frame: {path} ({len(image_bytes)} bytes)")
    return path

def upload_frame(image_path, server):
    """POST the image to the NeverOT server (optional)."""
    if not HAS_REQUESTS:
        return
    url = f"http://{server}/api/camera/upload"
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(url, files={"image": f}, timeout=10)
        if resp.ok:
            logging.info(f"Uploaded to server: {resp.status_code}")
        else:
            logging.warning(f"Server returned {resp.status_code}")
    except Exception as e:
        logging.warning(f"Upload failed: {e}")

def cleanup_old_images(keep_hours):
    """Delete images older than keep_hours."""
    cutoff = time.time() - (keep_hours * 3600)
    for path in glob.glob(os.path.join(CAMERA_DIR, "*.jpg")):
        if os.path.getmtime(path) < cutoff:
            os.remove(path)
            logging.info(f"Cleaned up old image: {path}")

def main():
    setup_logging()
    logging.info("📷 Camera monitor starting...")

    config = load_config()
    cam_cfg = config["camera"]
    device = cam_cfg["device"]
    interval = cam_cfg["interval_seconds"]
    keep_hours = cam_cfg["keep_hours"]
    upload = cam_cfg.get("upload_to_server", False)
    server = config["neverot_server"]

    logging.info(f"Device: {device}, Interval: {interval}s, Keep: {keep_hours}h")

    while True:
        try:
            image_bytes = capture_frame(device)
            if image_bytes:
                path = save_frame(image_bytes)
                if upload:
                    upload_frame(path, server)
            cleanup_old_images(keep_hours)
        except Exception as e:
            logging.error(f"Error in capture loop: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    main()
