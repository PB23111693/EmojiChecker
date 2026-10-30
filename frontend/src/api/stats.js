import http from './http'

export const fetchDashboard = (sessionId) =>
  http.get('/dashboard/realtime', { params: { session_id: sessionId } })

export const fetchStatistics = (params) => http.get('/statistics', { params })

function filenameFrom(headers) {
  const disposition = headers?.['content-disposition'] || ''
  const match = /filename="?([^";]+)"?/.exec(disposition)
  return match ? match[1] : `emoji_records.csv`
}

export async function exportCsv(params) {
  const response = await http.get('/admin/emoji/export', {
    params,
    responseType: 'blob'
  })
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filenameFrom(response.headers)
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
  return Number(response.headers['x-export-rows'] || 0)
}
