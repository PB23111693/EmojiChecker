<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">我的记录</h1>
        <p class="page-sub">仅显示本人手动提交的表情记录，AI 观察结果不计入个人历史。</p>
      </div>
    </div>

    <section class="panel">
      <div class="filter-row">
        <el-select v-model="filters.course_id" placeholder="全部课程" clearable style="width: 200px">
          <el-option v-for="item in courses" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-date-picker
          v-model="range"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 280px"
        />
        <el-button type="primary" @click="search">查询</el-button>
        <el-button text @click="reset">重置</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" empty-text="暂无记录" style="width: 100%">
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.observed_at) }}</template>
        </el-table-column>
        <el-table-column prop="course_name" label="课程" min-width="160" />
        <el-table-column prop="class_name" label="班级" width="140" />
        <el-table-column label="表情" width="140">
          <template #default="{ row }">
            <span class="emotion-cell">
              <span>{{ emotionMeta(row.emotion).icon }}</span>
              {{ emotionMeta(row.emotion).label }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ SOURCE_LABEL[row.source] || row.source }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          layout="total, prev, pager, next, sizes"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          :page-sizes="[10, 20, 50]"
          @current-change="onPage"
          @size-change="onSize"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { listCourses } from '@/api/catalog'
import { listHistory } from '@/api/emoji'
import { formatDateTime, emotionMeta, SOURCE_LABEL } from '@/stores/dict'

const route = useRoute()
const courses = ref([])
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const range = ref(null)
const filters = reactive({ course_id: null, session_id: null })

function buildParams() {
  const params = { page: page.value, page_size: pageSize.value }
  if (filters.course_id) params.course_id = filters.course_id
  if (filters.session_id) params.session_id = filters.session_id
  if (Array.isArray(range.value) && range.value.length === 2) {
    params.from = `${range.value[0]}T00:00:00+08:00`
    params.to = `${range.value[1]}T23:59:59+08:00`
  }
  return params
}

async function load() {
  loading.value = true
  try {
    const data = await listHistory(buildParams())
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function reset() {
  filters.course_id = null
  filters.session_id = null
  range.value = null
  search()
}

function onPage(value) {
  page.value = value
  load()
}

function onSize(value) {
  pageSize.value = value
  page.value = 1
  load()
}

onMounted(async () => {
  if (route.query.session_id) {
    filters.session_id = Number(route.query.session_id)
  }
  courses.value = await listCourses()
  await load()
})
</script>

<style scoped>
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.emotion-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
