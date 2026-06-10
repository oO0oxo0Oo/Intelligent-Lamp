import { onMounted, onUnmounted, ref } from 'vue'

import {
  extractReadingValues,
  fetchSensorDashboard,
  POLL_INTERVAL_MS,
  USE_MOCK,
} from '@/api/sensorService'
import type { SensorDashboardPayload, SensorKey } from '@/types/sensor'

export function useSensorDashboard() {
  const dashboard = ref<SensorDashboardPayload>()
  const loading = ref(true)
  const error = ref<string | null>(null)
  const dataSource = ref<'mock' | 'live'>(USE_MOCK ? 'mock' : 'live')

  let timer: ReturnType<typeof setInterval> | null = null
  let previousValues: Partial<Record<SensorKey, number>> | undefined

  async function refresh() {
    try {
      const nextDashboard = await fetchSensorDashboard(previousValues)
      dashboard.value = nextDashboard
      previousValues = extractReadingValues(nextDashboard)
      error.value = null
      dataSource.value = USE_MOCK ? 'mock' : 'live'
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '数据刷新失败'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void refresh()
    timer = setInterval(() => {
      void refresh()
    }, POLL_INTERVAL_MS)
  })

  onUnmounted(() => {
    if (timer) {
      clearInterval(timer)
    }
  })

  return {
    dashboard,
    loading,
    error,
    dataSource,
    refresh,
  }
}
