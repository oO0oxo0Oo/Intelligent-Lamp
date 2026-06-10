import type {
  EventRecord,
  LampControlState,
  LampSettings,
  StudySession,
  TelemetryRecord,
} from '@/types/api'

import { SCENE_MODE_LABEL } from '@/constants/labels'

const DEVICE_ID = 'esp32-study-lamp-01'

export interface MockRuntimeState {
  settings: LampSettings
  lampControl: LampControlState
  sessions: StudySession[]
  events: EventRecord[]
  telemetryBaseline: {
    temperature: number
    humidity: number
    lux: number
    distance_mm: number
  }
  sessionStartedAt: number
  studyDurationSeconds: number
  presenceState: 'present' | 'away'
  distanceLevel: 'normal' | 'too_close' | 'far'
  studyState: 'studying' | 'warning' | 'idle'
  envLabels: string[]
  tick: number
  smoothed: {
    temperature: number
    humidity: number
    lux: number
    distance_mm: number
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** 带均值回归的平滑随机游走，模拟真实传感器缓慢漂移 */
function smoothWalk(current: number, baseline: number, maxStep: number, pull = 0.04): number {
  const noise = (Math.random() - 0.5) * 2 * maxStep
  const reversion = (baseline - current) * pull
  return current + noise + reversion
}

function smoothWalkInt(current: number, baseline: number, maxStep: number, pull = 0.04): number {
  return Math.round(smoothWalk(current, baseline, maxStep, pull))
}

function smoothHumidity(current: number, baseline: number): number {
  if (Math.random() > 0.22) {
    return current
  }

  const next = current + (Math.random() < 0.5 ? -1 : 1)
  return clamp(next, baseline - 2, baseline + 2)
}

/** 人体距离波动更大，模拟读写时前倾、后仰等坐姿微调 */
function smoothDistance(current: number, baseline: number, tooClose: boolean): number {
  const target = tooClose ? 315 : baseline
  const maxStep = tooClose ? 14 : 22
  const pull = tooClose ? 0.05 : 0.02
  let next = smoothWalk(current, target, maxStep, pull)

  if (Math.random() < 0.18) {
    next += (Math.random() - 0.5) * 56
  }

  return Math.round(clamp(next, 290, 820))
}

function resolveDistanceLevel(
  distanceMm: number,
  settings: LampSettings,
): MockRuntimeState['distanceLevel'] {
  const warning = settings.distance_warning_mm ?? 350
  const presence = settings.distance_presence_mm ?? 1200

  if (distanceMm <= warning) {
    return 'too_close'
  }

  if (distanceMm >= presence) {
    return 'far'
  }

  return 'normal'
}

function startOfToday(): number {
  const now = new Date()
  return Math.floor(new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000)
}

function atToday(hour: number, minute: number): number {
  return startOfToday() + hour * 3600 + minute * 60
}

function createSnapshot(label: string, timeText: string, accent: string): string {
  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2a2520"/>
      <stop offset="100%" stop-color="#151311"/>
    </linearGradient>
    <linearGradient id="desk" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#6b5344"/>
      <stop offset="100%" stop-color="#4a382c"/>
    </linearGradient>
  </defs>
  <rect width="640" height="360" fill="url(#bg)"/>
  <rect x="0" y="220" width="640" height="140" fill="url(#desk)"/>
  <rect x="80" y="60" width="480" height="170" rx="8" fill="#f5f0e8" opacity="0.92"/>
  <rect x="120" y="100" width="200" height="12" rx="4" fill="#d8d2c8"/>
  <rect x="120" y="130" width="280" height="8" rx="4" fill="#e8e2d8"/>
  <rect x="120" y="150" width="240" height="8" rx="4" fill="#e8e2d8"/>
  <circle cx="420" cy="130" r="36" fill="${accent}" opacity="0.35"/>
  <circle cx="420" cy="130" r="18" fill="${accent}"/>
  <rect x="24" y="24" width="592" height="312" rx="16" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
  <text x="32" y="340" fill="rgba(255,255,255,0.55)" font-family="sans-serif" font-size="13">${timeText}</text>
  <text x="608" y="340" fill="rgba(255,255,255,0.75)" font-family="sans-serif" font-size="13" text-anchor="end">${label}</text>
</svg>`.trim()

  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

function buildInitialEvents(): EventRecord[] {
  const morningStart = atToday(8, 12)
  const morningClose = atToday(8, 38)
  const morningLeave = atToday(8, 26)
  const morningWarn = atToday(8, 21)
  const afternoonStart = atToday(14, 28)
  const afternoonWarn = atToday(15, 4)
  const afternoonLeave = atToday(15, 18)

  return [
    {
      id: 1,
      device_id: DEVICE_ID,
      timestamp: morningStart,
      event_type: 'study_started',
      level: 'info',
      message: '检测到入座，本次学习开始',
      presence_state: 'present',
      distance_level: 'normal',
      study_state: 'studying',
    },
    {
      id: 2,
      device_id: DEVICE_ID,
      timestamp: morningWarn,
      event_type: 'distance_too_close',
      level: 'warning',
      message: '坐姿距离过近，请向后调整',
      presence_state: 'present',
      distance_level: 'too_close',
      study_state: 'warning',
      snapshot_url: createSnapshot('坐姿异常快照', '08:21:06', '#ff6900'),
    },
    {
      id: 3,
      device_id: DEVICE_ID,
      timestamp: morningLeave,
      event_type: 'presence_away',
      level: 'warning',
      message: '检测到离桌，已启动离桌判定计时',
      presence_state: 'away',
      distance_level: 'far',
      study_state: 'warning',
      snapshot_url: createSnapshot('离桌快照', '08:26:42', '#f59e0b'),
    },
    {
      id: 4,
      device_id: DEVICE_ID,
      timestamp: morningClose,
      event_type: 'study_finished',
      level: 'info',
      message: '本次学习结束，已生成学习摘要',
      presence_state: 'away',
      distance_level: 'far',
      study_state: 'idle',
      extra_json: { study_duration: 1560 },
    },
    {
      id: 5,
      device_id: DEVICE_ID,
      timestamp: atToday(12, 5),
      event_type: 'environment_changed',
      level: 'warning',
      message: '环境光照偏低，建议提高台灯亮度',
      presence_state: 'away',
      distance_level: 'far',
      study_state: 'idle',
      extra_json: { lux: 118, threshold: 150 },
    },
    {
      id: 6,
      device_id: DEVICE_ID,
      timestamp: afternoonStart,
      event_type: 'study_started',
      level: 'info',
      message: '检测到入座，本次学习开始',
      presence_state: 'present',
      distance_level: 'normal',
      study_state: 'studying',
    },
    {
      id: 7,
      device_id: DEVICE_ID,
      timestamp: afternoonWarn,
      event_type: 'distance_too_close',
      level: 'warning',
      message: '坐姿距离过近，请向后调整',
      presence_state: 'present',
      distance_level: 'too_close',
      study_state: 'warning',
      snapshot_url: createSnapshot('坐姿异常快照', '15:04:18', '#ff6900'),
    },
    {
      id: 8,
      device_id: DEVICE_ID,
      timestamp: afternoonLeave,
      event_type: 'presence_away',
      level: 'warning',
      message: '检测到短暂离桌',
      presence_state: 'away',
      distance_level: 'far',
      study_state: 'warning',
      snapshot_url: createSnapshot('离桌快照', '15:18:03', '#f59e0b'),
    },
  ]
}

function buildInitialSessions(now: number): StudySession[] {
  const morningStart = atToday(8, 12)
  const morningEnd = atToday(8, 38)
  const afternoonStart = atToday(14, 28)

  return [
    {
      id: 1,
      device_id: DEVICE_ID,
      started_at: morningStart,
      ended_at: morningEnd,
      duration_seconds: morningEnd - morningStart,
      warning_count: 2,
      leave_count: 1,
      status: 'completed',
      summary_text:
        '本次学习开始于 08:12:00，结束于 08:38:00，累计学习 26 分 0 秒，离桌 1 次，异常提醒 2 次。',
    },
    {
      id: 2,
      device_id: DEVICE_ID,
      started_at: afternoonStart,
      ended_at: null,
      duration_seconds: Math.max(0, now - afternoonStart),
      warning_count: 2,
      leave_count: 1,
      status: 'active',
      summary_text: null,
    },
  ]
}

function createInitialState(): MockRuntimeState {
  const now = Math.floor(Date.now() / 1000)
  const afternoonStart = atToday(14, 28)

  return {
    settings: {
      distance_warning_mm: 350,
      distance_presence_mm: 1200,
      light_low_lux: 150,
      temperature_high_c: 30,
      humidity_high_percent: 75,
      leave_grace_seconds: 15,
    },
    lampControl: {
      brightness: 72,
      color_temperature: 4100,
      scene_mode: 'eye_care',
    },
    sessions: buildInitialSessions(now),
    events: buildInitialEvents(),
    telemetryBaseline: {
      temperature: 25.4,
      humidity: 51,
      lux: 342,
      distance_mm: 580,
    },
    sessionStartedAt: afternoonStart,
    studyDurationSeconds: Math.max(0, now - afternoonStart),
    presenceState: 'present',
    distanceLevel: 'normal',
    studyState: 'studying',
    envLabels: [],
    tick: 0,
    smoothed: {
      temperature: 25.4,
      humidity: 51,
      lux: 342,
      distance_mm: 580,
    },
  }
}

let state = createInitialState()

function historyDrift(value: number, amplitude: number, phase: number, pull = 0.015): number {
  const wave = Math.sin(phase * 0.08) * amplitude
  const noise = Math.sin(phase * 0.23 + value) * amplitude * 0.25
  return Number((value + wave * pull + noise * pull).toFixed(1))
}

function historyDriftInt(value: number, amplitude: number, phase: number): number {
  return Math.round(historyDrift(value, amplitude, phase))
}

export function getMockState(): MockRuntimeState {
  return state
}

export function resetMockState(): void {
  state = createInitialState()
}

export function updateMockSettings(next: LampSettings): LampSettings {
  state.settings = { ...state.settings, ...next }
  return { ...state.settings }
}

export function updateMockLampControl(next: Partial<LampControlState>): LampControlState {
  state.lampControl = { ...state.lampControl, ...next }
  return { ...state.lampControl }
}

export function advanceMockTelemetry(): TelemetryRecord {
  state.tick += 1
  const now = Math.floor(Date.now() / 1000)
  state.studyDurationSeconds = Math.max(0, now - state.sessionStartedAt)

  const activeSession = state.sessions.find((item) => item.status === 'active')
  if (activeSession) {
    activeSession.duration_seconds = state.studyDurationSeconds
  }

  const cycle = state.tick % 180
  if (cycle === 150) {
    state.distanceLevel = 'too_close'
    state.studyState = 'warning'
  } else if (cycle === 153) {
    state.distanceLevel = 'normal'
    state.studyState = 'studying'
  }

  if (cycle >= 70 && cycle <= 85) {
    state.envLabels = ['light_low']
    state.telemetryBaseline.lux = 135
  } else if (cycle > 85) {
    state.envLabels = []
    state.telemetryBaseline.lux = 342
  }

  const { telemetryBaseline, smoothed } = state
  const luxTarget = state.envLabels.includes('light_low')
    ? telemetryBaseline.lux
    : telemetryBaseline.lux

  smoothed.temperature = Number(
    smoothWalk(smoothed.temperature, telemetryBaseline.temperature, 0.04).toFixed(1),
  )
  smoothed.humidity = smoothHumidity(smoothed.humidity, telemetryBaseline.humidity)
  smoothed.lux = smoothWalkInt(smoothed.lux, luxTarget, 1.2, 0.06)
  smoothed.distance_mm = smoothDistance(
    smoothed.distance_mm,
    telemetryBaseline.distance_mm,
    state.distanceLevel === 'too_close',
  )

  const distanceLevel = resolveDistanceLevel(smoothed.distance_mm, state.settings)
  if (cycle < 150 || cycle > 153) {
    state.distanceLevel = distanceLevel
    if (distanceLevel === 'too_close' && state.studyState !== 'idle') {
      state.studyState = 'warning'
    } else if (distanceLevel === 'normal' && state.studyState === 'warning') {
      state.studyState = 'studying'
    }
  }

  const temperature = smoothed.temperature
  const humidity = smoothed.humidity
  const lux = smoothed.lux
  const distance_mm = smoothed.distance_mm

  return {
    device_id: DEVICE_ID,
    timestamp: now,
    temperature,
    humidity,
    lux,
    distance_mm,
    presence_state: state.presenceState,
    distance_level: state.distanceLevel,
    env_label: [...state.envLabels],
    study_state: state.studyState,
    study_duration: state.studyDurationSeconds,
    session_started_at: state.sessionStartedAt,
  }
}

export function getMockHeartbeat(): {
  device_id: string
  timestamp: number
  ip: string
  study_state: string
} {
  return {
    device_id: DEVICE_ID,
    timestamp: Math.floor(Date.now() / 1000),
    ip: '192.168.1.108',
    study_state: state.studyState,
  }
}

export function getMockLatestEvent(): EventRecord | null {
  return state.events.length > 0 ? { ...state.events[state.events.length - 1] } : null
}

export function getMockEvents(page = 1, pageSize = 8): {
  items: EventRecord[]
  total: number
  page: number
  page_size: number
} {
  const sorted = [...state.events].sort((a, b) => (b.timestamp ?? 0) - (a.timestamp ?? 0))
  const start = (page - 1) * pageSize
  return {
    items: sorted.slice(start, start + pageSize),
    total: sorted.length,
    page,
    page_size: pageSize,
  }
}

export function getMockCurrentSession(): StudySession | null {
  return state.sessions.find((item) => item.status === 'active') ?? null
}

export function getMockLatestSummary(): StudySession | null {
  const completed = state.sessions
    .filter((item) => item.status === 'completed')
    .sort((a, b) => (b.ended_at ?? 0) - (a.ended_at ?? 0))
  return completed[0] ?? null
}

export function getMockTodaySummary(): {
  sessions: StudySession[]
  total_duration_seconds: number
  total_warning_count: number
  total_leave_count: number
} {
  const sessions = [...state.sessions].sort((a, b) => (b.started_at ?? 0) - (a.started_at ?? 0))
  return {
    sessions,
    total_duration_seconds: sessions.reduce((sum, item) => sum + (item.duration_seconds ?? 0), 0),
    total_warning_count: sessions.reduce((sum, item) => sum + (item.warning_count ?? 0), 0),
    total_leave_count: sessions.reduce((sum, item) => sum + (item.leave_count ?? 0), 0),
  }
}

export function getMockHistory(limit = 120): TelemetryRecord[] {
  const now = Math.floor(Date.now() / 1000)
  const interval = 60
  const points: TelemetryRecord[] = []

  for (let index = limit - 1; index >= 0; index -= 1) {
    const timestamp = now - index * interval
    const phase = limit - index
    points.push({
      device_id: DEVICE_ID,
      timestamp,
      temperature: historyDrift(25.2, 0.8, phase),
      humidity: historyDriftInt(52, 2.5, phase),
      lux: historyDriftInt(phase > limit * 0.6 ? 360 : 295, 12, phase),
      distance_mm: historyDriftInt(590, 28, phase),
      presence_state: 'present',
      distance_level: 'normal',
      study_state: 'studying',
    })
  }

  return points
}

export { SCENE_MODE_LABEL } from '@/constants/labels'
