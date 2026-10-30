import { reactive } from 'vue'

const TOKEN_KEY = 'se_token'
const USER_KEY = 'se_user'

function safeParse(raw) {
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export const authStore = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: safeParse(localStorage.getItem(USER_KEY))
})

export function setSession(token, user) {
  authStore.token = token
  authStore.user = user
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function setUser(user) {
  authStore.user = user
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  authStore.token = ''
  authStore.user = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function homeFor(role) {
  if (role === 'TEACHER') return '/teacher/dashboard'
  if (role === 'ADMIN') return '/admin/statistics'
  return '/student/sessions'
}

export function isLoggedIn() {
  return Boolean(authStore.token)
}
