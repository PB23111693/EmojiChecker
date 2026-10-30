<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">多维统计</h1>
        <p class="page-sub">
          按课程、班级与时间范围汇总。导出使用与当前查询完全相同的筛选条件。
        </p>
      </div>
      <el-button :loading="exporting" :disabled="total === 0" @click="exportFile">
        导出 CSV
      </el-button>
    </div>

    <section class="panel">
      <div class="filter-row">
        <el-select v-model="filters.course_id" placeholder="全部课程" clearable style="width: 190px">
          <el-option v-for="item in courses" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="filters.class_name" placeholder="全部班级" clearable style="width: 170px">
          <el-option
            v-for="item in classOptions"
            :key="item.class_name"
            :label="`${item.class_name} / ${item.session_count} 节`"
            :value="item.class_name"
          />
        </el-select>
        <el-date-picker
          v-model="range"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 280px"
        />
        <el-select v-model="filters.source" placeholder="全部来源" clearable style="width: 150px">
          <el-option label="手动" value="MANUAL" />
          <el-option label="AI" value="AI" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button text @click="reset">重置</el-button>
      </div>

      <div class="metric-row">
        <div class="metric">
          <div class="metric-label">记录总数</div>
          <div class="metric-value">{{ total }}</div>
          <div class="metric-note">当前筛选条件</div>
        </div>
        <div class="metric">
          <div class="metric-label">手动反馈</div>
          <div class="metric-value">{{ stats?.manual_total ?? 0 }}</div>
          <div class="metric-note">按次数统计</div>
        </div>
        <div class="metric">
          <div class="metric-label">AI 观察</div>
          <div class="metric-value">{{ stats?.ai_total ?? 0 }}</div>
          <div class="metric-note">同一人跨帧重复计数</div>
        </div>
        <div class="metric">
          <div class="metric-label">参与学生</div>
          <div class="metric-value">{{ stats?.participants ?? 0 }}</div>
          <div class="metric-note">手动记录去重人数</div>
        </div>
      </div>
    </section>

    <div class="grid-2" style="margin-top: 16px">
      <section class="panel">
        <div class="panel-head">
          <h2 class="panel-title">表情分布</h2>
          <span class="panel-hint">分母为当前条件记录总数</span>
        </div>
        <ChartBox v-if="total > 0" :option="distributionChart" height="280px" />
        <div v-else class="empty-hint">当前条件下没有记录，不计算占比。</div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2 class="panel-title">分钟趋势</h2>
          <span class="panel-hint">按观测时间聚合，空桶为 0</span>
        </div>
        <ChartBox v-if="trend.length" :option="trendChart" height="280px" />
        <div v-else class="empty-hint">暂无趋势数据。</div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import ChartBox from '@/components/ChartBox.vue'
import { createStatisticsController } from '@/controllers/statisticsController'
import { EMOTIONS } from '@/stores/dict'

// 页面控制器负责筛选、查询与导出，View 只保留图表配置与模板。
const {
  courses,
  classOptions,
  stats,
  total,
  range,
  exporting,
  filters,
  trend,
  load,
  reset,
  exportFile,
  init
} = createStatisticsController()

const distributionChart = computed(() => {
  const items = stats.value?.distribution || []
  const values = EMOTIONS.map((emotion) => {
    const found = items.find((item) => item.emotion === emotion.value)
    return found ? found.count : 0
  })
  return {
    grid: { left: 44, right: 20, top: 20, bottom: 30 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: EMOTIONS.map((item) => item.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d9dee3' } }
    },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#eef1f4' } } },
    series: [
      {
        type: 'bar',
        barMaxWidth: 40,
        data: values.map((value, index) => ({
          value,
          itemStyle: { color: EMOTIONS[index].color, borderRadius: [4, 4, 0, 0] }
        }))
      }
    ]
  }
})

const trendChart = computed(() => ({
  grid: { left: 44, right: 20, top: 30, bottom: 30 },
  tooltip: { trigger: 'axis' },
  legend: { right: 0, top: 0, itemWidth: 10, itemHeight: 10 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: trend.value.map((item) => item.bucket),
    axisTick: { show: false },
    axisLine: { lineStyle: { color: '#d9dee3' } }
  },
  yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#eef1f4' } } },
  series: [
    {
      name: '手动',
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: trend.value.map((item) => item.manual),
      lineStyle: { width: 2, color: '#2f6f5e' },
      areaStyle: { color: 'rgba(47, 111, 94, 0.10)' }
    },
    {
      name: 'AI',
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: trend.value.map((item) => item.ai),
      lineStyle: { width: 2, color: '#a8722f', type: 'dashed' }
    }
  ]
}))

onMounted(init)
</script>

<style scoped>
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}
</style>
