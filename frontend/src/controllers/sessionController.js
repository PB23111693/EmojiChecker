import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCourse,
  createSession,
  listCourses,
  listMembers,
  listSessions,
  listTeachers,
  saveMembers,
  updateSession
} from '@/api/catalog'
import { listUsers } from '@/api/admin'

/**
 * 管理端课程与课堂页的页面控制器。
 *
 * 修改版 MVC 中的 Controller：负责课程、课堂、名单的读取与提交，
 * 对话框开关与表单状态也在此维护，View 只负责模板与交互绑定。
 */
export function createSessionController() {
  const courses = ref([])
  const sessions = ref([])
  const teachers = ref([])
  const students = ref([])
  const currentCourse = ref(null)
  const loading = ref(false)
  const submitting = ref(false)

  const courseDialog = ref(false)
  const sessionDialog = ref(false)
  const memberDrawer = ref(false)
  const memberKeyword = ref('')
  const selectedIds = ref([])
  const memberSession = ref(null)

  const courseForm = reactive({ name: '', teacher_id: null })
  const sessionForm = reactive({
    id: null,
    class_name: '',
    room: '',
    start_at: null,
    end_at: null,
    ai_threshold: 0.6
  })

  const filteredStudents = computed(() => {
    const keyword = memberKeyword.value.trim().toLowerCase()
    if (!keyword) return students.value
    return students.value.filter((item) => item.username.toLowerCase().includes(keyword))
  })

  async function loadCourses() {
    courses.value = await listCourses()
    if (!currentCourse.value && courses.value.length) {
      currentCourse.value = courses.value[0]
      await loadSessions()
    }
  }

  async function loadSessions() {
    if (!currentCourse.value) return
    loading.value = true
    try {
      const data = await listSessions({
        course_id: currentCourse.value.id,
        page: 1,
        page_size: 100
      })
      sessions.value = data.items
    } finally {
      loading.value = false
    }
  }

  async function loadStudents() {
    const collected = []
    let page = 1
    while (page <= 10) {
      const data = await listUsers({ role: 'STUDENT', status: 'ACTIVE', page, page_size: 100 })
      collected.push(...data.items)
      if (collected.length >= data.total) break
      page += 1
    }
    students.value = collected
  }

  async function selectCourse(item) {
    currentCourse.value = item
    await loadSessions()
  }

  function openCourseDialog() {
    courseForm.name = ''
    courseForm.teacher_id = teachers.value[0]?.id || null
    courseDialog.value = true
  }

  async function submitCourse() {
    if (!courseForm.name.trim() || !courseForm.teacher_id) {
      ElMessage.warning('请填写课程名称并选择教师')
      return
    }
    submitting.value = true
    try {
      await createCourse({ name: courseForm.name.trim(), teacher_id: courseForm.teacher_id })
      ElMessage.success('课程已创建')
      courseDialog.value = false
      await loadCourses()
      await loadSessions()
    } finally {
      submitting.value = false
    }
  }

  function openSessionDialog(row = null) {
    if (row) {
      sessionForm.id = row.id
      sessionForm.class_name = row.class_name
      sessionForm.room = row.room || ''
      sessionForm.start_at = new Date(row.start_at)
      sessionForm.end_at = new Date(row.end_at)
      sessionForm.ai_threshold = Number(row.ai_threshold)
    } else {
      sessionForm.id = null
      sessionForm.class_name = ''
      sessionForm.room = ''
      sessionForm.start_at = null
      sessionForm.end_at = null
      sessionForm.ai_threshold = 0.6
    }
    sessionDialog.value = true
  }

  async function submitSession() {
    if (!sessionForm.class_name.trim() || !sessionForm.start_at || !sessionForm.end_at) {
      ElMessage.warning('请填写班级与起止时间')
      return
    }
    if (!sessionForm.id && !currentCourse.value) {
      ElMessage.warning('请先选择课程')
      return
    }
    const payload = {
      class_name: sessionForm.class_name.trim(),
      room: sessionForm.room.trim() || null,
      start_at: new Date(sessionForm.start_at).toISOString(),
      end_at: new Date(sessionForm.end_at).toISOString(),
      ai_threshold: sessionForm.ai_threshold
    }
    submitting.value = true
    try {
      if (sessionForm.id) {
        await updateSession(sessionForm.id, payload)
        ElMessage.success('课堂已更新')
      } else {
        await createSession({ course_id: currentCourse.value.id, ...payload })
        ElMessage.success('课堂已创建')
      }
      sessionDialog.value = false
      await loadSessions()
      await loadCourses()
    } finally {
      submitting.value = false
    }
  }

  async function toggleCancel(row) {
    const next = !row.cancelled
    try {
      await ElMessageBox.confirm(
        next
          ? '取消后该课堂不可恢复为进行中，学生无法提交反馈。'
          : '恢复后课堂按原时间安排正常进行。',
        next ? '取消课堂' : '恢复课堂',
        { type: 'warning' }
      )
    } catch {
      return
    }
    await updateSession(row.id, { cancelled: next })
    ElMessage.success(next ? '课堂已取消' : '课堂已恢复')
    await loadSessions()
  }

  async function openMembers(row) {
    memberSession.value = row
    memberDrawer.value = true
    const data = await listMembers(row.id)
    selectedIds.value = data.items.map((item) => item.user_id)
    if (!students.value.length) await loadStudents()
  }

  async function submitMembers() {
    if (!memberSession.value) return
    submitting.value = true
    try {
      await saveMembers(memberSession.value.id, selectedIds.value)
      ElMessage.success('名单已保存')
      memberDrawer.value = false
      await loadSessions()
      await loadCourses()
    } finally {
      submitting.value = false
    }
  }

  async function init() {
    const [courseRows, teacherRows] = await Promise.all([listCourses(), listTeachers()])
    courses.value = courseRows
    teachers.value = teacherRows
    await loadStudents()
    if (courses.value.length) {
      currentCourse.value = courses.value[0]
      await loadSessions()
    }
  }

  return {
    courses,
    sessions,
    teachers,
    students,
    currentCourse,
    loading,
    submitting,
    courseDialog,
    sessionDialog,
    memberDrawer,
    memberKeyword,
    selectedIds,
    memberSession,
    courseForm,
    sessionForm,
    filteredStudents,
    loadCourses,
    loadSessions,
    loadStudents,
    selectCourse,
    openCourseDialog,
    submitCourse,
    openSessionDialog,
    submitSession,
    toggleCancel,
    openMembers,
    submitMembers,
    init
  }
}
