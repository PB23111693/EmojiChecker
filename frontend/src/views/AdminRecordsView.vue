<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">记录明细</h1>
        <p class="page-sub">
          查看全部手动与 AI 记录。手动记录关联学生账号，AI 记录固定匿名；两者来源与置信度分别显示。
        </p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <section class="panel">
      <div class="filter-row">
        <el-select v-model="filters.course_id" placeholder="全部课程" clearable style="width: 180px">
          <el-option v-for="item in courses" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="filters.class_name" placeholder="全部班级" clearable style="width: 160px">
          <el-option
            v-for="item in classOptions"
            :key="item.class_name"
            :label="item.class_name"
            :value="item.class_name"
          />
        </el-select>
        <el-date-picker
          v-model="range"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
        />
        <el-select v-model="filters.source" placeholder="全部来源" clearable style="width: 130px">
          <el-option label="手动" value="MANUAL" />
          <el-option label="AI" value="AI" />
        </el-select>
        <el-select v-model="filters.emotion" placeholder="全部表情" clearable style="width: 140px">
          <el-option
            v-for="item in EMOTIONS"
            :key="item.value"
            :label="`${item.icon} ${item.label}`"
            :value="item.value"
          />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button text @click="reset">重置</el-button>
      </div>

      <el-table :data="rows" v-loading="loading" empty-text="当前条件下没有记录">
        <el-table-column label="观测时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.observed_at) }}</template>
        </el-table-column>
        <el-table-column prop="course_name" label="课程" min-width="150" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column label="学生" width="130">
          <template #default="{ row }">{{ row.username || '匿名' }}</template>
        </el-table-column>
        <el-table-column label="表情" width="120">
          <template #default="{ row }">
            {{ emotionMeta(row.emotion).icon }} {{ emotionMeta(row.emotion).label }}
          </template>
        </el-table-column>
        <el-table-column label="来源" width="90">
          <template #default="{ row }">
            <el-tag :type="row.source === 'AI' ? 'warning' : 'success'" size="small" effect="light">
              {{ SOURCE_LABEL[row.source] || row.source }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="100">
          <template #default="{ row }">
            {{ row.confidence == null ? '—' : Number(row.confidence).toFixed(3) }}
          </template>
        </el-table-column>
        <el-table-column label="设备" width="140">
          <template #default="{ row }">{{ row.device_id || '—' }}</template>
        </el-table-column>
        <el-table-column prop="event_id" label="事件编号" min-width="240" show-overflow-tooltip />
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="changePage"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { createRecordsController } from '@/controllers/recordsController'
import { EMOTIONS, emotionMeta, formatDateTime, SOURCE_LABEL } from '@/stores/dict'

const {
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
} = createRecordsController()

function search() {
  page.value = 1
  load()
}

onMounted(init)
</script>

<style scoped>
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
