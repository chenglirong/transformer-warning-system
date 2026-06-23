# 第 6-15 周开发规划

> **职责**:周计划 + 模块进度盘点。「继续开发」先读这里定位当前该做什么。
> 起点:2026/06/02(第 6 周周一) | 终点:第 15 周答辩
> 节奏:每天可投入开发
> 最近更新:已对齐 EDA 后的数据决策(D-008/D-015),修正早期"744 行/Fault 列"等过期假设

## 现状盘点(截至 2026-06-12,第 7 周)

| 模块 | 状态 | 已有产物 |
|------|------|---------|
| 模块 1 数据 | ✅ | `synthesis.py` → 360 行单设备时序;`labeled_iec.csv`(IEC 打标);工况周末模式 bug 已修(D-019) |
| 模块 2 特征 | ✅ | `features.py`(48 特征);`featured_timeseries.csv` |
| 前端联调 | ✅ | vite proxy + `api/data.py`(已守系统边界,只回 is_abnormal) |
| 模块 3 检测 | ✅ | 三方法齐全 + `compare_detection.py` + 混淆矩阵图 + 后端 `/api/detect/*`(D-020/021);DetectionView 全接真(D-039:三方法投票表/删PCA/补CO₂/判定取后端/三比值方法论说明)|
| 模块 4 预测 | ✅ | `predict/` + `train_lstm.py`/`compare_predict.py` + `test_predict.py`(14 用例)+ `/api/predict/compare` + PredictionView 接真。实测 ARIMA 优于 LSTM(D-027~031;D-044 新数据重跑:ARIMA 胜 6/7,MAE 148 vs 160)|
| 模块 5 决策 | ✅ | `warning/`(rules.yaml/engine/dedup)+ `test_warning.py`(20 用例)+ `backtest.py` + `/api/warning/backtest` + AlertsView 工单工作台(D-032~035)。误报率 74.4%(D-045 补 blue 档;D-044 全链路重跑为 73.2%;CO/CO₂ 改 §10.2.3.1 比值法 C-02);残余误判为早期/轻微异常边界样本(D-044);四级分级 blue 档由趋势规则 T-03/T-04 触发(D-045)|
| 模块 6 Agent | ✅ | `agent/`(tools 4工具/prompt ReAct 5步/runner 执行+降级)+ `/api/agent/run` + `run_agent_demo.py` 预跑落盘 7 条 + AlertsView 工单轨迹/通知接真(D-041,提前至第7周)。ReAct 跑通约13s;边界双保险(Prompt+黑名单)实测捕获过 LLM 越界 |
| 模块 7 大屏 | ✅ | Dashboard/Detection 接真(D-022/023/025);Prediction 据实改形接真(D-031:ARIMA 胜);Alerts 预警工单工作台(D-035:全量228条+分页+筛选/排序/搜索;详情拆预警信息+`AgentTrace.vue`[ReAct三要素,模块6接真]+AI通知示意块D-037);**Analysis 据实重做「三层数据体系」(D-038:回归原始意图非评测页;删 IEC 故障码越界块;第1层七气体+第2层特征工程(总烃/产气速率/三比值,补展示缺口)+第3层工况全接真;后端F1扩 `/data/latest` 加 features;摘规划中横幅)**;**模块7 全页接真闭环,无规划中横幅**(仅 Agent 轨迹/AI通知挂示意标待模块6) |

## 全局视图

| 阶段 | 周次 | 主题 | 对应论文模块 |
|------|------|------|------------|
| 一 | 第 6 周 | 数据底座 + 后端骨架 | 模块 1、2 |
| 二 | 第 7 周 | 异常检测 | 模块 3 |
| 三 | 第 8 周 | **中期检查** + 前后端联调 | 整合 |
| 四 | 第 9-10 周 | LSTM 预测 ⭐ | 模块 4 |
| 五 | 第 11-12 周 | 预警决策 ⭐ | 模块 5 |
| 六 | 第 13 周 | LangChain Agent ⭐⭐⭐ | 模块 6 |
| 七 | 第 14-15 周 | 系统完善 + 论文 + 答辩 | 模块 7 + 论文 |

---

## 阶段一:数据底座(第 6 周,本周 6/2-6/8)

| 日期 | 任务 | 交付 |
|------|------|------|
| 6/2 周一 | ① 申请通义千问 API key<br>② 搭 BE 项目骨架(FastAPI + SQLite) | `http://localhost:8000/docs` 可访问 |
| 6/3 周二 | EDA:探索原始 743 行快照,搞清缺失值/分布/Fault 可用性 | `scripts/eda.py` + `figures/` |
| 6/4 周三 | 设计 + 实现时序合成器 | `data/synthetic_timeseries.csv` |
| 6/5 周四 | 工况模拟(油温/负载/环温)+ 数据入库 | SQLite `.db` 文件 |
| 6/6 周五 | 特征工程模块 | `BE/app/algorithms/features.py` |
| 6/7-6/8 周末 | 前端 → API → SQLite 最小闭环 | Dashboard 显示真实数据 |

**🎯 周末交付**:Dashboard 所有 KPI 来自 SQLite 真实数据。

---

## 阶段二:异常检测(第 7 周,6/9-6/15)

| 任务 | 输出 | 状态 |
|------|------|------|
| 阈值法(国标 DL/T 722) | `algorithms/detect/threshold.py` | ✅ |
| 三比值法(DL/T 722-2014) | `algorithms/detect/iec.py` | ✅ |
| Isolation Forest | `algorithms/detect/iforest.py` | ✅ |
| 三方法对比实验(以合成真值 fault_state 为基准,D-020) | `scripts/compare_detection.py` | ✅ |
| 准确率/召回率/误报率对比表 → 论文素材 | 表格 + 混淆矩阵图(`figures/detection_confusion.png`) | ✅ |
| 检测 API(后端) | `/api/detect/methods/{id}` + `/_internal/compare`;共享 `detect/metrics.py` | ✅ |
| DetectionView 对接(前端) | FE 调用 `/api/detect/*` 渲染三方法对比 | ✅ 全页接真(D-039):左侧指标对比(D-022)+ 混淆矩阵;右侧近7日三方法逐日投票表接 `/detect/recent`、阈值表 5 项补齐 CO₂ 接 latest 真值、判定取后端 exceeded(方案C 渐进档)、三比值编码块加方法论+边界说明;删 PCA 散点(D-030 据实不硬做)+ 删 demo-badge 杜撰数据 |
| 算法层单元测试 | `tests/test_detect.py`(pytest,17 用例覆盖三检测器 + metrics 契约与边界) | ✅ |

**🎯 基准说明**(D-020 修订;D-044 更新打标口径):原始 `Fault` 列 97.6% 未标注(D-008),不可用。**最终以合成时序的真实状态标签 `fault_state` 为 ground truth**,三方法(阈值/三比值/IF)平等评估。`fault_state` 由国标 DL/T 722-2014 打标定义:表3 注意值定健康/异常二分、表7 三比值法细分故障类型(仅用于合成器状态库分组,不充当对比基准,避免"自己跟自己比")。

**⚠️ 系统边界**:对比实验内部可按 fault_state 故障类型分组分析,但论文表格与大屏只呈现**二分类(is_abnormal)指标**,绝不暴露具体故障类型。

---

## 阶段三:中期检查(第 8 周,6/16-6/22)

**这周不开发新功能**,做整合:

- 把阶段一、二的成果完整对接到前端
- 准备中期检查材料(进度报告 + Demo)
- 处理一切积压的小问题

**🎯 中期交付**:数据 → 后端 API → 前端真实展示的最小闭环全通。

---

## 阶段四:LSTM 预测(第 9-10 周,6/23-7/6)⭐核心

> **⏩ 提前启动**(2026-06-10,第 7 周):异常检测收尾后提前介入本核心模块,为最高风险项留缓冲。架构定调「离线训练 + 在线推理」,框架/环境路线锁定见 **D-027**。

| 任务 | 输出 | 状态 |
|------|------|------|
| 第 9 周初:升级 Python 3.11 + 装 TensorFlow(D-003) | 环境就绪(3.11.12 + TF 2.16.2 + Keras 3.14.1;Intel mac 用标准 tensorflow)| ✅ 提前完成 D-027 |
| 滑窗造样本(过去 30 天 → 第 31 天,单步) | `algorithms/predict/dataset.py` | ✅ 阶段 B1(D-028) |
| ARIMA 基线(7 气体 for 循环) | `algorithms/predict/arima.py` | ✅ 阶段 B2(D-029) |
| LSTM 多输出回归 `Sequential([LSTM(64), Dense(7)])` | `algorithms/predict/lstm.py` + `lstm.h5`(加载须 `compile=False`,见 D-027 踩坑)| ✅ 阶段 B1(D-028,推理模块)+ `train_lstm.py` 已训练落盘 |
| 滚动预测(迭代 3 次 → 1-3 天) | `algorithms/predict/rolling.py` | ✅ 阶段 B2(D-029) |
| 训练脚本(离线,落盘 `.h5`+scaler) | `scripts/train_lstm.py` | ✅ 阶段 B1(D-028,已跑通) |
| 对比实验(MAE/RMSE/MAPE) | `scripts/compare_predict.py` + 7 子图(`figures/`) | ✅ 阶段 B2(D-029;D-044 重跑 ARIMA 胜 6/7)|
| 算法层单元测试 | `tests/test_predict.py`(pytest,14 用例覆盖 dataset/arima/rolling 契约与边界;rolling 用 stub model 不依赖 .h5)| ✅ 阶段 B 收尾 |
| PredictionView 对接 + 摘「规划中」横幅(D-026)| `/api/predict/compare` + predict_eval.json 落盘 | ✅ 阶段 C/D(D-031 翻转 ARIMA 胜;D-036 补回滚动预测块:tab 切 LSTM 回灌/ARIMA 多步 + 气体可切换,接真)|

**⚠️ 风险预案**(论文已写):
- 第 9 周末必须能"跑通"(loss 下降即可)
- 第 10 周再调精度
- 跑不通启用论文里的兜底叙事(改写为"ARIMA 在该数据集上更稳健")

---

## 阶段五:预警决策(第 11-12 周,7/7-7/20)⭐核心

> **⏩ 提前启动**(2026-06-11,第 7 周):模块 4 提前完工后顺势启动。本轮做**算法核心**(用户选),回测/API/前端留下一轮。**软规则的预测源 = ARIMA**(承 D-029 实测更稳健,见 D-032)。

| 任务 | 输出 | 状态 |
|------|------|------|
| 规则引擎核心(YAML 配置化) | `algorithms/warning/rules.yaml` | ✅ B1(D-032) |
| 三类规则:硬规则、软规则、组合规则 | `algorithms/warning/engine.py` | ✅ B1(D-032,软规则用 ARIMA)|
| 四级分级(红橙黄蓝) | 同上(LEVEL_ORDER 取最高) | ✅ B1(D-032) |
| 误报控制:连续 N 次触发 + 24h 去重 | `algorithms/warning/dedup.py` | ✅ B1(D-032) |
| 算法层单元测试 | `tests/test_warning.py`(17 用例) | ✅ B1(D-032) |
| 历史回测(360 天合成时序) | `scripts/backtest.py` + `warning_backtest.json` + 图 | ✅ B2(D-033;D-044 重跑误报率 73.2%/召回 0.65,残余为早期异常边界样本;D-045 补 blue 档后 74.4%)|
| AlertsView 对接 | `/api/warning/backtest` + 接真 + 摘横幅 | ✅ C(D-034,工单接真+清越界+Agent标规划中)|

**🎯 回测基准**(D-033 修订):原始快照无时间维,无法回测时序预警。改用 **360 天合成时序**,以**合成真值 `fault_state`** 算 TP/FP/FN(与检测模块 D-020 同一基准)→ 论文素材。当日对齐口径;软规则预测源 ARIMA(D-032)。CO/CO₂ 不再设绝对硬规则,改 §10.2.3.1 CO₂/CO 比值组合判据(D-044)。

---

## 阶段六:LangChain Agent(第 13 周,7/21-7/27)⭐⭐⭐最大创新

严格按论文规划(354-371 行),**不要扩展**。**已提前至第 7 周完成(D-041)**:

| 任务 | 输出 | 状态 |
|------|------|------|
| 4 个 `@tool` 封装 | `agent/tools.py`(取数/检测/预测/规则,各复用已验证算法入口)| ✅ |
| ReAct Prompt 模板(写死 5 步)| `agent/prompt.py`(取数→检测→预测→规则→生成通知 + 边界硬约束)| ✅ |
| AgentExecutor 执行 | `agent/runner.py`(ChatTongyi qwen-plus + create_react_agent;ReAct 实测约 13s)| ✅ |
| 降级处理(Agent 失败 → 纯 Pipeline)| 同上(失败/超步/通知越界 → 串行调工具 + 模板通知,status=fallback)| ✅ |
| 通知边界双保险(守 D-008)| Prompt 禁越界词 + Final Answer 落盘前黑名单校验(实测捕获过 LLM「停运」越界)| ✅ |
| 预跑落盘(承 D-027 在线轻量)| `scripts/run_agent_demo.py` 离线跑 7 条代表性工单(各等级+最新日)→ `data/agent_runs.json` + AgentRun 表 | ✅ |
| Agent 执行轨迹接入 **AlertsView 工单详情**(点单追溯,D-035 纠正)| `/api/agent/run/{id}?on=` + `getAgentRun`;AlertsView/AgentTrace.vue 接真 + 去示意标 + 未预跑占位 | ✅ |

**⚠️ 偏差说明**:论文原写「AgentExecutor + **定时调度**」,实际做的是**预跑脚本离线触发**(承 D-027 在线轻量:ReAct 调 LLM 约 13s 不进请求路径),未做定时器。定时调度如答辩需要再补,当前以离线预跑覆盖代表性工单。

**✅ 提前验证**:LangChain hello world 已跑通(ChatTongyi + ReAct 链路),API key/环境 OK。

---

## 阶段七:系统完善 + 论文(第 14-15 周,7/28-8/10)

- 替换所有剩余的前端静态数据
- Agent 执行可视化(5 步状态展示)
- 论文初稿 → 终稿
- 答辩 PPT + **Demo 录屏**(防现场环境出问题)

---

## 进度更新约定

- 每周开始时回看本文件,确认是否需要调整
- 每完成一个任务,在对应行打 ✅
- 任何延期/提前/砍掉的任务,**同步更新到 [05-decisions-log.md](./05-decisions-log.md)**
