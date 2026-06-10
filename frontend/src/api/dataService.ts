import * as client from '@/api/client'
import {
  getMockCurrentSession,
  getMockEvents,
  getMockHistory,
  getMockLatestSummary,
  getMockTodaySummary,
  updateMockLampControl,
  updateMockSettings,
} from '@/api/mockData'
import { getMockCurrentStatus } from '@/api/mockData'
import type {
  CurrentStatusPayload,
  EventRecord,
  LampControlState,
  LampSettings,
  StudySession,
  TelemetryRecord,
  TodaySummaryPayload,
} from '@/types/api'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

export { USE_MOCK }

export async function loadCurrentStatus(): Promise<CurrentStatusPayload> {
  if (USE_MOCK) {
    return getMockCurrentStatus()
  }

  const response = await client.fetchCurrentStatus()
  return {
    telemetry: response.telemetry,
    heartbeat: response.heartbeat,
    latest_event: response.latest_event,
    settings: response.settings,
    lamp_control: response.lamp_control,
  }
}

export async function loadEvents(page = 1, pageSize = 8): Promise<{
  items: EventRecord[]
  total: number
  page: number
  page_size: number
}> {
  if (USE_MOCK) {
    return getMockEvents(page, pageSize)
  }

  const response = await client.fetchEvents(pageSize)
  return {
    items: response.items,
    total: response.items.length,
    page: 1,
    page_size: pageSize,
  }
}

export async function loadHistory(limit = 120): Promise<TelemetryRecord[]> {
  if (USE_MOCK) {
    return getMockHistory(limit)
  }

  const response = await client.fetchHistory(limit)
  return response.items
}

export async function loadCurrentSession(): Promise<StudySession | null> {
  if (USE_MOCK) {
    return getMockCurrentSession()
  }

  const response = await client.fetchCurrentSession()
  return response.session
}

export async function loadLatestSummary(): Promise<StudySession | null> {
  if (USE_MOCK) {
    return getMockLatestSummary()
  }

  const response = await client.fetchLatestSummary()
  return response.summary
}

export async function loadTodaySummary(): Promise<TodaySummaryPayload> {
  if (USE_MOCK) {
    return getMockTodaySummary()
  }

  const response = await client.fetchTodaySummary()
  return {
    sessions: response.sessions,
    total_duration_seconds: response.total_duration_seconds,
    total_warning_count: response.total_warning_count,
    total_leave_count: response.total_leave_count,
  }
}

export async function loadSettings(): Promise<LampSettings> {
  if (USE_MOCK) {
    return getMockCurrentStatus().settings
  }

  const response = await client.fetchSettings()
  return response.settings
}

export async function persistSettings(settings: LampSettings): Promise<LampSettings> {
  if (USE_MOCK) {
    return updateMockSettings(settings)
  }

  const response = await client.saveSettings(settings)
  return response.settings
}

export async function persistLampControl(control: LampControlState): Promise<LampControlState> {
  if (USE_MOCK) {
    return updateMockLampControl(control)
  }

  await client.saveLampControl(control)
  return control
}
