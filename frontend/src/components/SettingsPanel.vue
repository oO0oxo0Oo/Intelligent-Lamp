<script setup lang="ts">
import { useSettings } from '@/composables/useSettings'

const { loading, saving, error, success, form, submit, reset } = useSettings()

const fields = [
  {
    key: 'distance_warning_mm' as const,
    label: '坐姿预警距离',
    unit: 'mm',
    hint: '低于该距离判定为坐姿过近',
  },
  {
    key: 'distance_presence_mm' as const,
    label: '离桌判定距离',
    unit: 'mm',
    hint: '超过该距离开始离桌宽限计时',
  },
  {
    key: 'light_low_lux' as const,
    label: '环境光照下限',
    unit: 'lx',
    hint: '低于该值触发环境偏暗提醒',
  },
  {
    key: 'temperature_high_c' as const,
    label: '温度上限',
    unit: '°C',
    hint: '超过该值触发高温提醒',
  },
  {
    key: 'humidity_high_percent' as const,
    label: '湿度上限',
    unit: '%',
    hint: '超过该值触发高湿提醒',
  },
  {
    key: 'leave_grace_seconds' as const,
    label: '离桌宽限时间',
    unit: '秒',
    hint: '离桌后等待多久判定为真正离桌',
  },
]
</script>

<template>
  <div class="panel-stack">
    <section class="content-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">Settings</p>
          <h2>系统参数配置</h2>
          <p class="section-desc">
            统一前端展示、后端存储与设备执行规则，保存后将同步至设备端生效。
          </p>
        </div>
      </div>

      <section v-if="loading" class="loading-card">正在读取参数配置...</section>

      <form v-else class="settings-form" @submit.prevent="submit">
        <div class="settings-grid">
          <label v-for="field in fields" :key="field.key" class="settings-field">
            <span>{{ field.label }}</span>
            <div class="settings-field__input">
              <input v-model.number="form[field.key]" type="number" min="1" step="1" />
              <em>{{ field.unit }}</em>
            </div>
            <small>{{ field.hint }}</small>
          </label>
        </div>

        <div v-if="error" class="form-message form-message--error">{{ error }}</div>
        <div v-if="success" class="form-message form-message--success">{{ success }}</div>

        <div class="form-actions">
          <button type="button" class="button-secondary" @click="reset">恢复默认</button>
          <button type="submit" :disabled="saving">
            {{ saving ? '保存中...' : '保存并同步设备' }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>
