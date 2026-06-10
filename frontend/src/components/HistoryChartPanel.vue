<script setup lang="ts">
import TrendChart from '@/components/TrendChart.vue'
import { useHistory } from '@/composables/useHistory'

const { loading, error, series, timeLabels } = useHistory()
</script>

<template>
  <div class="panel-stack">
    <section class="content-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">History</p>
          <h2>环境指标历史趋势</h2>
          <p class="section-desc">
            基于近 120 条遥测记录，展示光照、温度与湿度的长期变化，辅助评估学习环境稳定性。
          </p>
        </div>
      </div>

      <section v-if="loading" class="loading-card">正在加载历史数据...</section>
      <section v-else-if="error" class="loading-card loading-card--error">{{ error }}</section>

      <div v-else class="chart-grid">
        <TrendChart
          v-for="item in series"
          :key="item.key"
          :series="item"
          :labels="timeLabels"
        />
      </div>
    </section>
  </div>
</template>
