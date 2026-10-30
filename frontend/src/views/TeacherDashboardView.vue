<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">课堂看板</h1>
        <p class="page-sub">
          手动反馈与 AI 观察分区呈现，两者分母不同，不合并为单一情绪得分。
        </p>
      </div>
      <div class="head-actions">
        <el-select
          v-model="courseId"
          placeholder="选择课程"
          style="width: 190px"
          @change="onCourseChange"
        >
          <el-option v-for="item in courses" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select
          v-model="sessionId"
          placeholder="选择课堂"
          style="width: 230px"
          :disabled="!courseId"
          @change="onSessionChange"
        >
          <el-option
            v-for="item in sessions"
            :key="item.id"
            :label="`${item.class_name} · ${shortTime(item.start_at)}`"
            :value="item.id"
          />
        </el-select>
      </div>
    </div>

    <div v-if="!sessionId" class="panel empty-hint">
      请选择课程与课堂。没有可选课堂时，先由管理员创建课堂并安排名单。
    </div>

    <template v-else>
      <section class="panel status-strip">
        <div class="status-main">
          <div class="course">{{ dashboard?.course_name || session?.course_name }}</div>
          <div class="muted">
            {{ dashboard?.class_name || session?.class_name }}
            <span v-if="session?.room"> · 教室 {{ session.room }}</span>
            <span v-if="session"> · {{ formatTimeRange(session.start_at, session.end_at) }}</span>
          </div>
        </div>
        <div class="status-side">
          <el-tag :type="statusMeta(session?.status || dashboard?.status).type" round>
            {{ statusMeta(session?.status || dashboard?.status).label }}
          </el-tag>
          <span class="muted">更新于 {{ lastSuccessLabel }}</span>
          <el-tag v-if="updateFailed" type="danger" effect="plain" size="small">更新失败</el-tag>
        </div>
      </section>

      <div class="grid-2" style="margin-top: 16px">
        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">手动反馈</h2>
            <span class="panel-hint">分母为反馈次数与名单人数</span>
          </div>
          <div class="metric-row">
            <div class="metric">
              <div class="metric-label">反馈次数</div>
              <div class="metric-value">{{ manual.total }}</div>
              <div class="metric-note">同一学生可多次提交</div>
            </div>
            <div class="metric">
              <div class="metric-label">参与学生</div>
              <div class="metric-value">{{ manual.participants }}</div>
              <div class="metric-note">按用户去重</div>
            </div>
            <div class="metric">
              <div class="metric-label">名单覆盖率</div>
              <div class="metric-value">{{ coverageText }}</div>
              <div class="metric-note">名单 {{ manual.member_count }} 人</div>
            </div>
          </div>
          <ChartBox :option="manualChart" height="240px" />
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2 class="panel-title">AI 观察</h2>
            <span class="panel-hint">同一人跨帧会重复计数</span>
          </div>
          <div class="metric-row">
            <div class="metric">
              <div class="metric-label">有效观察</div>
              <div class="metric-value">{{ ai.total }}</div>
              <div class="metric-note">通过阈值的人脸结果</div>
            </div>
            <div class="metric">
              <div class="metric-label">置信度阈值</div>
              <div class="metric-value">{{ ai.threshold.toFixed(2) }}</div>
              <div class="metric-note">低于阈值不入库</div>
            </div>
            <div class="metric">
              <div class="metric-label">最近有效样本</div>
              <div class="metric-value" style="font-size: 15px">
                {{ ai.last_observed_at ? formatDateTime(ai.last_observed_at).slice(11) : '暂无' }}
              </div>
              <div class="metric-note">
                {{ ai.last_observed_at ? '仅表示最近一次采样' : '最近 15 秒无有效样本' }}
              </div>
            </div>
          </div>
          <ChartBox :option="aiChart" height="240px" />
        </section>
      </div>

      <section class="panel" style="margin-top: 16px">
        <div class="panel-head">
          <h2 class="panel-title">分钟趋势</h2>
          <el-radio-group v-model="trendSource" size="small">
            <el-radio-button label="MANUAL">手动</el-radio-button>
            <el-radio-button label="AI">AI</el-radio-button>
          </el-radio-group>
        </div>
        <ChartBox v-if="trendPoints.length" :option="trendChart" height="260px" />
        <div v-else class="empty-hint">暂无数据。空桶按 0 处理，不填充中性情绪。</div>
      </section>

      <section class="panel" style="margin-top: 16px">
        <div class="panel-head">
          <h2 class="panel-title">参与学生</h2>
          <span class="panel-hint">点击查看该生在本课堂的手动记录</span>
        </div>
        <el-table :data="students" v-loading="studentLoading" empty-text="本课堂暂无手动反馈">
          <el-table-column prop="username" label="学生" min-width="160" />
          <el-table-column prop="record_count" label="反馈次数" width="120" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button text type="primary" @click="openStudent(row)">查看记录</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="620px">
      <el-table :data="dialogRows" v-loading="dialogLoading" empty-text="暂无记录">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.observed_at) }}</template>
        </el-table-column>
        <el-table-column label="表情" width="130">
          <template #default="{ row }">
            {{ emotionMeta(row.emotion).icon }} {{ emotionMeta(row.emotion).label }}
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ChartBox from '@/components/ChartBox.vue'
import { useDashboard } from '@/composables/useDashboard'
import {
  EMOTIONS,
  emotionMeta,
  formatDateTime,
  formatTimeRange,
  statusMeta
} from '@/stores/dict'

// 组合式函数负责状态、轮询、WebSocket 与数据加载；View 保留图表配置与模板。
const {
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
  onCourseChange,
  onSessionChange,
  openStudent
} = useDashboard()

function distributionOption(items, colorMap) {
  const values = EMOTIONS.map((emotion) => {
    const found = items.find((item) => item.emotion === emotion.value)
    return found ? found.count : 0
  })
  return {
    grid: { left: 40, right: 16, top: 20, bottom: 30 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: EMOTIONS.map((item) => item.label),
      axisLine: { lineStyle: { color: '#d9dee3' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#eef1f4' } }
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 38,
        data: values.map((value, index) => ({
          value,
          itemStyle: { color: colorMap[index], borderRadius: [4, 4, 0, 0] }
        }))
      }
    ]
  }
}

const manualChart = computed(() =>
  distributionOption(
    manual.value.distribution,
    EMOTIONS.map((item) => item.color)
  )
)

const aiChart = computed(() =>
  distributionOption(
    ai.value.distribution,
    EMOTIONS.map(() => '#2f6f5e')
  )
)

const trendChart = computed(() => {
  const key = trendSource.value === 'MANUAL' ? 'manual' : 'ai'
  return {
    grid: { left: 44, right: 20, top: 24, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trendPoints.value.map((item) => item.bucket),
      axisLine: { lineStyle: { color: '#d9dee3' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#eef1f4' } }
    },
    series: [
      {
        name: trendSource.value === 'MANUAL' ? '手动次数' : 'AI 观察次数',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: trendPoints.value.map((item) => item[key]),
        lineStyle: { width: 2, color: '#2f6f5e' },
        areaStyle: { color: 'rgba(47, 111, 94, 0.12)' }
      }
    ]
  }
})
</script>

<style scoped>
.head-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.status-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.course {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 2px;
}

.status-side {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
