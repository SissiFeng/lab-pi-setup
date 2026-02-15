#!/usr/bin/env python3
"""
🌡️ Sensor Reader — NeverOT Lab Pi
====================================
Reads pH and temperature sensors via I2C/serial.
Falls back to simulated data if no hardware is detected.

Logs to ~/lab-data/sensors/readings.csv
Runs as a systemd service (lab-sensors).
"""

import os
import sys
import csv
import time
import random
import logging
import datetime
import yaml

# Try to import I2C library
try:
    import smbus2
    HAS_I2C = True
except ImportError:
    HAS_I2C = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ----- Configuration -----

CONFIG_PATH = os.path.expanduser("~/lab-config.yaml")
SENSOR_DIR = os.path.expanduser("~/lab-data/sensors")
LOG_DIR = os.path.expanduser("~/lab-data/logs")
CSV_PATH = os.path.join(SENSOR_DIR, "readings.csv")

# Common I2C addresses for lab sensors
PH_I2C_ADDR = 0x63      # Atlas Scientific EZO-pH default
TEMP_I2C_ADDR = 0x66     # Atlas Scientific EZO-RTD default
I2C_BUS = 1

def load_config():
    defaults = {
        "sensors": {
            "ph_enabled": True,
            "temp_enabled": True,
            "read_interval_seconds": 10,
            "ph_range": [4.0, 10.0],
            "temp_range": [15.0, 45.0],
            "simulate": False,
        },
        "neverot_server": "192.168.1.100:8000",
        "alerts": {"telegram_chat_id": "", "email": ""},
    }
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = yaml.safe_load(f) or {}
        sensors = {**defaults["sensors"], **(cfg.get("sensors") or {})}
        return {
            "sensors": sensors,
            "neverot_server": cfg.get("neverot_server", defaults["neverot_server"]),
            "alerts": {**defaults["alerts"], **(cfg.get("alerts") or {})},
        }
    except FileNotFoundError:
        logging.warning(f"Config not found at {CONFIG_PATH}, using defaults")
        return defaults

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, "sensors.log")),
            logging.StreamHandler(sys.stdout),
        ],
    )

def read_i2c_sensor(bus, addr):
    """Send read command to Atlas Scientific EZO sensor and parse response."""
    try:
        bus.write_byte(addr, 0x52)  # 'R' command = read
        time.sleep(1)  # EZO sensors need ~1s to respond
        raw = bus.read_i2c_block_data(addr, 0x00, 16)
        # First byte is status (1 = success)
        if raw[0] == 1:
            value_str = "".join(chr(b) for b in raw[1:] if b != 0)
            return float(value_str)
    except Exception as e:
        logging.debug(f"I2C read error at 0x{addr:02x}: {e}")
    return None

def read_ph(bus, simulate=False):
    """Read pH value. Returns float or None."""
    if simulate:
        return round(random.uniform(6.5, 7.5), 2)
    if bus is None:
        return None
    return read_i2c_sensor(bus, PH_I2C_ADDR)

def read_temperature(bus, simulate=False):
    """Read temperature in °C. Returns float or None."""
    if simulate:
        return round(random.uniform(22.0, 26.0), 2)
    if bus is None:
        return None
    return read_i2c_sensor(bus, TEMP_I2C_ADDR)

def check_alerts(ph, temp, config):
    """Check if values are outside configured ranges and log warnings."""
    sensor_cfg = config["sensors"]
    alerts = []

    if ph is not None:
        ph_min, ph_max = sensor_cfg["ph_range"]
        if ph < ph_min or ph > ph_max:
            msg = f"⚠️ pH OUT OF RANGE: {ph} (expected {ph_min}-{ph_max})"
            logging.warning(msg)
            alerts.append(msg)

    if temp is not None:
        temp_min, temp_max = sensor_cfg["temp_range"]
        if temp < temp_min or temp > temp_max:
            msg = f"⚠️ Temperature OUT OF RANGE: {temp}°C (expected {temp_min}-{temp_max}°C)"
            logging.warning(msg)
            alerts.append(msg)

    # Send alerts to NeverOT server if configured
    if alerts and HAS_REQUESTS:
        server = config["neverot_server"]
        try:
            requests.post(
                f"http://{server}/api/alerts",
                json={"source": "lab-pi-sensors", "alerts": alerts},
                timeout=5,
            )
        except Exception:
            pass  # Don't crash on alert delivery failure

    return alerts

def write_csv(timestamp, ph, temp):
    """Append a reading to the CSV file."""
    os.makedirs(SENSOR_DIR, exist_ok=True)
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "ph", "temp_c"])
        writer.writerow([timestamp, ph if ph is not None else "", temp if temp is not None else ""])

def main():
    setup_logging()
    logging.info("🌡️ Sensor reader starting...")

    config = load_config()
    sensor_cfg = config["sensors"]
    interval = sensor_cfg["read_interval_seconds"]
    simulate = sensor_cfg.get("simulate", False)

    # Try to open I2C bus
    bus = None
    if HAS_I2C and not simulate:
        try:
            bus = smbus2.SMBus(I2C_BUS)
            logging.info("I2C bus opened")
        except Exception as e:
            logging.warning(f"Cannot open I2C bus: {e}")
            if not simulate:
                logging.info("Falling back to simulated data")
                simulate = True

    if simulate:
        logging.info("Running in SIMULATION mode (no real hardware)")

    logging.info(f"Interval: {interval}s, pH: {sensor_cfg['ph_enabled']}, Temp: {sensor_cfg['temp_enabled']}")

    while True:
        try:
            ts = datetime.datetime.now().isoformat()

            ph = read_ph(bus, simulate) if sensor_cfg["ph_enabled"] else None
            temp = read_temperature(bus, simulate) if sensor_cfg["temp_enabled"] else None

            logging.info(f"pH={ph}, temp={temp}°C")
            write_csv(ts, ph, temp)
            check_alerts(ph, temp, config)

        except Exception as e:
            logging.error(f"Error in sensor loop: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    main()
