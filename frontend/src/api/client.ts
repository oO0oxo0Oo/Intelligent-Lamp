import type {
  CurrentStatusResponse,
  EventsResponse,
  HistoryResponse,
  LatestSummaryResponse,
  LampControlState,
  LampSettings,
  SessionResponse,
  SettingsResponse,
  TodaySummaryResponse,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`请求失败 (${response.status})`)
  }

  const payload = (await response.json()) as T & { ok?: boolean; message?: string }
  if (payload.ok === false) {
    throw new Error(payload.message ?? '接口返回异常')
  }

  return payload
}

export async function fetchCurrentStatus(): Promise<CurrentStatusResponse> {
  return parseJson(await fetch(`${API_BASE}/api/status/current`))
}

export async function fetchEvents(limit = 50): Promise<EventsResponse> {
  return parseJson(await fetch(`${API_BASE}/api/status/events?limit=${limit}`))
}

export async function fetchHistory(limit = 120): Promise<HistoryResponse> {
  return parseJson(await fetch(`${API_BASE}/api/status/history?limit=${limit}`))
}

export async function fetchCurrentSession(): Promise<SessionResponse> {
  return parseJson(await fetch(`${API_BASE}/api/status/session/current`))
}

export async function fetchLatestSummary(): Promise<LatestSummaryResponse> {
  return parseJson(await fetch(`${API_BASE}/api/summaries/latest`))
}

export async function fetchTodaySummary(): Promise<TodaySummaryResponse> {
  return parseJson(await fetch(`${API_BASE}/api/summaries/today`))
}

export async function fetchSettings(): Promise<SettingsResponse> {
  return parseJson(await fetch(`${API_BASE}/api/settings`))
}

export async function saveSettings(settings: LampSettings): Promise<SettingsResponse> {
  return parseJson(
    await fetch(`${API_BASE}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    }),
  )
}

export async function saveLampControl(control: LampControlState): Promise<{ ok: boolean }> {
  return parseJson(
    await fetch(`${API_BASE}/api/lamp/control`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(control),
    }),
  )
}
