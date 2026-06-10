import { onMounted, reactive, ref } from 'vue'

import { SCENE_MODE_LABEL } from '@/constants/labels'
import { loadCurrentStatus, persistLampControl } from '@/api/dataService'
import type { LampControlState, SceneMode } from '@/types/api'

const SCENE_PRESETS: Record<
  SceneMode,
  Pick<LampControlState, 'brightness' | 'color_temperature'>
> = {
  eye_care: { brightness: 72, color_temperature: 4100 },
  reading: { brightness: 85, color_temperature: 4500 },
  focus: { brightness: 78, color_temperature: 5000 },
  night: { brightness: 35, color_temperature: 3000 },
}

export function useLampControl() {
  const loading = ref(true)
  const applying = ref(false)
  const error = ref<string | null>(null)
  const success = ref<string | null>(null)
  const control = reactive<LampControlState>({
    brightness: 72,
    color_temperature: 4100,
    scene_mode: 'eye_care',
  })

  async function refresh() {
    loading.value = true
    try {
      const status = await loadCurrentStatus()
      if (status.lamp_control) {
        Object.assign(control, status.lamp_control)
      }
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '台灯状态读取失败'
    } finally {
      loading.value = false
    }
  }

  async function applyControl(next?: Partial<LampControlState>) {
    if (next) {
      Object.assign(control, next)
    }

    applying.value = true
    success.value = null
    try {
      const saved = await persistLampControl({ ...control })
      Object.assign(control, saved)
      error.value = null
      success.value = '控制指令已下发，设备状态已回显'
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '台灯控制失败'
    } finally {
      applying.value = false
    }
  }

  async function applyScene(scene: SceneMode) {
    await applyControl({
      scene_mode: scene,
      ...SCENE_PRESETS[scene],
    })
  }

  onMounted(() => {
    void refresh()
  })

  return {
    loading,
    applying,
    error,
    success,
    control,
    scenePresets: SCENE_PRESETS,
    sceneLabels: SCENE_MODE_LABEL,
    refresh,
    applyControl,
    applyScene,
  }
}
