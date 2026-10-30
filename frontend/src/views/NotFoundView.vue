<template>
  <div class="notfound">
    <div class="code">404</div>
    <p class="muted">页面不存在，或当前账号没有访问权限。</p>
    <el-button type="primary" @click="goHome">返回工作台</el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { authStore, homeFor } from '@/stores/auth'

const router = useRouter()

function goHome() {
  router.replace(authStore.token ? homeFor(authStore.user?.role) : '/login')
}
</script>

<style scoped>
.notfound {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.code {
  font-size: 64px;
  font-weight: 700;
  color: var(--brand);
  letter-spacing: 4px;
}
</style>
