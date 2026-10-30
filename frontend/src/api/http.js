import axios from 'axios'
import { ElMessage } from 'element-plus'
import { authStore, clearSession } from '@/stores/auth'

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 20000
})

http.interceptors.request.use((config) => {
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response
    }
    const body = response.data
    if (body && typeof body.code === 'number') {
      if (body.code === 0) {
        return body.data
      }
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body
  },
  (error) => {
    const status = error.response?.status
    const body = error.response?.data
    const message = body?.message || error.message || '网络异常'

    if (status === 401) {
      if (authStore.token) {
        clearSession()
        window.dispatchEvent(new CustomEvent('auth:expired'))
      }
      return Promise.reject(new Error(message))
    }

    if (status === 422 && Array.isArray(body?.errors)) {
      const detail = body.errors
        .slice(0, 3)
        .map((item) => item.msg || item.message || '')
        .filter(Boolean)
        .join('；')
      ElMessage.error(detail || message)
    } else if (status === 429) {
      ElMessage.warning(message)
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default http
