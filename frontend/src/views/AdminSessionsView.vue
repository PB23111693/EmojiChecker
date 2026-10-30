<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">课程与课堂</h1>
        <p class="page-sub">
          课堂开始后时间、名单与阈值冻结；名单表示提交资格，不代表出勤。
        </p>
      </div>
      <el-button type="primary" :disabled="!currentCourse" @click="openSessionDialog()">
        新建课堂
      </el-button>
    </div>

    <div class="admin-grid">
      <section class="panel course-panel">
        <div class="panel-head">
          <h2 class="panel-title">课程</h2>
          <el-button text type="primary" @click="openCourseDialog">新建课程</el-button>
        </div>
        <div v-if="courses.length" class="course-list">
          <button
            v-for="item in courses"
            :key="item.id"
            type="button"
            class="course-item"
            :class="{ 'is-active': currentCourse?.id === item.id }"
            @click="selectCourse(item)"
          >
            <span class="course-name">{{ item.name }}</span>
            <span class="muted">{{ item.teacher_name }} · {{ item.session_count }} 节课</span>
          </button>
        </div>
        <div v-else class="empty-hint">暂无课程，先创建课程并指定教师。</div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2 class="panel-title">课堂</h2>
          <span class="panel-hint">{{ currentCourse ? currentCourse.name : '请先选择课程' }}</span>
        </div>

        <el-table :data="sessions" v-loading="loading" empty-text="该课程暂无课堂">
          <el-table-column prop="class_name" label="班级" width="130" />
          <el-table-column label="时间" min-width="200">
            <template #default="{ row }">{{ formatTimeRange(row.start_at, row.end_at) }}</template>
          </el-table-column>
          <el-table-column prop="room" label="教室" width="100">
            <template #default="{ row }">{{ row.room || '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusMeta(row.status).type" size="small" effect="light">
                {{ statusMeta(row.status).label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="名单" width="90">
            <template #default="{ row }">{{ row.member_count }} 人</template>
          </el-table-column>
          <el-table-column label="阈值" width="80">
            <template #default="{ row }">{{ Number(row.ai_threshold).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240">
            <template #default="{ row }">
              <div class="action-cell">
                <el-button text type="primary" :disabled="row.status !== 'PENDING'" @click="openMembers(row)">
                  名单
                </el-button>
                <el-button text :disabled="row.status !== 'PENDING'" @click="openSessionDialog(row)">
                  编辑
                </el-button>
                <el-button
                  text
                  :type="row.cancelled ? 'primary' : 'danger'"
                  :disabled="row.status !== 'PENDING' && row.status !== 'CANCELLED'"
                  @click="toggleCancel(row)"
                >
                  {{ row.cancelled ? '恢复' : '取消' }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <el-dialog v-model="courseDialog" title="新建课程" width="440px">
      <el-form label-width="80px">
        <el-form-item label="课程名称" required>
          <el-input v-model="courseForm.name" placeholder="例如 软件工程实践" />
        </el-form-item>
        <el-form-item label="授课教师" required>
          <el-select v-model="courseForm.teacher_id" placeholder="选择教师" style="width: 100%">
            <el-option
              v-for="item in teachers"
              :key="item.id"
              :label="item.username"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCourse">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="sessionDialog"
      :title="sessionForm.id ? '编辑课堂' : '新建课堂'"
      width="520px"
    >
      <el-form label-width="90px">
        <el-form-item label="班级" required>
          <el-input v-model="sessionForm.class_name" placeholder="例如 计科2101" />
        </el-form-item>
        <el-form-item label="教室">
          <el-input v-model="sessionForm.room" placeholder="可选" />
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-date-picker
            v-model="sessionForm.start_at"
            type="datetime"
            placeholder="选择开始时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间" required>
          <el-date-picker
            v-model="sessionForm.end_at"
            type="datetime"
            placeholder="选择结束时间"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="AI 阈值">
          <el-slider v-model="sessionForm.ai_threshold" :min="0.3" :max="0.95" :step="0.05" show-input />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sessionDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitSession">
          {{ sessionForm.id ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="memberDrawer" title="课堂名单" size="420px">
      <div class="stack-16">
        <el-input v-model="memberKeyword" placeholder="搜索学生" clearable />
        <div class="muted">
          已选 {{ selectedIds.length }} 人。名单保存后立即生效，课堂开始后不可修改。
        </div>
        <el-checkbox-group v-model="selectedIds" class="member-list">
          <el-checkbox
            v-for="item in filteredStudents"
            :key="item.id"
            :value="item.id"
            class="member-item"
          >
            {{ item.username }}
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="memberDrawer = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitMembers">保存名单</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { createSessionController } from '@/controllers/sessionController'
import { formatTimeRange, statusMeta } from '@/stores/dict'

// 页面控制器负责课程、课堂、名单的读取与提交，View 只保留模板。
const {
  courses,
  sessions,
  teachers,
  currentCourse,
  loading,
  submitting,
  courseDialog,
  sessionDialog,
  memberDrawer,
  memberKeyword,
  selectedIds,
  courseForm,
  sessionForm,
  filteredStudents,
  selectCourse,
  openCourseDialog,
  submitCourse,
  openSessionDialog,
  submitSession,
  toggleCancel,
  openMembers,
  submitMembers,
  init
} = createSessionController()

onMounted(init)
</script>

<style scoped>
.admin-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  align-items: start;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.course-item {
  text-align: left;
  border: 1px solid var(--line);
  background: #fbfcfd;
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font: inherit;
  color: inherit;
}

.course-item.is-active {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.course-name {
  font-weight: 600;
}

.action-cell {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
}

.action-cell :deep(.el-button + .el-button) {
  margin-left: 2px;
}

.member-list {
  display: flex;
  flex-direction: column;
  max-height: 52vh;
  overflow-y: auto;
}

.member-item {
  margin-right: 0;
  height: 34px;
}

@media (max-width: 1240px) {
  .admin-grid {
    grid-template-columns: 1fr;
  }
}
</style>
