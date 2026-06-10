import { computed, onMounted, ref } from 'vue'

import { loadEvents } from '@/api/dataService'
import type { EventRecord } from '@/types/api'

const PAGE_SIZE = 6

export function useEvents() {
  const loading = ref(true)
  const error = ref<string | null>(null)
  const events = ref<EventRecord[]>([])
  const page = ref(1)
  const total = ref(0)

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

  async function refresh() {
    loading.value = true
    try {
      const response = await loadEvents(page.value, PAGE_SIZE)
      events.value = response.items
      total.value = response.total
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '事件记录加载失败'
    } finally {
      loading.value = false
    }
  }

  async function goToPage(nextPage: number) {
    if (nextPage < 1 || nextPage > totalPages.value) {
      return
    }

    page.value = nextPage
    await refresh()
  }

  onMounted(() => {
    void refresh()
  })

  return {
    loading,
    error,
    events,
    page,
    total,
    totalPages,
    refresh,
    goToPage,
  }
}
