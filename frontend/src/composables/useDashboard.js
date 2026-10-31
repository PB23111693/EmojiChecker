import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getSession, listCourses, listSessions } from '@/api/catalog'
import { listHistory, listSessionStudents } from '@/api/emoji'
import { fetchDashboard } from '@/api/stats'
import { authStore } from '@/stores/auth'
import { formatDateTime } from '@/stores/dict'

/**
 * 教师课堂看板的状态、轮询与 WebSocket。
 *
 * WebSocket 只作为变更信号，收到后拉取一次看板数据；3 秒轮询作为
 * 断线恢复与兜底。图表配置属于 View 的呈现细节，保留在 .vue 中。
 */
export function useDashboard() {
  const courses = ref([])
  const sessions = ref([])
  const courseId = ref(null)
  const sessionId = ref(null)
  const dashboard = ref(null)
  const session = ref(null)
  const students = ref([])
  const studentLoading = ref(false)
  const trendSource = ref('MANUAL')
  const lastSuccessAt = ref(null)
  const updateFailed = ref(false)
  const dialogVisible = ref(false)
  const dialogRows = ref([])
  const dialogLoading = ref(false)
  const dialogTitle = ref('')

  let pollTimer = null
  let socket = null
  let socketRetry = 0
  let dashboardRequest = 0
  let studentRequest = 0
  let disposed = false

  const manual = computed(
    () =>
      dashboard.value?.manual || {
        total: 0,
        participants: 0,
        member_count: 0,
        coverage: null,
        distribution: []
      }
  )
  const ai = computed(
    () =>
      dashboard.value?.ai || {
        total: 0,
        threshold: 0.6,
        last_observed_at: null,
        distribution: []
      }
  )
  const trendPoints = computed(() => dashboard.value?.trend || [])
  const coverageText = computed(() => {
    const value = manual.value.coverage
    if (value === null || value === undefined) return '不适用'
    return `${Math.round(value * 100)}%`
  })
  const lastSuccessLabel = computed(() =>
    lastSuccessAt.value ? formatDateTime(lastSuccessAt.value).slice(11) : '—'
  )

  function shortTime(value) {
    const formatted = formatDateTime(value)
    return formatted === '—' ? formatted : formatted.slice(5)
  }

  async function loadSessions() {
    if (!courseId.value) {
      sessions.value = []
      sessionId.value = null
      return
    }
    const data = await listSessions({ course_id: courseId.value, page: 1, page_size: 100 })
    sessions.value = data.items
    const ongoing = data.items.find((item) => item.status === 'ONGOING')
    sessionId.value = ongoing ? ongoing.id : data.items[0]?.id || null
    if (sessionId.value) await onSessionChange(sessionId.value)
  }

  async function loadDashboard() {
    const target = Number(sessionId.value)
    if (!target) return
    const requestId = ++dashboardRequest
    try {
      const [data, detail] = await Promise.all([
        fetchDashboard(target),
        session.value?.id === target ? Promise.resolve(session.value) : getSession(target)
      ])
      // 切换课堂后旧请求可能才返回，按课堂与请求序号丢弃过期响应。
      if (requestId !== dashboardRequest || Number(sessionId.value) !== target) return
      dashboard.value = data
      session.value = detail
      lastSuccessAt.value = new Date()
      updateFailed.value = false
    } catch (error) {
      if (requestId === dashboardRequest && Number(sessionId.value) === target) {
        updateFailed.value = true
      }
    }
  }

  async function loadStudents() {
    const target = Number(sessionId.value)
    if (!target) return
    const requestId = ++studentRequest
    if (!students.value.length) studentLoading.value = true
    try {
      const rows = await listSessionStudents(target)
      if (requestId !== studentRequest || Number(sessionId.value) !== target) return
      students.value = rows
    } catch {
      // 明细刷新失败时保留旧表，看板顶部的更新时间与失败标记仍会提示。
    } finally {
      if (requestId === studentRequest) studentLoading.value = false
    }
  }

  async function refresh() {
    // 聚合数据与参与学生明细一起刷新，避免看板人数变化而明细停留在旧值。
    await Promise.all([loadDashboard(), loadStudents()])
  }

  async function onCourseChange() {
    await loadSessions()
  }

  async function onSessionChange() {
    dashboard.value = null
    session.value = null
    students.value = []
    connectSocket()
    await refresh()
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(() => {
      if (document.visibilityState === 'visible') refresh()
    }, 3000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function connectSocket() {
    closeSocket()
    if (!sessionId.value || !authStore.token) return
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/ws/dashboard?session_id=${sessionId.value}&token=${encodeURIComponent(authStore.token)}`
    try {
      socket = new WebSocket(url)
    } catch {
      return
    }
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'emoji.created') refresh()
      } catch {
        /* 忽略无法解析的消息 */
      }
    }
    socket.onclose = () => {
      socket = null
      if (disposed || !sessionId.value) return
      socketRetry = Math.min(socketRetry + 1, 5)
      setTimeout(() => {
        if (!disposed && !socket) connectSocket()
      }, socketRetry * 2000)
    }
    socket.onopen = () => {
      socketRetry = 0
    }
  }

  function closeSocket() {
    if (socket) {
      socket.onclose = null
      socket.close()
      socket = null
    }
  }

  async function openStudent(row) {
    dialogTitle.value = `${row.username} 在本课堂的手动记录`
    dialogVisible.value = true
    dialogLoading.value = true
    try {
      const data = await listHistory({
        session_id: Number(sessionId.value),
        user_id: row.user_id,
        source: 'MANUAL',
        page: 1,
        page_size: 50
      })
      dialogRows.value = data.items
    } finally {
      dialogLoading.value = false
    }
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible') refresh()
  }

  onMounted(async () => {
    document.addEventListener('visibilitychange', onVisibilityChange)
    courses.value = await listCourses()
    if (courses.value.length) {
      courseId.value = courses.value[0].id
      await loadSessions()
    }
    startPolling()
  })

  onBeforeUnmount(() => {
    disposed = true
    document.removeEventListener('visibilitychange', onVisibilityChange)
    stopPolling()
    closeSocket()
  })

  return {
    courses,
    sessions,
    courseId,
    sessionId,
    dashboard,
    session,
    students,
    studentLoading,
    trendSource,
    updateFailed,
    dialogVisible,
    dialogRows,
    dialogLoading,
    dialogTitle,
    manual,
    ai,
    trendPoints,
    coverageText,
    lastSuccessLabel,
    shortTime,
    loadDashboard,
    loadStudents,
    onCourseChange,
    onSessionChange,
    openStudent
  }
}
