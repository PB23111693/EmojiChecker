<template>
  <div class="page feedback-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">课堂反馈</h1>
        <p class="page-sub">选择此刻最接近你感受的表情。提交后不可修改，可在个人记录中查看。</p>
      </div>
      <el-button text @click="router.back()">返回</el-button>
    </div>

    <el-skeleton v-if="!session" :rows="5" animated />

    <template v-else>
      <section class="panel session-brief">
        <div>
          <div class="course">{{ session.course_name }}</div>
          <div class="muted">
            {{ session.teacher_name }} · {{ session.class_name }}
            <span v-if="session.room"> · 教室 {{ session.room }}</span>
          </div>
          <div class="muted">{{ formatTimeRange(session.start_at, session.end_at) }}</div>
        </div>
        <el-tag :type="statusMeta(session.status).type" effect="light" round>
          {{ statusMeta(session.status).label }}
        </el-tag>
      </section>

      <el-alert
        v-if="session.status !== 'ONGOING'"
        class="stack-16"
        type="warning"
        :closable="false"
        show-icon
        title="当前不在可提交时间范围内"
        description="反馈仅在课堂进行中开放。课堂开始前与结束后提交都会被服务端拒绝。"
      />

      <section class="panel stack-16" style="margin-top: 16px">
        <div class="panel-head" style="margin-bottom: 0">
          <h2 class="panel-title">此刻的感受</h2>
          <span class="panel-hint">七个类别同时给出图标与文字，不依赖颜色区分</span>
        </div>

        <EmotionPicker v-model="emotion" />

        <div class="submit-row">
          <span class="muted">{{ hint }}</span>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            :disabled="!emotion || session.status !== 'ONGOING'"
            @click="submit"
          >
            确认提交
          </el-button>
        </div>
      </section>

      <el-result
        v-if="lastResult"
        class="panel"
        style="margin-top: 16px"
        icon="success"
        title="反馈已记录"
        :sub-title="`服务端时间 ${formatDateTime(lastResult.observed_at)}${lastResult.duplicate ? '，本次为重复提交的幂等返回' : ''}`"
      >
        <template #extra>
          <el-button @click="router.push('/student/history')">查看我的记录</el-button>
          <el-button type="primary" @click="reset">再记一次</el-button>
        </template>
      </el-result>
    </template>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmotionPicker from '@/components/EmotionPicker.vue'
import { useFeedback } from '@/composables/useFeedback'
import { formatDateTime, formatTimeRange, statusMeta } from '@/stores/dict'

const route = useRoute()
const router = useRouter()
const { session, emotion, submitting, lastResult, hint, load, submit, reset } = useFeedback(
  () => route.params.id
)

onMounted(load)
</script>

<style scoped>
.feedback-page {
  max-width: 820px;
}

.session-brief {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.course {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 4px;
}

.submit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-top: 1px solid var(--line);
  padding-top: 14px;
}

@media (max-width: 640px) {
  .submit-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
