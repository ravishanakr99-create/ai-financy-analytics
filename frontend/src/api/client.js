/**
 * API client for FastAPI backend.
 *
 * baseURL resolution:
 * - Empty or unset VITE_API_URL → use relative path (Vite proxy in dev)
 * - VITE_API_URL set → use that URL (direct to backend, requires CORS)
 */

import axios from 'axios'

// Use relative path when empty → Vite proxies /api to backend (no CORS)
// Use full URL when set → direct backend call (CORS must allow frontend origin)
const baseURL = import.meta.env.VITE_API_URL || ''

const axiosInstance = axios.create({
  baseURL: baseURL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
})

// For FormData, let browser set Content-Type (multipart boundary)
axiosInstance.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    config.headers['Content-Type'] = undefined
  }
  return config
})

axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
      const base = error.config?.baseURL || ''
      const path = error.config?.url || ''
      const fullUrl = base.startsWith('http')
        ? `${base.replace(/\/$/, '')}${path.startsWith('/') ? path : '/' + path}`
        : `${window.location.origin}${base}${path}`
      error.message = `Backend unreachable. Check: (1) Backend running on port 8000? (2) Request URL: ${fullUrl}`
    }
    return Promise.reject(error)
  }
)

export const apiClient = {
  testConnection: () => axiosInstance.get('/test'),
  uploadReport: (files, metadata = {}) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    if (metadata.user_id) form.append('user_id', metadata.user_id)
    if (metadata.category) form.append('category', metadata.category)
    return axiosInstance.post('/reports/upload', form)
  },
  getReport: (reportId) => axiosInstance.get(`/reports/${reportId}`),
  getReportPdfUrl: (reportId) => {
    const base = import.meta.env.VITE_API_URL || '/api/v1'
    return `${base}/reports/${reportId}/pdf`
  },
}

// Keep `api` alias for backward compatibility
export const api = apiClient
