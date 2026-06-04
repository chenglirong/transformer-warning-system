import http from '@/service/http'

// ============ 数据查询接口 ============

/** 全局概览(总台数 / 健康-异常二分类 / 历史健康率) */
export const getOverview = () => http.get('/data/overview')

/** 变压器列表(每台最新状态,只含 is_abnormal 二分类) */
export const getTransformers = () => http.get('/data/transformers')

/** 单台最新一条监测记录 */
export const getLatest = (transformerId) => http.get(`/data/latest/${transformerId}`)

/** 单台最近 N 天时序(默认 30 天) */
export const getTimeseries = (transformerId, days = 30) =>
  http.get(`/data/timeseries/${transformerId}`, { days })
