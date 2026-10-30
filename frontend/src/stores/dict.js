export const EMOTIONS = [
  { value: 'HAPPY', label: '开心', icon: '😄', color: '#e8a33d' },
  { value: 'NEUTRAL', label: '平静', icon: '😐', color: '#7b8794' },
  { value: 'SAD', label: '低落', icon: '😢', color: '#4a7fb5' },
  { value: 'ANGRY', label: '生气', icon: '😠', color: '#cc5a52' },
  { value: 'SURPRISED', label: '惊讶', icon: '😲', color: '#8a6db1' },
  { value: 'FEARFUL', label: '害怕', icon: '😨', color: '#3f8f8a' },
  { value: 'DISGUST', label: '厌恶', icon: '🤢', color: '#7f8f4a' }
]

const EMOTION_MAP = Object.fromEntries(EMOTIONS.map((item) => [item.value, item]))

export function emotionMeta(value) {
  return EMOTION_MAP[value] || { value, label: value, icon: '•', color: '#9aa4ae' }
}

export const SESSION_STATUS = {
  PENDING: { label: '未开始', type: 'info' },
  ONGOING: { label: '进行中', type: 'success' },
  ENDED: { label: '已结束', type: 'warning' },
  CANCELLED: { label: '已取消', type: 'danger' }
}

export function statusMeta(value) {
  return SESSION_STATUS[value] || { label: value, type: 'info' }
}

export const ROLE_LABEL = {
  STUDENT: '学生',
  TEACHER: '教师',
  ADMIN: '管理员'
}

export const SOURCE_LABEL = {
  MANUAL: '手动',
  AI: 'AI'
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatTimeRange(start, end) {
  const s = new Date(start)
  const e = new Date(end)
  const pad = (num) => String(num).padStart(2, '0')
  const date = `${s.getMonth() + 1}月${s.getDate()}日`
  return `${date} ${pad(s.getHours())}:${pad(s.getMinutes())} 至 ${pad(e.getHours())}:${pad(e.getMinutes())}`
}
