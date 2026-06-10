"""后端联调扩展测试（边界、鉴权、数据链路）。

运行（项目根目录）：
    python -m tests.integration_extended

在 integration_smoke 主路径之外，额外测试：

1. 设备鉴权
   - POST /api/device/telemetry 无 Token → 401
   - 错误 Token → 401

2. 设备上报链路
   - POST /api/device/telemetry  → current / history 有真实数据
   - POST /api/device/heartbeat  → current 反映 ip、study_state
   - env_label 序列化为数组

3. 参数校验
   - POST /api/device/events 缺 device_id / event_type → 400
   - PUT  /api/lamp/control 非法色温、非法 scene_mode、空 body → 400
   - PUT  /api/settings 带 lamp_control 脏字段 → 被过滤，不影响台灯

4. 快照边界
   - presence_away 事件可上传快照
   - 空 body → 400；不存在的 event_id → 404
   - latest_event 在绑快照后带 snapshot_url

5. 事件分页
   - page=2 与 page=1 无重复
   - limit 模式 total 等于库内真实总数

6. 设备 config 同步
   - 修改 settings 后 GET /api/device/config 阈值已更新

建议：改完 backend 后先跑 smoke，再跑 extended；两者均通过再开前端联调。
"""

import sys
import time

from backend.app import create_app


def fail(msg):
    raise AssertionError(msg)


def main():
    app = create_app()
    c = app.test_client()
    h = {"X-Device-Token": "change-me"}
    device = "esp32-study-lamp-01"
    now = int(time.time())

    # --- device auth ---
    r = c.post("/api/device/telemetry", json={"device_id": device})
    if r.status_code != 401:
        fail(f"telemetry without token should 401, got {r.status_code}")

    r = c.post("/api/device/telemetry", headers={"X-Device-Token": "bad"}, json={"device_id": device})
    if r.status_code != 401:
        fail("telemetry bad token should 401")

    # --- telemetry + heartbeat shape ---
    tele = {
        "device_id": device,
        "timestamp": now,
        "temperature": 25.5,
        "humidity": 48.0,
        "lux": 320.0,
        "distance_mm": 600,
        "presence_state": "present",
        "distance_level": "normal",
        "env_label": ["normal"],
        "study_state": "studying",
        "study_duration": 300,
        "session_started_at": now - 300,
    }
    r = c.post("/api/device/telemetry", headers=h, json=tele)
    if r.status_code != 201 or not r.get_json().get("ok"):
        fail(f"telemetry post failed: {r.status_code} {r.get_data(as_text=True)}")

    r = c.post(
        "/api/device/heartbeat",
        headers=h,
        json={"device_id": device, "timestamp": now, "ip": "192.168.1.10", "study_state": "studying"},
    )
    if r.status_code != 201:
        fail("heartbeat post failed")

    cur = c.get("/api/status/current").get_json()
    if cur["telemetry"] is None:
        fail("current telemetry still null after upload")
    if not isinstance(cur["telemetry"].get("env_label"), list):
        fail(f"env_label should be list, got {cur['telemetry'].get('env_label')}")
    if cur["heartbeat"] is None or cur["heartbeat"].get("ip") != "192.168.1.10":
        fail("heartbeat not reflected in current status")

    hist = c.get("/api/status/history?limit=5").get_json()
    if not hist.get("items") or hist["items"][-1].get("lux") != 320.0:
        fail("history missing latest telemetry point")

    # --- event validation ---
    r = c.post("/api/device/events", headers=h, json={"device_id": device})
    if r.status_code != 400:
        fail("event without event_type should 400")

    r = c.post("/api/device/events", headers=h, json={"event_type": "x"})
    if r.status_code != 400:
        fail("event without device_id should 400")

    # --- lamp validation ---
    r = c.put("/api/lamp/control", json={"color_temperature": 9999})
    if r.status_code != 400:
        fail("invalid color_temperature should 400")

    r = c.put("/api/lamp/control", json={"scene_mode": "invalid"})
    if r.status_code != 400:
        fail("invalid scene_mode should 400")

    r = c.put("/api/lamp/control", json={})
    if r.status_code != 400:
        fail("empty lamp payload should 400")

    # --- settings filter on PUT ---
    r = c.put("/api/settings", json={"lamp_control": {"brightness": 1}, "distance_warning_mm": 340})
    saved = r.get_json()
    if saved["settings"].get("distance_warning_mm") != 340:
        fail("settings threshold update failed")
    if "lamp_control" in saved["settings"]:
        fail("settings response leaked lamp_control")
    if c.get("/api/status/current").get_json()["lamp_control"]["brightness"] == 1:
        fail("lamp_control should not change via settings PUT")

    # --- presence_away snapshot ---
    ev = c.post(
        "/api/device/events",
        headers=h,
        json={
            "device_id": device,
            "event_type": "presence_away",
            "level": "warning",
            "message": "User left desk",
        },
    ).get_json()
    away_id = ev["event_id"]
    r = c.post(f"/api/device/events/{away_id}/snapshot", headers=h, data=b"\xff\xd8\xff\xe0" + b"x" * 20)
    if r.status_code != 201:
        fail(f"presence_away snapshot failed: {r.status_code}")

    # --- pagination page 2 ---
    for i in range(8):
        c.post(
            "/api/device/events",
            headers=h,
            json={"device_id": device, "event_type": "presence_present", "level": "info", "message": f"p{i}"},
        )
    p1 = c.get("/api/status/events?page=1&page_size=6").get_json()
    p2 = c.get("/api/status/events?page=2&page_size=6").get_json()
    if p1["total"] < 7:
        fail(f"expected enough events for page2, total={p1['total']}")
    if len(p1["items"]) != 6 or len(p2["items"]) < 1:
        fail("pagination page sizes wrong")
    ids1 = {x["id"] for x in p1["items"]}
    ids2 = {x["id"] for x in p2["items"]}
    if ids1 & ids2:
        fail("page1 and page2 overlap")

    # --- limit mode total should match full count ---
    lim = c.get("/api/status/events?limit=3").get_json()
    full_total = c.get("/api/status/events?page=1&page_size=3").get_json()["total"]
    if lim["total"] != full_total:
        fail(f"limit mode total={lim['total']} != full total={full_total}")
    if len(lim["items"]) > 3:
        fail("limit mode returned too many items")

    # --- snapshot empty body ---
    r = c.post(f"/api/device/events/{away_id}/snapshot", headers=h, data=b"")
    if r.status_code != 400:
        fail(f"empty snapshot body should 400, got {r.status_code}")

    # --- nonexistent event snapshot upload ---
    r = c.post("/api/device/events/999999/snapshot", headers=h, data=b"jpeg")
    if r.status_code != 404:
        fail("snapshot for missing event should 404")

    # --- latest_event snapshot_url when latest has snapshot ---
    c.post(
        "/api/device/events",
        headers=h,
        json={"device_id": device, "event_type": "distance_too_close", "level": "warning", "message": "close"},
    )
    close_id = c.get("/api/status/events?limit=1").get_json()["items"][0]["id"]
    c.post(f"/api/device/events/{close_id}/snapshot", headers=h, data=b"\xff\xd8\xff\xe0" + b"y" * 20)
    latest = c.get("/api/status/current").get_json()["latest_event"]
    if latest.get("id") != close_id:
        fail("latest event mismatch")
    if latest.get("snapshot_url") != f"/api/status/events/{close_id}/snapshot.jpg":
        fail(f"latest_event missing snapshot_url: {latest}")

    # --- device config sync ---
    cfg = c.get("/api/device/config", headers=h).get_json()
    if cfg["settings"]["distance_warning_mm"] != 340:
        fail("device config settings stale")

    print("integration_extended: ALL PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"integration_extended: FAILED - {exc}", file=sys.stderr)
        raise SystemExit(1)
