import http from '@/service/http'

// ============ 数据查询接口 ============

/** 全局概览(总台数 / 健康-异常二分类 / 历史健康率) */
export const getOverview = () => http.get('/data/overview')

/** 变压器列表(每台最新状态,只含 is_abnormal 二分类) */
export const getTransformers = () => http.get('/data/transformers')

/** 单台最新一条监测记录 */
export const getLatest = (transformerId) => http.get(`/data/latest/${transformerId}`)

/** 单台截止某日的最近 N 天时序(默认 30 天;end 缺省取最新日) */
export const getTimeseries = (transformerId, days = 30, end) =>
  http.get(`/data/timeseries/${transformerId}`, end ? { days, end } : { days })

/** 指定日期的三层数据快照(AnalysisView 日期切换用);on 缺省取最新日 */
export const getSnapshot = (transformerId, on) =>
  http.get(`/data/snapshot/${transformerId}`, on ? { on } : {})

/** 全部监测日期 + 二分类异常标记(日期选择器红点用,不含故障类型) */
export const getDates = (transformerId) => http.get(`/data/dates/${transformerId}`)

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

/**
 * 最近 N 天三方法(阈值/IEC/iForest)逐日检测 + 融合投票(≥2 异常→异常)。
 * 守边界:每天只回三方法 is_abnormal 二分类 + 投票,不回故障类型。
 * 返回 { transformer_id, days, vote_rule, daily:[{date,threshold,iec,iforest,vote_abnormal,is_abnormal}] }。
 */
export const getDetectRecent = (transformerId, days = 7) =>
  http.get(`/detect/recent/${transformerId}`, { days })

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

/**
 * 预警规则库全貌(规则库抽屉用)。读后端 rules.yaml(engine.load_rules)。
 * 守边界:只回 编号/判定项/等级/触发条件/message,不含故障类型。
 * 返回 { levels, groups:[{type,label,desc,rules:[{id,item,level,condition,message}]}], n_rules }。
 */
export const getWarningRules = () => http.get('/warning/rules')

// ============ Agent 接口(模块 6)============

/**
 * Agent 预跑 ReAct 预警轨迹(点单追溯:这条预警背后 Agent 怎么推出来的)。
 * 读后端 agent_runs.json 快照(scripts/run_agent_demo.py 离线落盘,D-027 在线轻量)。
 * on 传工单日期 YYYY-MM-DD(预跑按工单日 as_of 分析);缺省取最新一条。
 * 守边界:只回 等级/规则编号/趋势/响应级别,不回故障类型/健康评分/运维建议。
 * 返回 { transformer_id, as_of, status:'success'|'fallback', steps:[...],
 *        notice, duration_ms, fallback_reason }。该工单未预跑 → 404。
 */
export const getAgentRun = (transformerId, on) =>
  http.get(`/agent/run/${transformerId}`, on ? { on } : {})

/**
 * 已预跑 Agent 轨迹的工单日期列表(前端给「可追溯」工单卡片打标用)。
 * 预跑仅覆盖代表性工单,据此标记避免点到未预跑工单。返回 { dates: [...] }。
 */
export const getAgentDates = (transformerId) =>
  http.get(`/agent/dates/${transformerId}`)
