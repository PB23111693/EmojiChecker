<template>
  <div class="app-shell">
    <aside class="app-aside">
      <div class="brand">
        <div class="brand-name">课堂情绪检查器</div>
        <div class="brand-sub">软件工程实践 · 课程大作业</div>
      </div>
      <el-menu :default-active="activeMenu" router class="side-menu">
        <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-foot muted">角色：{{ roleLabel }}</div>
    </aside>

    <div class="app-body">
      <header class="app-header">
        <div class="muted">{{ pageTitle }}</div>
        <el-dropdown trigger="click" @command="onCommand">
          <span class="user-chip">
            <el-icon><UserFilled /></el-icon>
            {{ user?.username || '未登录' }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人设置</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>
      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Calendar,
  DataAnalysis,
  Document,
  Setting,
  Tickets,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import { authStore, clearSession } from '@/stores/auth'
import { ROLE_LABEL } from '@/stores/dict'

const route = useRoute()
const router = useRouter()

const user = computed(() => authStore.user)
const roleLabel = computed(() => ROLE_LABEL[user.value?.role] || '未登录')
const pageTitle = computed(() => route.meta.title || '课堂情绪检查器')

const MENU_BY_ROLE = {
  STUDENT: [
    { path: '/student/sessions', label: '我的课堂', icon: Calendar },
    { path: '/student/history', label: '我的记录', icon: Tickets },
    { path: '/profile', label: '个人设置', icon: Setting }
  ],
  TEACHER: [
    { path: '/teacher/dashboard', label: '课堂看板', icon: DataAnalysis },
    { path: '/teacher/statistics', label: '多维统计', icon: DataAnalysis },
    { path: '/profile', label: '个人设置', icon: Setting }
  ],
  ADMIN: [
    { path: '/teacher/dashboard', label: '课堂看板', icon: DataAnalysis },
    { path: '/admin/statistics', label: '多维统计', icon: DataAnalysis },
    { path: '/admin/sessions', label: '课程与课堂', icon: Calendar },
    { path: '/admin/users', label: '用户管理', icon: User },
    { path: '/admin/records', label: '记录明细', icon: Document },
    { path: '/admin/audit', label: '审计日志', icon: Tickets },
    { path: '/profile', label: '个人设置', icon: Setting }
  ]
}

const menus = computed(() => MENU_BY_ROLE[user.value?.role] || [])
const activeMenu = computed(() => {
  if (route.path.startsWith('/student/sessions')) return '/student/sessions'
  return route.path
})

function onCommand(command) {
  if (command === 'logout') {
    clearSession()
    router.replace({ path: '/login' })
    return
  }
  if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.side-menu {
  border-right: none;
  padding: 8px;
  flex: 1;
}

.side-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin-bottom: 4px;
  height: 42px;
}

.aside-foot {
  padding: 12px 20px;
  border-top: 1px solid var(--line);
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
  outline: none;
}
</style>
