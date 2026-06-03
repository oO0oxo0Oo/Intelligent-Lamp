"""
sensor_collector.py - ESP32-S3 sensor collector with active WiFi telemetry.

Behavior:
- AHT20 temperature and humidity sampling every 30s
- BH1750 light sampling every 10s
- VL53L0X distance sampling every 1s
- Telemetry upload every 1s by default
- Heartbeat upload every 5s by default
- Immediate event upload on state changes
"""

import time

try:
    import ujson as json
except ImportError:
    import json

from machine import Pin, SoftI2C

from http_client import get_json, post_json
from net_utils import ensure_wifi, wifi_connected

# ===========================
# I2C Bus (shared by 3 sensors)
# ===========================
I2C_SCL = Pin(1)
I2C_SDA = Pin(2)
I2C_FREQ = 100000

# ===========================
# Sampling Intervals (seconds)
# ===========================
INTERVAL_TEMP_HUMID = 30
INTERVAL_LIGHT = 10
INTERVAL_DISTANCE = 1

sensor_state = {
    "temperature": None,
    "humidity": None,
    "lux": None,
    "distance_mm": None,
    "temperature_timestamp": 0,
    "humidity_timestamp": 0,
    "lux_timestamp": 0,
    "distance_timestamp": 0,
    "presence_state": "unknown",
    "distance_level": "unknown",
    "env_label": [],
    "study_state": "idle",
    "study_duration": 0,
    "session_started_at": 0,
    "last_update_at": 0,
}

runtime_config = {
    "distance_warning_mm": 350,
    "distance_presence_mm": 1200,
    "light_low_lux": 150,
    "temperature_high_c": 30,
    "humidity_high_percent": 75,
    "leave_grace_seconds": 15,
}

_last_temp_read = 0
_last_light_read = 0
_last_distance_read = 0
_last_telemetry_at = 0
_last_heartbeat_at = 0
_last_config_refresh_at = 0

aht_sensor = None
bh1750_sensor = None
tof_sensor = None

current_session = {
    "active": False,
    "started_at": 0,
    "last_present_at": 0,
    "warning_count": 0,
    "leave_count": 0,
}

last_flags = {
    "presence_state": None,
    "distance_level": None,
    "env_label_key": "",
}

device_config = {}
current_ip = None


def connect_wifi(config):
    return ensure_wifi(config)


def init_sensors():
    global aht_sensor, bh1750_sensor, tof_sensor

    i2c = SoftI2C(scl=I2C_SCL, sda=I2C_SDA, freq=I2C_FREQ)
    print("I2C bus ready (SCL=GPIO1, SDA=GPIO2)")

    devices = i2c.scan()
    dev_str = ",".join([hex(d) for d in devices])
    print("I2C devices: [{}]".format(dev_str))

    if 0x38 in devices:
        try:
            import ahtx0

            aht_sensor = ahtx0.AHT20(i2c)
            print("AHT20 OK (0x38)")
        except Exception as e:
            print("AHT20 init failed:", e)
    else:
        print("AHT20 (0x38) not found")

    if 0x23 in devices:
        try:
            from bh1750 import BH1750

            bh1750_sensor = BH1750(0x23, i2c)
            print("BH1750 OK (0x23)")
        except Exception as e:
            print("BH1750 init failed:", e)
    else:
        print("BH1750 (0x23) not found")

    if 0x29 in devices:
        try:
            import VL53L0X

            tof_sensor = VL53L0X.VL53L0X(i2c)
            tof_sensor.start()
            print("VL53L0X OK (0x29)")
        except Exception as e:
            print("VL53L0X init failed:", e)
    else:
        print("VL53L0X (0x29) not found")


def read_temperature_humidity(now):
    if aht_sensor is None:
        return False
    try:
        sensor_state["temperature"] = round(aht_sensor.temperature, 1)
        sensor_state["humidity"] = round(aht_sensor.relative_humidity, 1)
        sensor_state["temperature_timestamp"] = int(now)
        sensor_state["humidity_timestamp"] = int(now)
        return True
    except Exception as e:
        print("AHT20 read error:", e)
        return False


def read_light(now):
    if bh1750_sensor is None:
        return False
    try:
        sensor_state["lux"] = round(bh1750_sensor.measurement, 1)
        sensor_state["lux_timestamp"] = int(now)
        return True
    except Exception as e:
        print("BH1750 read error:", e)
        return False


def read_distance(now):
    if tof_sensor is None:
        return False
    try:
        dist = tof_sensor.read()
        if 0 < dist < 2000:
            sensor_state["distance_mm"] = int(dist)
            sensor_state["distance_timestamp"] = int(now)
            return True
        return False
    except Exception as e:
        print("VL53L0X read error:", e)
        return False


def update_sensors(now):
    global _last_temp_read, _last_light_read, _last_distance_read

    if now - _last_temp_read >= INTERVAL_TEMP_HUMID:
        if read_temperature_humidity(now):
            _last_temp_read = now

    if now - _last_light_read >= INTERVAL_LIGHT:
        if read_light(now):
            _last_light_read = now

    if now - _last_distance_read >= INTERVAL_DISTANCE:
        if read_distance(now):
            _last_distance_read = now


def classify_distance(distance_mm):
    if distance_mm is None:
        return "unknown", "unknown"

    presence_mm = int(runtime_config.get("distance_presence_mm", 1200))
    warning_mm = int(runtime_config.get("distance_warning_mm", 350))

    if distance_mm <= warning_mm:
        return "present", "too_close"
    if distance_mm <= presence_mm:
        return "present", "normal"
    return "away", "far"


def build_env_label():
    labels = []

    lux = sensor_state["lux"]
    temperature = sensor_state["temperature"]
    humidity = sensor_state["humidity"]

    if lux is not None and lux < float(runtime_config.get("light_low_lux", 150)):
        labels.append("too_dark")
    if temperature is not None and temperature > float(runtime_config.get("temperature_high_c", 30)):
        labels.append("too_hot")
    if humidity is not None and humidity > float(runtime_config.get("humidity_high_percent", 75)):
        labels.append("too_humid")

    return labels or ["normal"]


def update_state_machine(now):
    presence_state, distance_level = classify_distance(sensor_state["distance_mm"])
    sensor_state["presence_state"] = presence_state
    sensor_state["distance_level"] = distance_level
    sensor_state["env_label"] = build_env_label()

    if presence_state == "present":
        if not current_session["active"]:
            current_session["active"] = True
            current_session["started_at"] = int(now)
            current_session["warning_count"] = 0
            current_session["leave_count"] = 0
            post_event("study_started", "info", "Study session started", now)

        current_session["last_present_at"] = int(now)
        sensor_state["session_started_at"] = current_session["started_at"]
        sensor_state["study_duration"] = int(now) - current_session["started_at"]
    else:
        leave_grace_seconds = int(runtime_config.get("leave_grace_seconds", 15))
        if current_session["active"] and current_session["last_present_at"]:
            away_seconds = int(now) - current_session["last_present_at"]
            if away_seconds >= leave_grace_seconds:
                duration = sensor_state["study_duration"]
                post_event(
                    "study_finished",
                    "info",
                    "Study session finished",
                    now,
                    {"study_duration": duration},
                )
                current_session["active"] = False
                current_session["started_at"] = 0
                current_session["last_present_at"] = 0
                sensor_state["session_started_at"] = 0
                sensor_state["study_duration"] = 0

    if not current_session["active"]:
        if presence_state == "away":
            sensor_state["study_state"] = "idle"
        else:
            sensor_state["study_state"] = "idle"
    else:
        if distance_level == "too_close" or "normal" not in sensor_state["env_label"]:
            sensor_state["study_state"] = "warning"
        else:
            sensor_state["study_state"] = "studying"

    sensor_state["last_update_at"] = int(now)
    detect_flag_changes(now)


def detect_flag_changes(now):
    env_label_key = ",".join(sensor_state["env_label"])

    if last_flags["presence_state"] != sensor_state["presence_state"]:
        if sensor_state["presence_state"] == "away":
            current_session["leave_count"] += 1
            post_event("presence_away", "warning", "User left desk", now)
        elif sensor_state["presence_state"] == "present":
            post_event("presence_present", "info", "User at desk", now)
        last_flags["presence_state"] = sensor_state["presence_state"]

    if last_flags["distance_level"] != sensor_state["distance_level"]:
        if sensor_state["distance_level"] == "too_close":
            current_session["warning_count"] += 1
            post_event("distance_too_close", "warning", "Distance is too close", now)
        last_flags["distance_level"] = sensor_state["distance_level"]

    if last_flags["env_label_key"] != env_label_key:
        if env_label_key != "normal":
            post_event(
                "environment_changed",
                "warning",
                "Environment needs attention",
                now,
                {"env_label": sensor_state["env_label"]},
            )
        last_flags["env_label_key"] = env_label_key


def post_event(event_type, level, message, now, extra=None):
    payload = {
        "device_id": device_config["device_id"],
        "timestamp": int(now),
        "event_type": event_type,
        "level": level,
        "message": message,
        "study_state": sensor_state["study_state"],
        "presence_state": sensor_state["presence_state"],
        "distance_level": sensor_state["distance_level"],
    }
    if extra:
        payload["extra"] = extra

    try:
        status, _ = post_json(device_config, "/api/device/events", payload)
        print("Event uploaded:", event_type, status)
    except Exception as exc:
        print("Event upload failed:", event_type, exc)


def telemetry_payload():
    return {
        "device_id": device_config["device_id"],
        "timestamp": int(time.time()),
        "temperature": sensor_state["temperature"],
        "humidity": sensor_state["humidity"],
        "lux": sensor_state["lux"],
        "distance_mm": sensor_state["distance_mm"],
        "temperature_timestamp": sensor_state["temperature_timestamp"],
        "humidity_timestamp": sensor_state["humidity_timestamp"],
        "lux_timestamp": sensor_state["lux_timestamp"],
        "distance_timestamp": sensor_state["distance_timestamp"],
        "presence_state": sensor_state["presence_state"],
        "distance_level": sensor_state["distance_level"],
        "env_label": sensor_state["env_label"],
        "study_state": sensor_state["study_state"],
        "study_duration": sensor_state["study_duration"],
        "session_started_at": sensor_state["session_started_at"],
    }


def upload_telemetry(now):
    payload = telemetry_payload()
    status, _ = post_json(device_config, "/api/device/telemetry", payload)
    print("Telemetry uploaded:", status)
    return status


def upload_heartbeat(now):
    payload = {
        "device_id": device_config["device_id"],
        "timestamp": int(now),
        "ip": current_ip,
        "study_state": sensor_state["study_state"],
    }
    status, _ = post_json(device_config, "/api/device/heartbeat", payload)
    print("Heartbeat uploaded:", status)
    return status


def refresh_runtime_config(now):
    global runtime_config
    response = get_json(device_config, "/api/device/config")
    if response and "settings" in response:
        runtime_config.update(response["settings"])
        print("Runtime config updated:", json.dumps(runtime_config))
    else:
        print("Runtime config refresh skipped")


def run(config):
    global _last_telemetry_at, _last_heartbeat_at, _last_config_refresh_at
    global device_config, current_ip

    device_config = config
    current_ip = connect_wifi(config)
    if current_ip is None:
        print("WiFi failed, halt.")
        return

    init_sensors()

    now = time.time()
    read_temperature_humidity(now)
    read_light(now)
    read_distance(now)
    update_state_machine(now)

    print("Initial data:", json.dumps(telemetry_payload()))

    while True:
        now = time.time()

        try:
            if not wifi_connected():
                current_ip = connect_wifi(config)
                if current_ip is None:
                    time.sleep(1)
                    continue

            update_sensors(now)
            update_state_machine(now)

            telemetry_interval = int(config.get("telemetry_interval_seconds", 1))
            if now - _last_telemetry_at >= telemetry_interval:
                try:
                    upload_telemetry(now)
                    _last_telemetry_at = now
                except Exception as exc:
                    print("Telemetry upload failed:", exc)

            heartbeat_interval = int(config.get("heartbeat_interval_seconds", 5))
            if now - _last_heartbeat_at >= heartbeat_interval:
                try:
                    upload_heartbeat(now)
                    _last_heartbeat_at = now
                except Exception as exc:
                    print("Heartbeat upload failed:", exc)

            config_refresh_seconds = int(config.get("config_refresh_seconds", 60))
            if now - _last_config_refresh_at >= config_refresh_seconds:
                try:
                    refresh_runtime_config(now)
                    _last_config_refresh_at = now
                except Exception as exc:
                    print("Runtime config refresh failed:", exc)

            time.sleep_ms(100)
        except Exception as exc:
            print("Collector loop error:", exc)
            time.sleep(1)


def main():
    from config_loader import load_config

    run(load_config())


if __name__ == "__main__":
    main()
