import http from './http'

export const submitEmoji = (payload) => http.post('/emoji', payload)
export const listHistory = (params) => http.get('/emoji/history', { params })
export const listSessionStudents = (sessionId) =>
  http.get(`/sessions/${sessionId}/students`)
