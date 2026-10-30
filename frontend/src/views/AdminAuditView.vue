<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">审计日志</h1>
        <p class="page-sub">
          记录建号、名单变更、停用与导出等关键操作。日志不含密码、令牌与服务密钥。
        </p>
      </div>
      <el-button text @click="load" :loading="loading">刷新</el-button>
    </div>

    <section class="panel">
      <div class="filter-row">
        <el-select v-model="action" placeholder="全部操作" clearable style="width: 240px">
          <el-option v-for="item in ACTIONS" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" empty-text="暂无日志">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="action" label="操作" min-width="200" />
        <el-table-column label="目标" width="160">
          <template #default="{ row }">
            {{ row.target_type ? `${row.target_type}#${row.target_id}` : '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="180">
          <template #default="{ row }">{{ row.detail || '—' }}</template>
        </el-table-column>
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="row.result === 'SUCCESS' ? 'success' : 'danger'" size="small" effect="light">
              {{ row.result === 'SUCCESS' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actor_id" label="操作者 ID" width="110">
          <template #default="{ row }">{{ row.actor_id ?? '系统' }}</template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          layout="total, prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="onPage"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listAuditLogs } from '@/api/admin'
import { formatDateTime } from '@/stores/dict'

const ACTIONS = [
  'ADMIN_CREATE_USER',
  'ADMIN_SET_USER_STATUS',
  'ADMIN_CREATE_COURSE',
  'ADMIN_CREATE_SESSION',
  'ADMIN_UPDATE_SESSION',
  'ADMIN_UPDATE_SCHEDULE',
  'EXPORT_EMOJI'
]

const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const action = ref(null)

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (action.value) params.action = action.value
    const data = await listAuditLogs(params)
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

function onPage(value) {
  page.value = value
  load()
}

onMounted(load)
</script>

<style scoped>
.filter-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
