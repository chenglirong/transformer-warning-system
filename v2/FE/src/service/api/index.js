import http from '@/service/http'

// ============================================================
// v2 重构接口层 —— 待按新模块补齐(旧接口已清空)
// 后端统一信封 { status, code, message, data },http.js 已解出 data.data
// 规划(对应重构模块,实现时逐个补):
//   数据:   /data/timeseries、/data/snapshot ...
//   检测:   /detect(表A.3四档分级 + 两视角佐证)
//   诊断:   /diagnose(特征气体/三比值/Duval 倾向)
//   告警:   /warning(四档全报)
//   趋势:   /trend(产气速率 + 预)
//   Agent:  /agent(分析报告 + 决策建议)
// ============================================================

// 示例(占位,实现后端后启用):
// export const getTimeseries = (days = 360) => http.get('/data/timeseries', { days })
