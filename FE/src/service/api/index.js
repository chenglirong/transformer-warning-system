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

// ============ 异常检测接口 ============

/**
 * 三方法对比指标(全量 360 天,基准=合成真值 fault_state,D-020/D-021)。
 * 注:走后端 /_internal/ 前缀,属算法评估口径,仅供 DetectionView 对比展示 /
 * 答辩 Demo,不是业务接口。返回 { baseline, n_samples, n_abnormal_truth, metrics }。
 */
export const getDetectCompare = () => http.get('/detect/_internal/compare')

/**
 * 单台最新一条监测数据的三方法检测(阈值/IEC)+ 投票结果。
 * 守边界:只回 is_abnormal + 阈值法超标气体名 + 投票,不回具体故障类型。
 */
export const getDetectMethods = (transformerId) =>
  http.get(`/detect/methods/${transformerId}`)
