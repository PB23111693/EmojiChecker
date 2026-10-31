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

// 页面与课堂编辑统一使用北京时间，不能依赖浏览器或操作系统的默认时区。
const dateTimeFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23'
})

function dateTimeParts(value) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return Object.fromEntries(
    dateTimeFormatter.formatToParts(date).map(({ type, value }) => [type, value])
  )
}

export function formatDateTime(value) {
  const parts = dateTimeParts(value)
  if (!parts) return '—'
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`
}

export function formatTimeRange(start, end) {
  const s = dateTimeParts(start)
  const e = dateTimeParts(end)
  if (!s || !e) return '—'
  const sameDay = s.year === e.year && s.month === e.month && s.day === e.day
  const startDate = `${Number(s.month)}月${Number(s.day)}日`
  const endDate = sameDay ? '' : `${Number(e.month)}月${Number(e.day)}日 `
  return `${startDate} ${s.hour}:${s.minute} 至 ${endDate}${e.hour}:${e.minute}`
}

export function formatDateTimeInput(value) {
  const parts = dateTimeParts(value)
  if (!parts) return null
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`
}

export function toApiDateTime(value) {
  // 日期选择器返回北京时间的墙上时间，显式附加偏移后再转换为接口所用的 UTC。
  const date = new Date(`${value.replace(' ', 'T')}+08:00`)
  if (Number.isNaN(date.getTime())) throw new Error('课堂时间格式不正确')
  return date.toISOString()
}
