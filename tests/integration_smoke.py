"""后端联调冒烟测试（主路径 happy path）。

运行（项目根目录）：
    python -m tests.integration_smoke

测试范围 — 对应前端 6 大模块能否调通：

1. 实时监测  GET /api/status/current
   - 响应含 telemetry / heartbeat / latest_event / settings / lamp_control
   - settings 仅含 6 个阈值字段，不含 lamp_control

2. 台灯控制  PUT /api/lamp/control
   - 写入亮度/色温/模式后，current 与 device config 同步
   - 亮度越界返回 400

3. 参数配置  GET/PUT /api/settings
   - 只读写阈值字段，不泄露 lamp_control / snapshot 相关配置

4. 事件记录  GET /api/status/events
   - limit 与 page/page_size 两种模式
   - 行为类事件带 snapshot_url，环境类事件不带

5. 异常快照
   - POST /api/device/events → 返回 event_id
   - POST /api/device/events/<id>/snapshot（行为类）
   - GET  /api/status/events/<id>/snapshot.jpg
   - 环境类事件拒绝绑快照（404）

6. 历史数据  GET /api/status/history?limit=N

7. 学习摘要  GET /api/status/session/current
              GET /api/summaries/latest
              GET /api/summaries/today

8. 设备 config  GET /api/device/config（settings + lamp_control）

未覆盖：设备 telemetry/heartbeat 上报、鉴权细节、分页第 2 页等（见 integration_extended.py）。
"""

import sys

from backend.app import create_app


def assert_ok(name, response, expected_status=200):
    if response.status_code != expected_status:
        raise AssertionError(f"{name}: HTTP {response.status_code} body={response.get_data(as_text=True)}")
    payload = response.get_json()
    if not payload or payload.get("ok") is not True:
        raise AssertionError(f"{name}: bad payload {payload}")
    return payload


def assert_error(name, response, expected_status):
    if response.status_code != expected_status:
        raise AssertionError(f"{name}: expected HTTP {expected_status}, got {response.status_code}")
    payload = response.get_json()
    if payload.get("ok") is not False:
        raise AssertionError(f"{name}: expected ok=false, got {payload}")


def main():
    app = create_app()
    client = app.test_client()
    headers = {"X-Device-Token": "change-me"}

    current = assert_ok("GET /api/status/current", client.get("/api/status/current"))
    for key in ("telemetry", "heartbeat", "latest_event", "settings", "lamp_control"):
        if key not in current:
            raise AssertionError(f"current status missing {key}")
    for key in ("distance_warning_mm", "leave_grace_seconds"):
        if key not in current["settings"]:
            raise AssertionError(f"settings missing threshold key {key}")
    if "lamp_control" in current["settings"]:
        raise AssertionError("settings should not include lamp_control")
    if current["lamp_control"]["scene_mode"] not in {"eye_care", "reading", "focus", "night"}:
        raise AssertionError("invalid default scene_mode")

    lamp = assert_ok(
        "PUT /api/lamp/control",
        client.put(
            "/api/lamp/control",
            json={"brightness": 55, "color_temperature": 3800, "scene_mode": "focus"},
        ),
    )
    if lamp["lamp_control"]["brightness"] != 55:
        raise AssertionError("lamp control not persisted")

    current2 = assert_ok("GET /api/status/current after lamp update", client.get("/api/status/current"))
    if current2["lamp_control"]["brightness"] != 55:
        raise AssertionError("current status lamp_control not synced")

    assert_error(
        "PUT /api/lamp/control invalid brightness",
        client.put("/api/lamp/control", json={"brightness": 150}),
        400,
    )

    settings = assert_ok("GET /api/settings", client.get("/api/settings"))
    threshold_keys = {
        "distance_warning_mm",
        "distance_presence_mm",
        "light_low_lux",
        "temperature_high_c",
        "humidity_high_percent",
        "leave_grace_seconds",
    }
    extra = set(settings["settings"].keys()) - threshold_keys
    if extra:
        raise AssertionError(f"GET /api/settings leaked non-threshold keys: {sorted(extra)}")

    saved = assert_ok(
        "PUT /api/settings",
        client.put("/api/settings", json={"distance_warning_mm": 360}),
    )
    if saved["settings"]["distance_warning_mm"] != 360:
        raise AssertionError("settings update failed")

    event = assert_ok(
        "POST /api/device/events",
        client.post(
            "/api/device/events",
            headers=headers,
            json={
                "device_id": "esp32-study-lamp-01",
                "event_type": "distance_too_close",
                "level": "warning",
                "message": "Distance is too close",
            },
        ),
        201,
    )
    event_id = event.get("event_id")
    if not event_id:
        raise AssertionError("event_id missing in device event response")

    env_event = assert_ok(
        "POST environment event",
        client.post(
            "/api/device/events",
            headers=headers,
            json={
                "device_id": "esp32-study-lamp-01",
                "event_type": "environment_changed",
                "level": "warning",
                "message": "Environment needs attention",
            },
        ),
        201,
    )

    env_event_id = env_event.get("event_id")
    assert_error(
        "POST snapshot for environment event",
        client.post(
            f"/api/device/events/{env_event_id}/snapshot",
            headers=headers,
            data=b"jpeg",
        ),
        404,
    )

    snap = assert_ok(
        "POST behavior snapshot",
        client.post(
            f"/api/device/events/{event_id}/snapshot",
            headers=headers,
            data=b"\xff\xd8\xff\xe0" + b"\x00" * 64,
        ),
        201,
    )
    if snap.get("message") != "snapshot stored":
        raise AssertionError("unexpected snapshot response")

    events_limit = assert_ok("GET /api/status/events?limit=5", client.get("/api/status/events?limit=5"))
    if "total" not in events_limit or "items" not in events_limit:
        raise AssertionError("events limit response missing pagination fields")
    behavior_item = next((item for item in events_limit["items"] if item.get("id") == event_id), None)
    if behavior_item is None:
        raise AssertionError("behavior event missing from events list")
    if behavior_item.get("snapshot_url") != f"/api/status/events/{event_id}/snapshot.jpg":
        raise AssertionError(f"unexpected snapshot_url: {behavior_item.get('snapshot_url')}")

    env_item = next((item for item in events_limit["items"] if item.get("event_type") == "environment_changed"), None)
    if env_item and env_item.get("snapshot_url"):
        raise AssertionError("environment event should not expose snapshot_url")

    page = assert_ok("GET /api/status/events?page=1&page_size=6", client.get("/api/status/events?page=1&page_size=6"))
    if page["page"] != 1 or page["page_size"] != 6:
        raise AssertionError("pagination metadata wrong")
    if page["total"] < len(page["items"]):
        raise AssertionError("total should be >= page items")

    snap_resp = client.get(f"/api/status/events/{event_id}/snapshot.jpg")
    if snap_resp.status_code != 200 or snap_resp.mimetype != "image/jpeg":
        raise AssertionError("snapshot download failed")
    if len(snap_resp.data) < 10:
        raise AssertionError("snapshot body too small")

    assert_error(
        "GET missing snapshot",
        client.get("/api/status/events/99999/snapshot.jpg"),
        404,
    )

    history = assert_ok("GET /api/status/history", client.get("/api/status/history?limit=10"))
    if "items" not in history:
        raise AssertionError("history missing items")

    session = assert_ok("GET /api/status/session/current", client.get("/api/status/session/current"))
    if "session" not in session:
        raise AssertionError("session response invalid")

    latest = assert_ok("GET /api/summaries/latest", client.get("/api/summaries/latest"))
    if "summary" not in latest:
        raise AssertionError("latest summary response invalid")

    today = assert_ok("GET /api/summaries/today", client.get("/api/summaries/today"))
    for key in ("sessions", "total_duration_seconds", "total_warning_count", "total_leave_count"):
        if key not in today:
            raise AssertionError(f"today summary missing {key}")

    config = assert_ok("GET /api/device/config", client.get("/api/device/config", headers=headers))
    if "settings" not in config or "lamp_control" not in config:
        raise AssertionError("device config incomplete")
    if config["lamp_control"]["brightness"] != 55:
        raise AssertionError("device config lamp_control stale")

    print("integration_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"integration_smoke: FAILED - {exc}", file=sys.stderr)
        raise SystemExit(1)
