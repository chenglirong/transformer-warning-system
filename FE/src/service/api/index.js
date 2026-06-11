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

// ============ 趋势预测接口 ============

/**
 * LSTM vs ARIMA 验证段对比(指标 + 7 气体曲线 + loss 历史)。
 * 读后端 predict_eval.json 快照(训练时落盘,毫秒级)。
 * 实测结论:ARIMA 较 LSTM 更稳健(D-029),如实呈现。
 * 返回 { baseline, n_target_days, gases, overall, per_gas, series, loss_history }。
 */
export const getPredictCompare = () => http.get('/predict/compare')

// ============ 预警决策接口 ============

/**
 * 预警引擎历史回测(混淆矩阵 + 指标 + 四级分布 + 全量告警)。
 * 读后端 warning_backtest.json 快照(scripts/backtest.py 落盘)。
 * 守边界:只回 等级/规则编号/规则类型/响应级别/日期,不回故障类型/运维建议/置信度。
 * 返回 { baseline, n_days, confusion, metrics, level_distribution, n_alerts,
 *        alerts:[{date, level, rule_ids, rule_types, response, true_abnormal}] }。
 */
export const getWarningBacktest = () => http.get('/warning/backtest')
