function formatTs(ts) {
  if (!ts) return "--";
  return new Date(ts * 1000).toLocaleString("zh-CN");
}

function formatDuration(seconds) {
  if (seconds == null) return "--";
  const total = Math.max(0, Number(seconds) || 0);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}时 ${m}分 ${s}秒`;
  return `${m}分 ${s}秒`;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function applyStatus(data) {
  const telemetry = data.telemetry || {};
  const heartbeat = data.heartbeat || {};
  const latestEvent = data.latest_event || {};

  const deviceOnlineEl = document.getElementById("device-online");
  const studyStateEl = document.getElementById("study-state");

  const heartbeatTs = heartbeat.timestamp || 0;
  const online = heartbeatTs && Date.now() / 1000 - heartbeatTs < 15;

  deviceOnlineEl.textContent = online ? "设备在线" : "设备离线";
  deviceOnlineEl.className = `status-chip ${online ? "" : "offline"}`.trim();

  const studyState = telemetry.study_state || heartbeat.study_state || "unknown";
  studyStateEl.textContent = `学习状态：${studyState}`;
  studyStateEl.className = `status-chip ${studyState === "warning" ? "warning" : ""}`.trim();

  setText("last-updated", `最近更新：${formatTs(telemetry.timestamp || heartbeatTs)}`);
  setText("env-label", (telemetry.env_label || ["--"]).join(", "));
  setText("temperature", telemetry.temperature != null ? `${telemetry.temperature} ℃` : "--");
  setText("humidity", telemetry.humidity != null ? `${telemetry.humidity} %` : "--");
  setText("lux", telemetry.lux != null ? `${telemetry.lux} lux` : "--");
  setText("distance", telemetry.distance_mm != null ? `${telemetry.distance_mm} mm` : "--");
  setText("presence-state", `在位：${telemetry.presence_state || "--"}`);
  setText("study-mode", telemetry.study_state || "--");
  setText("distance-level", telemetry.distance_level || "--");
  setText("study-duration", formatDuration(telemetry.study_duration));
  setText("session-started", formatTs(telemetry.session_started_at));

  if (latestEvent.message) {
    setText("camera-meta", `最近事件：${latestEvent.message}`);
  }
}

function applyEvents(data) {
  const container = document.getElementById("event-list");
  const items = data.items || [];

  if (!container) return;

  if (!items.length) {
    container.innerHTML = '<div class="event-item"><div class="row"><strong>暂无事件</strong></div></div>';
    return;
  }

  container.innerHTML = items
    .map(
      (item) => `
        <div class="event-item ${item.level === "warning" ? "warning" : ""}">
          <div class="row">
            <strong>${item.message}</strong>
            <span class="event-time">${formatTs(item.timestamp)}</span>
          </div>
          <div class="event-time">${item.event_type} / ${item.study_state || "unknown"}</div>
        </div>
      `
    )
    .join("");
}

function applyTodaySummary(data) {
  setText("today-duration", formatDuration(data.total_duration_seconds || 0));
  setText("today-warnings", `${data.total_warning_count || 0}`);
  setText("today-leaves", `${data.total_leave_count || 0}`);
  setText("today-sessions", `${(data.sessions || []).length}`);
}

function applyLatestSummary(data) {
  const summary = data.summary;
  setText("latest-summary", summary?.summary_text || "暂无摘要");
}

function applySettings(data) {
  const settings = data.settings || {};
  const form = document.getElementById("settings-form");
  if (!form) return;

  Object.keys(settings).forEach((key) => {
    if (form.elements[key]) {
      form.elements[key].value = settings[key];
    }
  });
}

async function refreshAll() {
  try {
    const [status, events, today, latestSummary, settings, cameraMeta] = await Promise.all([
      api.getCurrentStatus(),
      api.getEvents(),
      api.getTodaySummary(),
      api.getLatestSummary(),
      api.getSettings(),
      api.getCameraMeta(),
    ]);

    if (status.ok) applyStatus(status);
    if (events.ok) applyEvents(events);
    if (today.ok) applyTodaySummary(today);
    if (latestSummary.ok) applyLatestSummary(latestSummary);
    if (settings.ok) applySettings(settings);

    if (cameraMeta.ok) {
      setText(
        "camera-meta",
        cameraMeta.has_frame ? `最近视频帧：${formatTs(cameraMeta.timestamp)}` : "等待视频帧"
      );
    }
  } catch (error) {
    console.error("Dashboard refresh failed:", error);
  }
}

document.getElementById("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {};

  Array.from(form.elements).forEach((item) => {
    if (item.name) {
      payload[item.name] = Number(item.value);
    }
  });

  const result = await api.saveSettings(payload);
  setText(
    "settings-status",
    result.ok ? "配置已保存，设备将在下次配置轮询时自动同步。" : (result.message || "保存失败")
  );

  if (result.ok) {
    applySettings(result);
  }
});

refreshAll();
setInterval(refreshAll, 2000);
