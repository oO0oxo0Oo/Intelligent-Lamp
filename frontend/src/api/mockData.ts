import type { CurrentStatusPayload } from '@/types/api'

import {
  advanceMockTelemetry,
  getMockHeartbeat,
  getMockLatestEvent,
  getMockState,
} from '@/api/mockState'

export function getMockCurrentStatus(): CurrentStatusPayload {
  const { settings, lampControl } = getMockState()

  return {
    telemetry: advanceMockTelemetry(),
    heartbeat: getMockHeartbeat(),
    latest_event: getMockLatestEvent(),
    settings: { ...settings },
    lamp_control: { ...lampControl },
  }
}

export {
  getMockCurrentSession,
  getMockEvents,
  getMockHistory,
  getMockLatestSummary,
  getMockState,
  getMockTodaySummary,
  resetMockState,
  SCENE_MODE_LABEL,
  updateMockLampControl,
  updateMockSettings,
} from '@/api/mockState'
