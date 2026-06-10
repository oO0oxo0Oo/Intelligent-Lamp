<script setup lang="ts">
import { computed } from 'vue'

import type { HistorySeries } from '@/composables/useHistory'

const props = defineProps<{
  series: HistorySeries
  labels: string[]
}>()

const path = computed(() => {
  const { values, min, max } = props.series
  if (values.length === 0) {
    return ''
  }

  const range = max - min || 1
  const width = 640
  const height = 180
  const step = width / Math.max(values.length - 1, 1)

  return values
    .map((value, index) => {
      const x = index * step
      const y = height - ((value - min) / range) * (height - 20) - 10
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
})

const areaPath = computed(() => {
  if (!path.value) {
    return ''
  }

  return `${path.value} L 640 180 L 0 180 Z`
})
</script>

<template>
  <article class="chart-card">
    <div class="chart-card__head">
      <div>
        <strong>{{ series.label }}</strong>
        <span>近 2 小时趋势</span>
      </div>
      <div class="chart-card__latest">
        <strong :style="{ color: series.color }">{{ series.latest }}</strong>
        <span>{{ series.unit }}</span>
      </div>
    </div>

    <svg viewBox="0 0 640 180" class="chart-card__svg" role="img" :aria-label="`${series.label}趋势图`">
      <defs>
        <linearGradient :id="`fill-${series.key}`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="series.color" stop-opacity="0.28" />
          <stop offset="100%" :stop-color="series.color" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      <path :d="areaPath" :fill="`url(#fill-${series.key})`" />
      <path :d="path" fill="none" :stroke="series.color" stroke-width="3" stroke-linecap="round" />
    </svg>

    <div class="chart-card__axis">
      <span>{{ labels[0] ?? '--:--' }}</span>
      <span>{{ labels[Math.floor(labels.length / 2)] ?? '--:--' }}</span>
      <span>{{ labels[labels.length - 1] ?? '--:--' }}</span>
    </div>
  </article>
</template>
