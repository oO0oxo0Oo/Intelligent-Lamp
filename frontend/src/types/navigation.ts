export type AppTab = 'monitor' | 'summary' | 'events' | 'settings' | 'control' | 'history'

export const APP_TABS: { id: AppTab; label: string; desc: string }[] = [
  { id: 'monitor', label: '实时监测', desc: '状态总览' },
  { id: 'summary', label: '学习摘要', desc: '会话统计' },
  { id: 'events', label: '事件记录', desc: '过程追溯' },
  { id: 'settings', label: '参数配置', desc: '阈值管控' },
  { id: 'control', label: '台灯控制', desc: '远程调节' },
  { id: 'history', label: '历史数据', desc: '趋势分析' },
]
