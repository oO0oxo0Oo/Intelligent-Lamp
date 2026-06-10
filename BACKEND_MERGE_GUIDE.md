# StudyPilot 后端联调与改进指南

> **文档用途**  
> 前端家长端（`frontend/`）已开发完成，将单独交付。接收方在现有 Flask 后端基础上，按本文档补齐/改造接口，即可与前端联调。  
> **前端无需再改业务页面**；后端改完并关闭 Mock 后即可对接。

---

## 0. 背景与交付物

### 0.1 你收到了什么

| 交付物 | 说明 |
|--------|------|
| `frontend/` | Vue 3 + TypeScript 家长端，含 6 大模块（监测、摘要、事件、配置、控制、历史） |
| 本文档 | 后端需实现的接口契约、改动清单、验证步骤 |

### 0.2 你需要有什么

| 前提 | 说明 |
|------|------|
| 现有 `backend/` | StudyPilot Flask 后端（设备上报、SQLite、基础 status/settings/summary 接口） |
| Python 环境 | 如 `conda activate studypilot`，`python -m backend.app` 可启动 |
| 可选：ESP32 设备 | 无设备时可用 curl 模拟上报 |

### 0.3 联调架构

```
frontend (Vite :5173)  ──proxy /api──▶  backend (Flask :5000)  ◀──  ESP32 设备
         │                                      │
    VITE_USE_MOCK=false                    SQLite + 快照文件
```

**前端联调配置**（`frontend/.env.development`）：

```env
VITE_USE_MOCK=false
VITE_API_BASE=
```

开发时 `VITE_API_BASE` 留空，走 `vite.config.ts` 中 `/api → http://127.0.0.1:5000` 代理。

---

## 1. 前端模块与后端接口对应关系

| 前端模块 | 源文件 | 调用的 API | 后端现状 |
|---------|--------|-----------|---------|
| 实时监测 | `MonitorPanel.vue`、`useSensorDashboard.ts` | `GET /api/status/current`（每 **2 秒**） | ✅ 有，需**扩展字段** |
| 学习摘要 | `StudySummaryPanel.vue` | `GET /api/status/session/current`、`/api/summaries/latest`、`/api/summaries/today` | ✅ 基本有 |
| 事件记录 | `EventTimeline.vue` | `GET /api/status/events` | ✅ 有，需**分页 + snapshot_url** |
| 异常快照 | `EventTimeline.vue` | 事件字段 `snapshot_url` 指向图片 URL | ❌ **需新增** |
| 参数配置 | `SettingsPanel.vue` | `GET/PUT /api/settings` | ✅ 有 |
| 台灯控制 | `LampControlPanel.vue` | `PUT /api/lamp/control` | ❌ **需新增** |
| 历史数据 | `HistoryChartPanel.vue` | `GET /api/status/history?limit=120` | ✅ 有 |

前端类型定义以 **`frontend/src/types/api.ts`** 为准；HTTP 封装在 **`frontend/src/api/client.ts`**。

---

## 2. 统一响应格式（必须遵守）

所有 JSON 接口使用统一封装（与现有 `backend/utils/response.py` 一致）：

**成功：**

```json
{
  "ok": true,
  "...业务字段"
}
```

**失败：**

```json
{
  "ok": false,
  "message": "错误说明"
}
```

HTTP 状态码：成功一般 200；创建可用 201；参数错误 400；未授权 401；未找到 404。

前端在 `client.ts` 中会检查：`response.ok === false` 时抛错。

---

## 3. 接口契约（按前端要求逐项实现）

### 3.1 当前状态 — `GET /api/status/current`

**用途：** 实时监测首页，每 2 秒轮询。

**响应示例：**

```json
{
  "ok": true,
  "telemetry": {
    "device_id": "esp32-study-lamp-01",
    "timestamp": 1717500000,
    "temperature": 25.6,
    "humidity": 48,
    "lux": 326,
    "distance_mm": 620,
    "presence_state": "present",
    "distance_level": "normal",
    "env_label": [],
    "study_state": "studying",
    "study_duration": 1200
  },
  "heartbeat": {
    "device_id": "esp32-study-lamp-01",
    "timestamp": 1717500000,
    "ip": "192.168.1.100",
    "study_state": "studying"
  },
  "latest_event": { "...见 EventRecord" },
  "settings": {
    "distance_warning_mm": 350,
    "distance_presence_mm": 1200,
    "light_low_lux": 150,
    "temperature_high_c": 30,
    "humidity_high_percent": 75,
    "leave_grace_seconds": 15
  },
  "lamp_control": {
    "brightness": 68,
    "color_temperature": 4100,
    "scene_mode": "eye_care"
  }
}
```

**相对原版的改动：**

- 必须增加 **`lamp_control`** 对象（原版没有）。
- `scene_mode` 枚举：`eye_care` | `reading` | `focus` | `night`。

---

### 3.2 事件列表 — `GET /api/status/events`

**用途：** 事件时间线 + 分页。

**Query 参数：**

| 参数 | 说明 |
|------|------|
| `page` | 页码，从 1 开始（**建议实现**） |
| `page_size` | 每页条数（前端 Mock 用 6～8） |
| `limit` | 兼容旧写法；当前 `client.ts` 仅用 `limit` |

**响应示例：**

```json
{
  "ok": true,
  "items": [
    {
      "id": 12,
      "device_id": "esp32-study-lamp-01",
      "event_type": "distance_too_close",
      "level": "warning",
      "message": "Distance is too close",
      "timestamp": 1717500000,
      "presence_state": "present",
      "distance_level": "too_close",
      "study_state": "studying",
      "extra_json": {},
      "snapshot_url": "/api/status/events/12/snapshot.jpg"
    }
  ],
  "total": 24,
  "page": 1,
  "page_size": 6
}
```

**EventRecord 字段说明：**

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 建议 | 事件主键 |
| `event_type` | 是 | 如 `presence_away`、`distance_too_close`、`environment_changed` |
| `level` | 是 | `info` / `warning` |
| `message` | 是 | 展示文案 |
| `timestamp` | 是 | Unix 秒 |
| `snapshot_url` | 行为类异常 | 有快照时填相对路径；无则 `null` |

**前端快照展示规则**（`statusMapper.ts`）：仅对 `presence_away`、`distance_too_close` 且 `snapshot_url` 非空时显示图片。

> **说明：** 当前 `frontend/src/api/client.ts` 的 `fetchEvents` 只传 `limit`，未传 `page`。后端应同时支持 `page/page_size` 与 `limit`；完整分页需后端返回正确 `total`，后续可让前端把 `page` 传给 API。

---

### 3.3 异常快照图片 — `GET /api/status/events/<event_id>/snapshot.jpg`

**用途：** 事件记录中 `<img :src="event.snapshot_url">` 加载。

**响应：** `Content-Type: image/jpeg`，body 为 JPEG 二进制。

**错误：** 无快照时返回 404 + `{ "ok": false, "message": "..." }`。

---

### 3.4 台灯控制 — `PUT /api/lamp/control`

**用途：** 家长端远程调节亮度、色温、模式。

**请求 Body：**

```json
{
  "brightness": 72,
  "color_temperature": 4000,
  "scene_mode": "reading"
}
```

**响应：**

```json
{
  "ok": true,
  "lamp_control": {
    "brightness": 72,
    "color_temperature": 4000,
    "scene_mode": "reading"
  }
}
```

**校验建议：**

- `brightness`：0～100
- `color_temperature`：2700～6500
- `scene_mode`：`eye_care` | `reading` | `focus` | `night`

**可选：** `GET /api/lamp/control` 单独读取当前状态（前端目前通过 `/api/status/current` 获取即可）。

---

### 3.5 参数配置 — `GET /api/settings`、`PUT /api/settings`

**用途：** 阈值配置页。原版已具备，保持即可。

**PUT Body 示例：**

```json
{
  "distance_warning_mm": 350,
  "light_low_lux": 150
}
```

**建议扩展 settings（供快照策略使用，可选）：**

```json
{
  "snapshot_enabled": true,
  "snapshot_event_types": ["distance_too_close", "presence_away"]
}
```

---

### 3.6 历史遥测 — `GET /api/status/history?limit=120`

**用途：** 历史曲线。原版已具备，返回 `{ "ok": true, "items": [ TelemetryRecord, ... ] }`。

---

### 3.7 学习摘要 — 已有接口

| 接口 | 响应要点 |
|------|---------|
| `GET /api/status/session/current` | `{ "session": StudySession \| null }` |
| `GET /api/summaries/latest` | `{ "summary": StudySession \| null }` |
| `GET /api/summaries/today` | `{ sessions, total_duration_seconds, total_warning_count, total_leave_count }` |

StudySession 字段：`id`, `device_id`, `started_at`, `ended_at`, `duration_seconds`, `warning_count`, `leave_count`, `summary_text`, `status`。

---

### 3.8 设备端接口（需配合改动）

| 接口 | 原版 | 需改动 |
|------|------|--------|
| `POST /api/device/telemetry` | ✅ | 保持 |
| `POST /api/device/heartbeat` | ✅ | 保持 |
| `POST /api/device/events` | ✅ | 响应增加 **`event_id`** |
| `POST /api/device/events/<id>/snapshot` | ❌ | **新增**，Body 为 JPEG 二进制 |
| `GET /api/device/config` | ✅ 仅 settings | 响应增加 **`lamp_control`** |

**事件上报响应示例：**

```json
{
  "ok": true,
  "message": "event stored",
  "event_id": 12
}
```

设备需在收到 `event_id` 后，对行为类异常上传快照（见第六节）。

---

## 4. 后端改动总览

### 4.1 改动分类

| 优先级 | 类型 | 文件 | 说明 |
|--------|------|------|------|
| P0 | **新增** | `backend/routes/lamp_api.py` | 台灯控制路由 |
| P0 | **新增** | `backend/services/lamp_service.py` | 读写 `lamp_control` |
| P0 | **修改** | `backend/services/telemetry_service.py` | `get_current_status` 加 `lamp_control` |
| P0 | **修改** | `backend/app.py` | 注册 `lamp_api` |
| P1 | **新增** | `backend/services/snapshot_store.py` | 快照存盘 |
| P1 | **修改** | `backend/services/telemetry_service.py` | `save_event` 返回 id；`get_events_page`；`attach_event_snapshot` |
| P1 | **修改** | `backend/routes/status_api.py` | 事件分页 + 快照图片路由 |
| P1 | **修改** | `backend/routes/device_api.py` | event_id、快照上传、config 加 lamp_control |
| P1 | **修改** | `backend/models/schema.py` | events 表加快照字段 |
| P1 | **SQL** | 见 4.3 | 已有库迁移 |
| P2 | **修改** | `backend/config.py` | `SNAPSHOT_DIR` |
| P2 | **修改** | `backend/services/db.py` | DEFAULT_SETTINGS 扩展 |
| — | **不动** | `settings_api.py`、`summary_api.py`、`camera_api.py` 等 | 保持 |

### 4.2 若仓库内带有参考实现

完整可参考代码在 **`mywork/backend/`**（与本文档同仓库时）：

```powershell
# 在项目根目录执行
Copy-Item -Force mywork/backend/services/lamp_service.py backend/services/
Copy-Item -Force mywork/backend/services/snapshot_store.py backend/services/
Copy-Item -Force mywork/backend/services/telemetry_service.py backend/services/
Copy-Item -Force mywork/backend/routes/lamp_api.py backend/routes/
Copy-Item -Force mywork/backend/routes/status_api.py backend/routes/
Copy-Item -Force mywork/backend/routes/device_api.py backend/routes/
```

再按 **`mywork/backend/patches/`** 内 snippet 合并 `app.py`、`config.py`、`db.py`、`schema.py`，并执行 **`mywork/backend/schema_migration.sql`**。

若无 `mywork/backend`，请按 **第 3 节接口契约** 自行实现。

---

### 4.3 数据库改动

**events 表新增字段：**

```sql
ALTER TABLE events ADD COLUMN snapshot_path TEXT;
ALTER TABLE events ADD COLUMN has_snapshot INTEGER NOT NULL DEFAULT 0;
```

**新建库时** 在 `backend/models/schema.py` 的 `events` 表定义中一并写入上述字段。

**settings 建议默认值（`db.py` DEFAULT_SETTINGS`）：**

```python
"snapshot_enabled": True,
"snapshot_event_types": ["distance_too_close", "presence_away"],
"lamp_control": {
    "brightness": 68,
    "color_temperature": 4100,
    "scene_mode": "eye_care",
},
```

---

## 5. 分步实施建议

### 第一步：台灯控制（P0，前端「控制」页可联调）

1. 新建 `lamp_service.py`：读写 settings 表中的 `lamp_control`。
2. 新建 `lamp_api.py`：`PUT /api/lamp/control`。
3. 修改 `telemetry_service.get_current_status()`：返回 `lamp_control`。
4. 在 `app.py` 注册：`app.register_blueprint(lamp_api, url_prefix="/api/lamp")`。
5. 验证：`PUT /api/lamp/control` 后，`GET /api/status/current` 中数值同步变化。

### 第二步：事件分页（P1，前端「事件」页）

1. 在 `telemetry_service` 实现 `get_events_page(page, page_size)`，返回 `items/total/page/page_size`。
2. 修改 `status_api` 的 `/events`：有 `page` 时分页，否则兼容 `limit`。
3. 验证：返回 JSON 含 `total`，且 `items` 内字段与 3.2 一致。

### 第三步：异常快照（P1，报告/演示重点）

1. 新建 `snapshot_store.py`，快照目录默认 `backend/data/snapshots/`。
2. `save_event()` 返回 `event_id`；新增 `attach_event_snapshot(event_id, jpeg_bytes)`。
3. 设备路由 `POST /api/device/events/<id>/snapshot`。
4. 家长端路由 `GET /api/status/events/<id>/snapshot.jpg`。
5. 列表项中：`has_snapshot=1` 时设置 `snapshot_url="/api/status/events/{id}/snapshot.jpg"`。
6. 仅对 `distance_too_close`、`presence_away` 允许绑快照（环境类事件不上图）。

### 第四步：设备 config（P1，设备拉取台灯目标）

修改 `GET /api/device/config`：

```json
{
  "ok": true,
  "settings": { "...": "..." },
  "lamp_control": { "brightness": 68, "color_temperature": 4100, "scene_mode": "eye_care" }
}
```

---

## 6. 设备端配合（`device/sensor_collector.py`）

后端完成后，ESP32 需配合：

1. **事件 ID**  
   `POST /api/device/events` 后解析 JSON 中的 `event_id`。

2. **上传快照**（行为类异常）  
   对 `distance_too_close`、`presence_away`：  
   `camera.capture()` → `POST /api/device/events/{event_id}/snapshot`（Body 为 JPEG，Header 带 `X-Device-Token`）。

3. **拉取台灯控制（可选）**  
   定期 `GET /api/device/config`，读取 `lamp_control` 执行 PWM 调光。

无设备时可用 curl 模拟事件 + 上传测试图。

---

## 7. 联调步骤（前后端一起跑）

### 7.1 启动后端

```powershell
conda activate studypilot
python -m pip install -r backend/requirements.txt
python -m backend.app
```

确认：`http://127.0.0.1:5000/api/status/current` 可访问。

### 7.2 启动前端

```powershell
cd frontend
npm install
# 确保 .env.development 中 VITE_USE_MOCK=false
npm run dev
```

浏览器打开：`http://localhost:5173`

### 7.3 模块验收

| 页面 | 通过标准 |
|------|---------|
| 实时监测 | 2 秒刷新；显示传感器卡片；设备面板有亮度/色温/模式 |
| 学习摘要 | 有会话/今日统计（需库中有 study_sessions 数据） |
| 事件记录 | 列表有数据；行为类异常可看到快照图 |
| 参数配置 | 修改阈值保存成功，刷新后仍为新值 |
| 台灯控制 | 拖动滑块保存后，监测页亮度/色温更新 |
| 历史数据 | 曲线/列表有历史遥测点 |

---

## 8. 接口验证命令（curl）

```powershell
# 1. 当前状态（必须有 lamp_control）
curl http://127.0.0.1:5000/api/status/current

# 2. 台灯控制
curl -X PUT http://127.0.0.1:5000/api/lamp/control ^
  -H "Content-Type: application/json" ^
  -d "{\"brightness\":72,\"color_temperature\":4000,\"scene_mode\":\"reading\"}"

# 3. 事件列表
curl "http://127.0.0.1:5000/api/status/events?page=1&page_size=6"

# 4. 设备上报事件（Token 与 backend 配置一致，默认 change-me）
curl -X POST http://127.0.0.1:5000/api/device/events ^
  -H "X-Device-Token: change-me" -H "Content-Type: application/json" ^
  -d "{\"device_id\":\"esp32-study-lamp-01\",\"event_type\":\"distance_too_close\",\"level\":\"warning\",\"message\":\"Distance is too close\"}"

# 5. 上传快照（将 {event_id} 换为上一步返回的 id）
curl -X POST http://127.0.0.1:5000/api/device/events/{event_id}/snapshot ^
  -H "X-Device-Token: change-me" -H "Content-Type: image/jpeg" ^
  --data-binary "@test.jpg"

# 6. 查看快照
curl http://127.0.0.1:5000/api/status/events/{event_id}/snapshot.jpg --output out.jpg
```

---

## 9. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 前端仍显示 Mock | `VITE_USE_MOCK=true` | 改为 `false` 并重启 `npm run dev` |
| 接口 404 | 未注册 lamp_api 或路径错误 | 检查 `app.py` 与路由前缀 |
| 控制页保存失败 | 缺少 `PUT /api/lamp/control` | 完成 P0 |
| 事件无图片 | 未实现 snapshot 或未上传 | 完成 P1 + 设备/curl 上传 |
| CORS 错误 | 未走 Vite 代理 | 开发时用 `localhost:5173`，勿直接打开 file:// |
| `ok: false` | 后端 error() 返回 | 看 `message` 字段 |

---

## 10. 附录：核心服务函数清单

便于对照实现进度：

| 文件 | 函数 / 路由 | 作用 |
|------|------------|------|
| `lamp_service.py` | `get_lamp_control()` | 读台灯状态 |
| `lamp_service.py` | `update_lamp_control(payload)` | 写台灯状态 |
| `lamp_api.py` | `PUT /control` | 家长端控制 |
| `snapshot_store.py` | `save_event_snapshot()` | 存 JPEG |
| `snapshot_store.py` | `load_event_snapshot()` | 读 JPEG |
| `telemetry_service.py` | `save_event()` → `event_id` | 事件入库 |
| `telemetry_service.py` | `attach_event_snapshot()` | 绑定快照 |
| `telemetry_service.py` | `get_events_page()` | 分页列表 |
| `telemetry_service.py` | `get_current_status()` | 聚合 + lamp_control |
| `status_api.py` | `GET /events/<id>/snapshot.jpg` | 快照下载 |
| `device_api.py` | `POST /events/<id>/snapshot` | 设备上传 |

---

## 11. 参考文件索引（前端侧）

接手人排查问题时可直接看前端：

| 文件 | 内容 |
|------|------|
| `frontend/src/types/api.ts` | 全部 TypeScript 类型 |
| `frontend/src/api/client.ts` | 所有 fetch URL |
| `frontend/src/api/dataService.ts` | Mock / 真实切换 |
| `frontend/vite.config.ts` | `/api` 代理到 5000 |
| `frontend/.env.example` | 环境变量说明 |

---

**文档版本：** 面向 frontend 交付 + 后端改进  
**维护：** 接口变更时请同步更新本文档与 `frontend/src/types/api.ts`
