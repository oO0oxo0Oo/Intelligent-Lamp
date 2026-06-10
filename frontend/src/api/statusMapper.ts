import { EVENT_TYPE_LABEL, SCENE_MODE_LABEL, STUDY_STATE_LABEL } from '@/constants/labels'
import type { CurrentStatusPayload, EventRecord, LampSettings } from '@/types/api'
import type { SensorDashboardPayload, SensorKey, SensorReading, StatusOverview } from '@/types/sensor'

const HEARTBEAT_ONLINE_SECONDS = 30
const DEFAULT_LAMP_BRIGHTNESS = 68
const DEFAULT_COLOR_TEMPERATURE = 4100

function formatTimestamp(timestamp?: number | null): string {
  if (!timestamp) {
    return '--'
  }

  const date = new Date(timestamp * 1000)
  const pad = (value: number) => String(value).padStart(2, '0')

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function isDeviceOnline(heartbeatTimestamp?: number | null): boolean {
  if (!heartbeatTimestamp) {
    return false
  }

  return Date.now() / 1000 - heartbeatTimestamp <= HEARTBEAT_ONLINE_SECONDS
}

function formatTrend(
  current?: number | null,
  previous?: number,
  stableThreshold = 0.12,
): string {
  if (current == null || previous == null) {
    return '稳定'
  }

  const delta = current - previous
  if (Math.abs(delta) < stableThreshold) {
    return '稳定'
  }

  const sign = delta > 0 ? '+' : ''
  const precision = stableThreshold >= 1 ? 0 : 1
  return `${sign}${delta.toFixed(precision)}`
}

function luxStatus(lux: number | null | undefined, settings: LampSettings): SensorReading['status'] {
  if (lux == null) {
    return 'normal'
  }

  const threshold = settings.light_low_lux ?? 150
  return lux < threshold ? 'low' : 'normal'
}

function humidityStatus(
  humidity: number | null | undefined,
  settings: LampSettings,
): SensorReading['status'] {
  if (humidity == null) {
    return 'normal'
  }

  const threshold = settings.humidity_high_percent ?? 75
  return humidity > threshold ? 'high' : 'normal'
}

function temperatureStatus(
  temperature: number | null | undefined,
  settings: LampSettings,
): SensorReading['status'] {
  if (temperature == null) {
    return 'normal'
  }

  const threshold = settings.temperature_high_c ?? 30
  return temperature > threshold ? 'high' : 'normal'
}

function distanceStatus(distanceLevel?: string | null): SensorReading['status'] {
  if (distanceLevel === 'too_close') {
    return 'high'
  }

  if (distanceLevel === 'far') {
    return 'low'
  }

  return 'normal'
}

function luxDescription(lux: number | null | undefined, settings: LampSettings): string {
  if (lux == null) {
    return '暂无光照数据'
  }

  const threshold = settings.light_low_lux ?? 150
  return lux < threshold ? '环境偏暗，建议提高亮度' : '光线充足，适合阅读'
}

function humidityDescription(
  humidity: number | null | undefined,
  settings: LampSettings,
): string {
  if (humidity == null) {
    return '暂无湿度数据'
  }

  const threshold = settings.humidity_high_percent ?? 75
  return humidity > threshold ? '湿度偏高，注意通风' : '湿度舒适，维持当前模式'
}

function temperatureDescription(
  temperature: number | null | undefined,
  settings: LampSettings,
): string {
  if (temperature == null) {
    return '暂无温度数据'
  }

  const threshold = settings.temperature_high_c ?? 30
  return temperature > threshold ? '温度偏高，注意散热' : '温度适中，无需调整'
}

function distanceDescription(distanceLevel?: string | null): string {
  if (distanceLevel === 'too_close') {
    return '距离过近，请向后调整坐姿'
  }

  if (distanceLevel === 'far') {
    return '未检测到有效用灯距离'
  }

  return '处于推荐用灯距离'
}

function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds <= 0) {
    return '0 分钟'
  }

  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const remainMinutes = minutes % 60
    return `${hours} 小时 ${remainMinutes} 分`
  }

  return remainSeconds > 0 ? `${minutes} 分 ${remainSeconds} 秒` : `${minutes} 分钟`
}

function eventLevelLabel(level?: string | null): string {
  if (level === 'warning') {
    return '告警'
  }

  return '信息'
}

function buildOverview(payload: CurrentStatusPayload): StatusOverview {
  const { telemetry, latest_event } = payload
  const studyState = telemetry?.study_state ?? 'idle'
  const presence = telemetry?.presence_state ?? 'away'

  let headline = '设备待机中'
  let detail = '暂未检测到学习活动，等待入座后开始陪学监测。'

  if (studyState === 'studying') {
    headline = '正在学习'
    detail = `已持续 ${formatDuration(telemetry?.study_duration)}，环境与坐姿状态正常监测中。`
  } else if (studyState === 'warning') {
    headline = '异常提醒'
    detail = latest_event?.message ?? '检测到需要关注的异常行为或环境变化。'
  } else if (presence === 'present') {
    headline = '已入座'
    detail = '检测到用户在位，等待进入正式学习状态。'
  }

  return {
    studyState,
    presenceState: presence,
    studyDurationText: formatDuration(telemetry?.study_duration),
    headline,
    detail,
    latestEvent: latest_event ?? null,
  }
}

function buildReadings(
  payload: CurrentStatusPayload,
  previousValues?: Partial<Record<SensorKey, number>>,
): SensorReading[] {
  const { telemetry, settings, lamp_control } = payload
  const lux = telemetry?.lux ?? null
  const humidity = telemetry?.humidity ?? null
  const temperature = telemetry?.temperature ?? null
  const distanceCm =
    telemetry?.distance_mm == null ? null : Number((telemetry.distance_mm / 10).toFixed(1))

  return [
    {
      key: 'illumination',
      label: '环境光照',
      value: lux ?? 0,
      unit: 'lx',
      status: luxStatus(lux, settings),
      trend: formatTrend(lux, previousValues?.illumination, 3),
      description: luxDescription(lux, settings),
    },
    {
      key: 'humidity',
      label: '空气湿度',
      value: humidity ?? 0,
      unit: '%',
      status: humidityStatus(humidity, settings),
      trend: formatTrend(humidity, previousValues?.humidity, 1),
      description: humidityDescription(humidity, settings),
    },
    {
      key: 'temperature',
      label: '环境温度',
      value: temperature ?? 0,
      unit: '°C',
      status: temperatureStatus(temperature, settings),
      trend: formatTrend(temperature, previousValues?.temperature, 0.15),
      description: temperatureDescription(temperature, settings),
    },
    {
      key: 'distance',
      label: '人体距离',
      value: distanceCm ?? 0,
      unit: 'cm',
      status: distanceStatus(telemetry?.distance_level),
      trend: formatTrend(distanceCm, previousValues?.distance, 0.8),
      description: distanceDescription(telemetry?.distance_level),
    },
    {
      key: 'brightness',
      label: '灯光亮度',
      value: lamp_control?.brightness ?? DEFAULT_LAMP_BRIGHTNESS,
      unit: '%',
      status: 'normal',
      trend: '稳定',
      description: `当前色温 ${lamp_control?.color_temperature ?? DEFAULT_COLOR_TEMPERATURE}K，${SCENE_MODE_LABEL[lamp_control?.scene_mode ?? 'eye_care'] ?? '护眼模式'}`,
    },
  ]
}

export function mapStatusToDashboard(
  payload: CurrentStatusPayload,
  previousValues?: Partial<Record<SensorKey, number>>,
): SensorDashboardPayload {
  const { telemetry, heartbeat, lamp_control } = payload
  const studyState = telemetry?.study_state ?? heartbeat?.study_state ?? 'idle'
  const updatedAt = formatTimestamp(telemetry?.timestamp ?? heartbeat?.timestamp)
  const sceneLabel = lamp_control?.scene_mode
    ? SCENE_MODE_LABEL[lamp_control.scene_mode]
    : undefined

  return {
    lamp: {
      name: 'StudyPilot 学习台灯',
      room: '书房 · 小明',
      online: isDeviceOnline(heartbeat?.timestamp),
      mode: sceneLabel ?? STUDY_STATE_LABEL[studyState] ?? '自适应护眼',
      colorTemperature: lamp_control?.color_temperature ?? DEFAULT_COLOR_TEMPERATURE,
      brightness: lamp_control?.brightness ?? DEFAULT_LAMP_BRIGHTNESS,
      updatedAt,
    },
    overview: buildOverview(payload),
    readings: buildReadings(payload, previousValues),
  }
}

export function formatEventTime(timestamp?: number | null): string {
  return formatTimestamp(timestamp)
}

export function getEventTypeLabel(eventType?: string | null): string {
  return EVENT_TYPE_LABEL[eventType ?? ''] ?? eventType ?? '系统事件'
}

export function isBehaviorEvent(event: EventRecord): boolean {
  return event.event_type === 'presence_away' || event.event_type === 'distance_too_close'
}

export { eventLevelLabel, formatDuration }

export function extractReadingValues(
  dashboard: SensorDashboardPayload,
): Partial<Record<SensorKey, number>> {
  return Object.fromEntries(dashboard.readings.map((reading) => [reading.key, reading.value]))
}
