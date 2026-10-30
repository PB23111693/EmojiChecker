import { createRouter, createWebHashHistory } from 'vue-router'
import { authStore, homeFor } from '@/stores/auth'

const routes = [
  { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/register', component: () => import('@/views/RegisterView.vue'), meta: { public: true } },
  {
    path: '/register/teacher',
    component: () => import('@/views/RegisterView.vue'),
    meta: { public: true, teacher: true }
  },
  {
    path: '/register/admin',
    component: () => import('@/views/RegisterView.vue'),
    meta: { public: true, admin: true }
  },
  {
    path: '/',
    component: () => import('@/components/AppLayout.vue'),
    children: [
      {
        path: 'student/sessions',
        component: () => import('@/views/StudentSessionsView.vue'),
        meta: { roles: ['STUDENT'], title: '我的课堂' }
      },
      {
        path: 'student/sessions/:id/feedback',
        component: () => import('@/views/FeedbackView.vue'),
        meta: { roles: ['STUDENT'], title: '课堂反馈' }
      },
      {
        path: 'student/history',
        component: () => import('@/views/HistoryView.vue'),
        meta: { roles: ['STUDENT'], title: '我的记录' }
      },
      {
        path: 'teacher/dashboard',
        component: () => import('@/views/TeacherDashboardView.vue'),
        meta: { roles: ['TEACHER', 'ADMIN'], title: '课堂看板' }
      },
      {
        path: 'admin/statistics',
        component: () => import('@/views/AdminStatisticsView.vue'),
        meta: { roles: ['ADMIN'], title: '多维统计' }
      },
      {
        path: 'admin/sessions',
        component: () => import('@/views/AdminSessionsView.vue'),
        meta: { roles: ['ADMIN'], title: '课程与课堂' }
      },
      {
        path: 'admin/users',
        component: () => import('@/views/AdminUsersView.vue'),
        meta: { roles: ['ADMIN'], title: '用户管理' }
      },
      {
        path: 'admin/audit',
        component: () => import('@/views/AdminAuditView.vue'),
        meta: { roles: ['ADMIN'], title: '审计日志' }
      },
      {
        path: 'profile',
        component: () => import('@/views/ProfileView.vue'),
        meta: { title: '个人设置' }
      }
    ]
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFoundView.vue') }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach((to) => {
  const loggedIn = Boolean(authStore.token)
  if (to.meta.public) {
    if (loggedIn && to.path === '/login') {
      return homeFor(authStore.user?.role)
    }
    return true
  }
  if (!loggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/') {
    return homeFor(authStore.user?.role)
  }
  const roles = to.meta.roles
  if (roles && !roles.includes(authStore.user?.role)) {
    return homeFor(authStore.user?.role)
  }
  return true
})

export default router
