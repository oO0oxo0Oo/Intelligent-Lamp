"""模拟 ESP32 设备向 Flask 后端持续上报遥测与心跳。

用法（项目根目录，另开终端）：
    python scripts/device_simulator.py

可选参数：
    --base-url http://127.0.0.1:5000
    --token change-me
    --telemetry-interval 1
    --heartbeat-interval 5

配合前后端联调：
    1. 终端 A：python -m backend.app
    2. 终端 B：python scripts/device_simulator.py
    3. 终端 C：cd frontend && npm run dev
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request

DEVICE_ID = "esp32-study-lamp-01"


class DeviceSimulator:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "X-Device-Token": token,
        }
        self.tick = 0
        self.session_started_at = int(time.time()) - 600
        self.smoothed = {
            "temperature": 25.4,
            "humidity": 51.0,
            "lux": 342.0,
            "distance_mm": 580.0,
        }
        self.baseline = dict(self.smoothed)
        self.presence_state = "present"
        self.distance_level = "normal"
        self.study_state = "studying"
        self.env_label: list[str] = []

    def _post(self, path: str, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=self.headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status not in (200, 201):
                raise RuntimeError(f"HTTP {resp.status}")

    @staticmethod
    def _smooth_walk(current: float, baseline: float, max_step: float, pull: float = 0.04) -> float:
        noise = (random.random() - 0.5) * 2 * max_step
        reversion = (baseline - current) * pull
        return current + noise + reversion

    def _advance_sensors(self) -> None:
        self.tick += 1
        cycle = self.tick % 180

        if cycle == 150:
            self.distance_level = "too_close"
            self.study_state = "warning"
        elif cycle == 153:
            self.distance_level = "normal"
            self.study_state = "studying"

        if 70 <= cycle <= 85:
            self.env_label = ["light_low"]
            self.baseline["lux"] = 135
        elif cycle > 85:
            self.env_label = []
            self.baseline["lux"] = 342

        self.smoothed["temperature"] = round(
            self._smooth_walk(self.smoothed["temperature"], self.baseline["temperature"], 0.04),
            1,
        )
        if random.random() < 0.22:
            self.smoothed["humidity"] += -1 if random.random() < 0.5 else 1
            self.smoothed["humidity"] = max(
                self.baseline["humidity"] - 2,
                min(self.baseline["humidity"] + 2, self.smoothed["humidity"]),
            )
        self.smoothed["lux"] = round(self._smooth_walk(self.smoothed["lux"], self.baseline["lux"], 1.2, 0.06))
        target = 315 if self.distance_level == "too_close" else self.baseline["distance_mm"]
        max_step = 14 if self.distance_level == "too_close" else 22
        pull = 0.05 if self.distance_level == "too_close" else 0.02
        distance = self._smooth_walk(self.smoothed["distance_mm"], target, max_step, pull)
        if random.random() < 0.18:
            distance += (random.random() - 0.5) * 56
        self.smoothed["distance_mm"] = round(max(290, min(820, distance)))

        if cycle < 150 or cycle > 153:
            warning, presence = 350, 1200
            if self.smoothed["distance_mm"] <= warning:
                self.distance_level = "too_close"
                if self.study_state != "idle":
                    self.study_state = "warning"
            elif self.smoothed["distance_mm"] >= presence:
                self.distance_level = "far"
            else:
                self.distance_level = "normal"
                if self.study_state == "warning":
                    self.study_state = "studying"

    def telemetry_payload(self) -> dict:
        now = int(time.time())
        return {
            "device_id": DEVICE_ID,
            "timestamp": now,
            "temperature": self.smoothed["temperature"],
            "humidity": self.smoothed["humidity"],
            "lux": self.smoothed["lux"],
            "distance_mm": int(self.smoothed["distance_mm"]),
            "temperature_timestamp": now,
            "humidity_timestamp": now,
            "lux_timestamp": now,
            "distance_timestamp": now,
            "presence_state": self.presence_state,
            "distance_level": self.distance_level,
            "env_label": list(self.env_label),
            "study_state": self.study_state,
            "study_duration": max(0, now - self.session_started_at),
            "session_started_at": self.session_started_at,
        }

    def heartbeat_payload(self) -> dict:
        now = int(time.time())
        return {
            "device_id": DEVICE_ID,
            "timestamp": now,
            "ip": "192.168.1.108",
            "study_state": self.study_state,
        }

    def upload_telemetry(self) -> None:
        self._advance_sensors()
        self._post("/api/device/telemetry", self.telemetry_payload())

    def upload_heartbeat(self) -> None:
        self._post("/api/device/heartbeat", self.heartbeat_payload())


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate ESP32 device telemetry uploads")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--token", default="change-me")
    parser.add_argument("--telemetry-interval", type=float, default=1.0)
    parser.add_argument("--heartbeat-interval", type=float, default=5.0)
    args = parser.parse_args()

    sim = DeviceSimulator(args.base_url, args.token)
    last_telemetry = 0.0
    last_heartbeat = 0.0

    print(f"Device simulator → {args.base_url}  (Ctrl+C 停止)")
    print(f"  telemetry every {args.telemetry_interval}s, heartbeat every {args.heartbeat_interval}s")

    try:
        while True:
            now = time.monotonic()
            if now - last_telemetry >= args.telemetry_interval:
                try:
                    sim.upload_telemetry()
                    payload = sim.telemetry_payload()
                    print(
                        f"[telemetry] T={payload['temperature']}°C H={payload['humidity']}% "
                        f"lux={payload['lux']} dist={payload['distance_mm']}mm "
                        f"state={payload['study_state']}"
                    )
                except urllib.error.URLError as exc:
                    print(f"[telemetry] failed: {exc}", file=sys.stderr)
                last_telemetry = now

            if now - last_heartbeat >= args.heartbeat_interval:
                try:
                    sim.upload_heartbeat()
                    print("[heartbeat] ok")
                except urllib.error.URLError as exc:
                    print(f"[heartbeat] failed: {exc}", file=sys.stderr)
                last_heartbeat = now

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
