import http from '@/service/http'

// ============================================================
// v2 重构接口层(对应重构模块)
// 后端统一信封 { status, code, message, data },http.js 已解出 data.data
// ============================================================

export const getTrendMonthly = () => http.get('/trend/monthly')
export const getTrendDaily = () => http.get('/trend/daily')

export const getDetectSeries = () => http.get('/detect/series')
export const getDetectDay = (day) => http.get(`/detect/day/${day}`)

export const getWarningRecords = (params) => http.get('/warning/records', params)
export const getWarningDay = (day) => http.get(`/warning/day/${day}`)

export const getDiagnoseSeries = () => http.get('/diagnose/series')
export const getDiagnoseDay = (day) => http.get(`/diagnose/day/${day}`)
