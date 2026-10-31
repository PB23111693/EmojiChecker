import { reactive, ref } from 'vue'
import { listClasses, listCourses } from '@/api/catalog'
import { listHistory } from '@/api/emoji'

/**
 * 管理端记录明细页的页面控制器。
 *
 * 管理员查看全部手动与 AI 记录，支持课程、班级、日期、来源与表情筛选。
 * 与统计页使用同一套服务端筛选参数，保证页面与导出可核对。
 */
export function createRecordsController() {
  const courses = ref([])
  const classOptions = ref([])
  const rows = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const range = ref(null)
  const filters = reactive({ course_id: null, class_name: null, source: null, emotion: null })

  function buildParams() {
    const params = {}
    if (filters.course_id) params.course_id = filters.course_id
    if (filters.class_name) params.class_name = filters.class_name
    if (filters.source) params.source = filters.source
    if (filters.emotion) params.emotion = filters.emotion
    if (Array.isArray(range.value) && range.value.length === 2) {
      params.from = `${range.value[0]}T00:00:00+08:00`
      params.to = `${range.value[1]}T23:59:59+08:00`
    }
    return params
  }

  async function load() {
    loading.value = true
    try {
      const data = await listHistory({
        ...buildParams(),
        page: page.value,
        page_size: pageSize.value
      })
      rows.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function reset() {
    filters.course_id = null
    filters.class_name = null
    filters.source = null
    filters.emotion = null
    range.value = null
    page.value = 1
    await load()
  }

  async function changePage(value) {
    page.value = value
    await load()
  }

  async function init() {
    const [courseRows, classRows] = await Promise.all([listCourses(), listClasses()])
    courses.value = courseRows
    classOptions.value = classRows
    await load()
  }

  return {
    courses,
    classOptions,
    rows,
    total,
    page,
    pageSize,
    loading,
    range,
    filters,
    load,
    reset,
    changePage,
    init
  }
}
