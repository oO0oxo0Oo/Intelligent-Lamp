<script setup lang="ts">
import { APP_TABS, type AppTab } from '@/types/navigation'

defineProps<{
  active: AppTab
}>()

defineEmits<{
  change: [tab: AppTab]
}>()
</script>

<template>
  <nav class="app-nav">
    <button
      v-for="tab in APP_TABS"
      :key="tab.id"
      type="button"
      class="app-nav__item"
      :class="{ 'app-nav__item--active': active === tab.id }"
      @click="$emit('change', tab.id)"
    >
      <strong>{{ tab.label }}</strong>
      <span>{{ tab.desc }}</span>
    </button>
  </nav>
</template>
