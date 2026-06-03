const api = {
  getCurrentStatus() {
    return fetch("/api/status/current").then((r) => r.json());
  },
  getEvents(limit = 12) {
    return fetch(`/api/status/events?limit=${limit}`).then((r) => r.json());
  },
  getTodaySummary() {
    return fetch("/api/summaries/today").then((r) => r.json());
  },
  getLatestSummary() {
    return fetch("/api/summaries/latest").then((r) => r.json());
  },
  getSettings() {
    return fetch("/api/settings").then((r) => r.json());
  },
  saveSettings(payload) {
    return fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((r) => r.json());
  },
  getCameraMeta() {
    return fetch("/api/camera/latest").then((r) => r.json());
  },
};

