import http from './http'

export const listCourses = () => http.get('/courses')
export const createCourse = (payload) => http.post('/admin/courses', payload)

export const listSessions = (params) => http.get('/sessions', { params })
export const getSession = (id) => http.get(`/sessions/${id}`)
export const createSession = (payload) => http.post('/admin/sessions', payload)
export const updateSession = (id, payload) => http.patch(`/admin/sessions/${id}`, payload)

export const listMembers = (id) => http.get(`/admin/sessions/${id}/members`)
export const saveMembers = (id, userIds) =>
  http.put(`/admin/sessions/${id}/members`, { user_ids: userIds })

export const listClasses = () => http.get('/admin/classes')
export const listTeachers = () => http.get('/admin/teachers')
