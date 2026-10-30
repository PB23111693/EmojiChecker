<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">我的课堂</h1>
        <p class="page-sub">仅显示已安排给你的课堂。课堂进行中才可提交反馈。</p>
      </div>
      <el-button text @click="load" :loading="loading">刷新</el-button>
    </div>

    <el-radio-group v-model="filter" class="stack-16" style="margin-bottom: 16px">
      <el-radio-button value="ALL">全部</el-radio-button>
      <el-radio-button value="ONGOING">进行中</el-radio-button>
      <el-radio-button value="PENDING">未开始</el-radio-button>
      <el-radio-button value="ENDED">已结束</el-radio-button>
    </el-radio-group>

    <div v-if="visibleSessions.length" class="session-grid">
      <article v-for="item in visibleSessions" :key="item.id" class="session-card">
        <header class="session-head">
          <div>
            <div class="session-course">{{ item.course_name }}</div>
            <div class="muted">{{ item.teacher_name }} · {{ item.class_name }}</div>
          </div>
          <el-tag :type="statusMeta(item.status).type" effect="light" round>
            {{ statusMeta(item.status).label }}
          </el-tag>
        </header>

        <div class="session-meta">
          <span>{{ formatTimeRange(item.start_at, item.end_at) }}</span>
          <span v-if="item.room">教室 {{ item.room }}</span>
        </div>

        <footer class="session-foot">
          <span class="muted">本课反馈 {{ item.manual_count }} 条</span>
          <div class="session-actions">
            <el-button text @click="goHistory(item)">查看记录</el-button>
            <el-button
              type="primary"
              :disabled="item.status !== 'ONGOING'"
              @click="goFeedback(item)"
            >
              {{ item.status === 'ONGOING' ? '提交反馈' : '未开放' }}
            </el-button>
          </div>
        </footer>
      </article>
    </div>

    <div v-else class="panel empty-hint">
      {{ loading ? '正在加载……' : '暂无符合条件的课堂。请确认管理员已把你加入课堂名单。' }}
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listSessions } from '@/api/catalog'
import { formatTimeRange, statusMeta } from '@/stores/dict'

const router = useRouter()
const sessions = ref([])
const loading = ref(false)
const filter = ref('ALL')

const visibleSessions = computed(() => {
  const order = { ONGOING: 0, PENDING: 1, ENDED: 2, CANCELLED: 3 }
  const rows = sessions.value.filter((item) => filter.value === 'ALL' || item.status === filter.value)
  return [...rows].sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9))
})

async function load() {
  loading.value = true
  try {
    const data = await listSessions({ page: 1, page_size: 100 })
    sessions.value = data.items
  } finally {
    loading.value = false
  }
}

function goFeedback(item) {
  router.push(`/student/sessions/${item.id}/feedback`)
}

function goHistory(item) {
  router.push({ path: '/student/history', query: { session_id: String(item.id) } })
}

onMounted(load)
</script>

<style scoped>
.session-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.session-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.session-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.session-course {
  font-size: 16px;
  font-weight: 600;
}

.session-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #3e4a56;
}

.session-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--line);
  padding-top: 12px;
  margin-top: auto;
}

.session-actions {
  display: flex;
  gap: 4px;
}
</style>
