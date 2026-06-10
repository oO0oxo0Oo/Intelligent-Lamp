import { computed, onMounted, ref } from 'vue'

import { loadHistory } from '@/api/dataService'
import type { TelemetryRecord } from '@/types/api'

export interface HistorySeries {
  key: 'lux' | 'temperature' | 'humidity'
  label: string
  unit: string
  color: string
  values: number[]
  latest: number
  min: number
  max: number
}

export function useHistory() {
  const loading = ref(true)
  const error = ref<string | null>(null)
  const records = ref<TelemetryRecord[]>([])

  const series = computed<HistorySeries[]>(() => {
    const items = records.value
    if (items.length === 0) {
      return []
    }

    const build = (
      key: 'lux' | 'temperature' | 'humidity',
      label: string,
      unit: string,
      color: string,
    ): HistorySeries => {
      const values = items.map((item) => Number(item[key] ?? 0))
      return {
        key,
        label,
        unit,
        color,
        values,
        latest: values[values.length - 1] ?? 0,
        min: Math.min(...values),
        max: Math.max(...values),
      }
    }

    return [
      build('lux', '环境光照', 'lx', '#ff6900'),
      build('temperature', '环境温度', '°C', '#2563eb'),
      build('humidity', '空气湿度', '%', '#059669'),
    ]
  })

  const timeLabels = computed(() =>
    records.value.map((item) => {
      if (!item.timestamp) {
        return '--:--'
      }
      const date = new Date(item.timestamp * 1000)
      return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    }),
  )

  async function refresh() {
    loading.value = true
    try {
      records.value = await loadHistory(120)
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '历史数据加载失败'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void refresh()
  })

  return {
    loading,
    error,
    records,
    series,
    timeLabels,
    refresh,
  }
}
