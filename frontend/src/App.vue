<template>
  <router-view />
</template>

<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clearSession } from '@/stores/auth'

const router = useRouter()

function handleExpired() {
  clearSession()
  ElMessage.warning('登录已失效，请重新登录')
  router.replace({ path: '/login' })
}

onMounted(() => window.addEventListener('auth:expired', handleExpired))
onBeforeUnmount(() => window.removeEventListener('auth:expired', handleExpired))
</script>
