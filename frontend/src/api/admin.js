import http from './http'

export const listUsers = (params) => http.get('/admin/users', { params })
export const createUser = (payload) => http.post('/admin/users', payload)
export const setUserStatus = (id, status) =>
  http.patch(`/admin/users/${id}/status`, { status })
export const listAuditLogs = (params) => http.get('/admin/audit-logs', { params })
