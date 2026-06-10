import { loadCurrentStatus, USE_MOCK } from '@/api/dataService'
import { extractReadingValues, mapStatusToDashboard } from '@/api/statusMapper'
import type { SensorDashboardPayload, SensorKey } from '@/types/sensor'

const POLL_INTERVAL_MS = 2000

export { POLL_INTERVAL_MS, USE_MOCK }

export async function fetchSensorDashboard(
  previousValues?: Partial<Record<SensorKey, number>>,
): Promise<SensorDashboardPayload> {
  const status = await loadCurrentStatus()
  return mapStatusToDashboard(status, previousValues)
}

export { extractReadingValues }
