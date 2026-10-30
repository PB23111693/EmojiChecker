import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listClasses, listCourses } from '@/api/catalog'
import { exportCsv, fetchStatistics } from '@/api/stats'

/**
 * 管理端多维统计页的页面控制器。
 *
 * 修改版 MVC 中的 Controller：负责筛选条件、查询、导出与页面状态；
 * 图表配置属于 View 的呈现细节，保留在 .vue 中。
 */
export function createStatisticsController() {
  const courses = ref([])
  const classOptions = ref([])
  const stats = ref(null)
  const total = ref(0)
  const range = ref(null)
  const exporting = ref(false)
  const filters = reactive({ course_id: null, class_name: null, source: null })

  const trend = computed(() => stats.value?.trend || [])
  // 最近一次成功查询的条件。导出始终使用它，避免页面显示 A 条件而 CSV 按 B 条件导出。
  let appliedParams = null

  function buildParams() {
    const params = {}
    if (filters.course_id) params.course_id = filters.course_id
    if (filters.class_name) params.class_name = filters.class_name
    if (filters.source) params.source = filters.source
    if (Array.isArray(range.value) && range.value.length === 2) {
      // 页面按本地日期选择，接口要求带偏移量的时间；统一按东八区边界换算。
      params.from = `${range.value[0]}T00:00:00+08:00`
      params.to = `${range.value[1]}T23:59:59+08:00`
    }
    return params
  }

  async function load() {
    const params = buildParams()
    const data = await fetchStatistics(params)
    appliedParams = params
    stats.value = data
    total.value = data.total
  }

  async function reset() {
    filters.course_id = null
    filters.class_name = null
    filters.source = null
    range.value = null
    await load()
  }

  async function exportFile() {
    if (exporting.value) return
    exporting.value = true
    try {
      const rows = await exportCsv(appliedParams ?? buildParams())
      ElMessage.success(`已导出 ${rows || total.value} 条记录`)
    } finally {
      exporting.value = false
    }
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
    stats,
    total,
    range,
    exporting,
    filters,
    trend,
    buildParams,
    load,
    reset,
    exportFile,
    init
  }
}
