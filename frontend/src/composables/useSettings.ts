import { onMounted, reactive, ref } from 'vue'

import { loadSettings, persistSettings } from '@/api/dataService'
import type { LampSettings } from '@/types/api'

const DEFAULT_SETTINGS: Required<LampSettings> = {
  distance_warning_mm: 350,
  distance_presence_mm: 1200,
  light_low_lux: 150,
  temperature_high_c: 30,
  humidity_high_percent: 75,
  leave_grace_seconds: 15,
}

export function useSettings() {
  const loading = ref(true)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const success = ref<string | null>(null)
  const form = reactive<LampSettings>({ ...DEFAULT_SETTINGS })

  async function refresh() {
    loading.value = true
    try {
      const settings = await loadSettings()
      Object.assign(form, DEFAULT_SETTINGS, settings)
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '参数读取失败'
    } finally {
      loading.value = false
    }
  }

  function validate(): string | null {
    if ((form.distance_warning_mm ?? 0) <= 0) {
      return '坐姿预警距离必须大于 0'
    }
    if ((form.distance_presence_mm ?? 0) <= (form.distance_warning_mm ?? 0)) {
      return '离桌判定距离应大于坐姿预警距离'
    }
    if ((form.light_low_lux ?? 0) <= 0) {
      return '光照下限必须大于 0'
    }
    if ((form.leave_grace_seconds ?? 0) < 5) {
      return '离桌宽限时间不应小于 5 秒'
    }
    return null
  }

  async function submit() {
    success.value = null
    const validationError = validate()
    if (validationError) {
      error.value = validationError
      return
    }

    saving.value = true
    try {
      const saved = await persistSettings({ ...form })
      Object.assign(form, saved)
      error.value = null
      success.value = '参数已保存，将同步至设备端生效'
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '参数保存失败'
    } finally {
      saving.value = false
    }
  }

  function reset() {
    Object.assign(form, DEFAULT_SETTINGS)
    success.value = null
    error.value = null
  }

  onMounted(() => {
    void refresh()
  })

  return {
    loading,
    saving,
    error,
    success,
    form,
    refresh,
    submit,
    reset,
  }
}
