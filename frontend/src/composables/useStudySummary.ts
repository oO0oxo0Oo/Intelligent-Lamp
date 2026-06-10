import { onMounted, ref } from 'vue'

import {
  loadCurrentSession,
  loadLatestSummary,
  loadTodaySummary,
} from '@/api/dataService'
import { formatDuration } from '@/api/statusMapper'
import type { StudySession, TodaySummaryPayload } from '@/types/api'

export function useStudySummary() {
  const loading = ref(true)
  const error = ref<string | null>(null)
  const currentSession = ref<StudySession | null>(null)
  const latestSummary = ref<StudySession | null>(null)
  const todaySummary = ref<TodaySummaryPayload | null>(null)

  async function refresh() {
    try {
      const [session, latest, today] = await Promise.all([
        loadCurrentSession(),
        loadLatestSummary(),
        loadTodaySummary(),
      ])
      currentSession.value = session
      latestSummary.value = latest
      todaySummary.value = today
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '学习摘要加载失败'
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
    currentSession,
    latestSummary,
    todaySummary,
    formatDuration,
    refresh,
  }
}
