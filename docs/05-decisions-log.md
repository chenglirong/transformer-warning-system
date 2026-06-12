# 关键决策日志

> **职责**:决策史——记「为什么这么做」(决策 + 理由 + 备选)。答辩遇到「为什么这么设计」翻这里。话术成稿见 08,实验分析见 07。
> 按时间倒序记录开发过程中的重大决策。新决策追加到顶部。

## 2026-06-12 数据弱可分性是核心约束(统一根因);数据基础维持+诚实声明局限

### D-040:四个「负面」结果统一根因=数据弱可分性;合成忠于原始数据;数据基础维持+主动声明局限(方案 A)

- **触发**:跑数发现**等权融合(≥2 票)打不过单一 iForest**——融合 acc=0.756/f1=0.569/fpr=0.204 vs iForest 0.803/0.608/0.130。弱方法(IEC 召回 0.407、阈值法 fpr 0.454)稀释了 iForest
- **根因=气体弱可分(量化)**:正常 vs 异常各气体可分性 d:CO **0.11**/C₂H₂ 0.29/C₂H₄ 0.41/H₂ 0.47/CH₄ 0.52/C₂H₆ 0.60/CO₂ 0.80,除 CO₂ 外全高度重叠;异常组总烃中位数 90(注意值 150),**66% 异常样本未超国标** → 合成异常多为早期/轻微潜伏故障,信号微弱
- **统一根因**:检测 60-80%、IEC 召回 40%、融合未优、预警 70% 误报(D-033)同一根因=弱可分(无清晰决策边界);ARIMA>LSTM(D-029)是独立根因=360 天小样本。四者非「没调好」,是数据固有约束的诚实反映
- **反证非合成失真**:原始 743 行 IEC 打标后可分性更低(C₂H₂ d=0.00),合成反而略高 → 弱可分是数据集 + DGA 早期故障固有性质。**故不改合成器**(硬调异常显著=失真)
- **数据集查证**(WebFetch dgadb 官网+GitHub):**无正式论文、无标注方法、来源不明**,`Fault` 列 97.6% 缺标(D-008),GT 靠自用 IEC 打标
- **决策(方案 A)**:数据基础维持现状,**论文主动声明局限**(来源不明/缺标/自打 GT/弱可分)+ 说明弥补(IEC 打标+可分性分析+合成保分布)。不换集、不加交叉验证(本科毕设成本权衡)
- **同步**:本条;DetectionView「融合避免误判」措辞改据实(D-039);`04` 答辩话术;`论文梳理` 修订 12

---

## 2026-06-12 DetectionView 遗漏据实处理:一致性表接真/删PCA/补CO₂/三比值说明/判定取后端

### D-039:DetectionView 多项据实改形——清最后的示意/杜撰,补国标完整性,判定口径统一后端

- **背景**:收尾 DetectionView 欠账(dev-plan:59「近7日表/PCA 散点仍示意」)
- **① 近7日一致性表接真**:新建 `/api/detect/recent/{id}?days=7`,三方法逐日 + 投票(≥2→异常)。iForest 全量 fit_predict 后取最近 N 天切片(同 `_internal/compare` 口径)。删原「逐渐恶化」假数据。真实数据自带好案例:3-25 两票判异常、3-21 阈值单方误报被否决
- **② PCA 散点删除**(用户选 D,承 D-030):原 `Math.random()` 杜撰点;真做需建 PCA 管线、价值低,据实删,混淆矩阵撑满左下
- **③ 阈值表补 CO₂**:原 4 行漏 CO₂,后端实为 5 项(+co2 10000),补齐
- **④ 三比值块加方法论说明**(用户要丰富):加「第1步比值→编码」+ 黄框边界说明(第2步编码→故障类型属诊断不输出;仅内部二分类用,召回约40%)。**红线:只讲方法零故障类型词**(复查 PASS)
- **⑤「当前值」→「最新日值」**:取最新一日真值非实时,改名免误解
- **⑥ 判定取后端(方案 C)**:超标权威取后端 `exceeded_gases`;未超标前端按占比细分 趋近(≥80%)/关注(≥50%)/正常(纯 UI 提示);断网兜底前端算
- **核验**:`/recent` curl 真实无 fault_state;CO₂ 接真;判定对齐后端;build 通过;无故障类型词;视觉用户确认 OK
- **同步**:本条;`02-dev-plan` 阶段二 DetectionView 行

---

## 2026-06-12 AnalysisView 据实重做为「三层数据体系」(方案 F,接真)

### D-038:AnalysisView 保留原始意图「三层数据体系」据实接真;删 IEC 故障码越界块;补上第2层特征工程展示缺口;消灭最后一个规划中横幅

- **背景**:AnalysisView 是模块 7 大屏唯一仍挂 `:planning` 横幅的页面。问题有二:① **越界**——Tier2 写死 `021 → 低温过热 (<300℃)`,把 IEC 三比值法推出的具体故障类型暴露在业务页面,违反系统刚性边界(IEC 仅内部用,dev-plan 第18行早列「删 IEC 编码越界展示」);② 三层指标用的是**开题报告阶段的静态 UI 原型数据**(算法未实现时先搭界面形态用),算法落地后未清理
- **方向纠偏(本轮关键)**:我先误判为「算法评测中心(方案 B)」,经用户两次质疑纠正:(a) 检测三方法对比 DetectionView 已全量接真、预测对比 PredictionView 已全量接真,Analysis 再做评测就是**重复**;(b) 那些静态数据是**开题报告的正当 UI 原型,不是 D-023 意义的「杜撰」**(杜撰指在已宣称接真的页面塞假数据冒充真实产出);(c) AnalysisView 的**原始设计意图是展示本研究监测的「三层数据体系」**(数据基础叙事),非算法结果。故回归原意图据实重做
- **用户拍板方案 F + 三层规格(用户给定)**:
  - **第1层 DGA 七气体(直接检测)**:H₂/CH₄/C₂H₆/C₂H₄/C₂H₂/CO/CO₂ —— 核心地位:LSTM 预测目标 + 预警核心依据
  - **第2层 衍生指标(特征工程计算)**:总烃、产气速率、三比值(CH₄/H₂、C₂H₂/C₂H₄、C₂H₄/C₂H₆) —— 补上特征工程产物此前前端无处展示的缺口
  - **第3层 运行工况(辅助判断)**:油温/温升速率、负载电流、环境温度 —— 辅助地位:为规则引擎提供上下文,不直接参与预测
- **守边界(红线)**:三比值**只显数值**(中性衍生指标,合规),**绝不显 IEC 编码与故障类型**(删 `021→低温过热`);页面无故障类型/健康评分/运维建议
- **据实接真(全三层有真值)**:`featured_timeseries.csv` 已含全部所需列——第1层气体、第2层 `total_hydrocarbon`/`ratio_*`/`*_rate_pct`、第3层 `oil_temp`/`load_current`/`ambient_temp`。**后端 F1**:扩展 `/data/latest/{id}` 增 `features` 字段(总烃/三比值/产气速率),一个端点回全三层同日快照
- **不重复结论**:DetectionView=算法**评测**(三方法指标对比);AnalysisView=数据**体系**(监测什么、三层如何分工喂给算法)。第1/3层与 Dashboard 有交集但角度不同(Dashboard=运行总览,Analysis=数据体系全貌+第2层特征产物)
- **预警回测指标去向**:D-035 从 Alerts 移出的回测混淆/四级分布,**与本页无关**(本页是数据体系非评测),其安放另议
- **日期回看(用户选方案 A)**:头部 `el-date-picker`,可回看 360 天任意一日(默认最新日),**异常日标红点**(`cell-class-name`,二分类 is_abnormal)。后端新增 `/data/snapshot/{id}?on=`、`/data/dates/{id}`(无 fault_state)、`/data/timeseries` 加 `end` 参数(曲线截止选中日)。答辩可切异常日演示(如 2024-04-19)
- **核验**:`/dates` 无 fault_state 泄露(原始响应+grep+字段全集三处核);`cell-class-name` 入参查 element-plus 源码实为原生 `Date`(否则红点不显);node 复刻 transform 于异常日正确;build 通过;视觉(深色日历)用户确认 OK
- **守边界**:`/dates`+红点只用 is_abnormal,不暴露 fault_state;深色样式限 `popper-class` 不污染他处
- **同步**:本条;`02-dev-plan` 模块7行;`论文梳理` 修订11

---

## 2026-06-11 AlertsView 补回 AI 预警通知块(示意数据)

### D-037:Alerts 工单详情补回「AI 预警通知」块,示意数据 + 规划中标

- **背景**:D-034 删 Alerts 通知块删过头(同 D-036 性质)。通知确属模块6(LLM生成),但论文模块7 明列「AI 预警通知展示 ⭐」,应同 AgentTrace 用示意+规划中标补回,不整块抹掉
- **实现**:工单详情右列底部加「AI 预警通知(LLM 生成)」块(flex 0.7),`noticeText` computed 按选中工单生成通知文本(等级/触发规则/预测趋势/响应级别/日期),带「模块6·第13周·示意数据」紫色标
- **守边界**:只含等级/规则/响应级别/趋势,**无故障类型/置信度/运维处置建议**;趋势措辞用 ARIMA(D-032)
- **核验**:`npm run build` 通过(AlertsView 13.41KB)
- **同步**:本条 D-037

---

## 2026-06-11 PredictionView 补回滚动预测块(LSTM/ARIMA tab 对比)

### D-036:滚动预测推理改 tab 切两模型 + 气体可切换,据实接真

- **背景**:用户发现 D-031 删 PredictionView 滚动预测块删过头了——当时该删的只是那组**杜撰数字**(D+1=3.42→4.05ppm)和 LSTM 创新点误导,但**滚动预测功能本身是真实能力**(rolling.py 已实现),不该整块删
- **用户定方案**:改 **tab 切换,LSTM 和 ARIMA 两个模型的滚动都展示** —— 与全页对比研究叙事一致,LSTM 数值离谱反成对比素材(印证局限),不回避
- **后端**:`compare_predict.py` 加滚动预测落盘——取最后 30 天历史,LSTM 用 `rolling_forecast` 迭代回灌、ARIMA 用 `forecast_arima(steps=3)` 原生多步,各出未来 1-3 天;连同最近 7 天真值落盘进 `predict_eval.json` 的 `rolling` 字段(history/lstm/arima)
- **前端**:PredictionView 右列加滚动预测块(flex 1.2)——**tab 切 LSTM 回灌 / ARIMA 多步**,**气体可切换**(下拉,复用 gasOptions),展示「最近 7 天真值 + 未来 3 天预测」曲线,预测段 markArea 高亮;默认 ARIMA(主力)。loss 块缩 flex 0.9 腾位
- **守边界**:据真接 `predict_eval.json`,非杜撰;两模型机制注脚说明(LSTM 回灌 vs ARIMA 原生多步)
- **核验**:compare_predict 重跑落盘 rolling;`npm run build` 通过(PredictionView 13.03KB)
- **同步**:本条 D-036;dev-plan 阶段四 PredictionView 行

---

## 2026-06-11 AlertsView 产品级重设计:工单工作台 + Agent 推理时间线(布局先行)

### D-035:Alerts 重设计为预警工单工作台 + AgentTrace 组件;纠正 Agent 归属;回测指标待迁 Analysis

- **背景**:用户从产品角度质疑 D-034 后的 Alerts:① 只展示最近 20 条(且恰全是同一规则 T-02,看不到 80 条红色)② 把回测评测指标和预警工单混在一起(受众不同)③ Agent 区块设计丑
- **Agent 归属纠正(连环查证)**:dev-plan 第 131 行原写「Agent 执行轨迹接入 AnalysisView」——查证发现**无论文依据**(论文模块7「Agent执行可视化」是独立 ⭐ 模块),且与 AnalysisView「三层指标看板」定位冲突。我前两轮被这行带着走没核实。**与用户确认最终定位:Agent 轨迹与工单一对一绑定**(点工单看这条预警背后 Agent 怎么推出来的),留 **AlertsView 工单详情**最合理,不拆独立页、不塞 Analysis
- **Agent 模块未开发 → 布局先行(用户拍板)**:本轮只做布局,用**模拟数据**把 Agent ReAct 展示设计专业,后续开发完接 `/api/agent/run`。模拟数据**带显眼「模块6·第13周·示意数据」标识**(承 P1 诚实原则 D-023)
- **后端铺垫(task 18/19)**:`backtest.py` 落盘从 `recent_alerts[-20:]` 改全量 `alerts`(228条,每条 date/level/rule_ids/rule_types/response/true_abnormal);warning API 透传(端到端验证 228条/80红)
- **新建 `FE/src/components/AgentTrace.vue`**:Agent ReAct 轨迹组件。顶部状态条(步数/总耗时/成功或降级 chip)+ 时间线(状态色点+连接线)+ 每步可展开 Thought/Action/Observation 三要素 + 失败降级高亮 + 「模块6·第13周·示意数据」紫色标。Timeline.vue 保持通用不动。模块6接真只改此组件数据源
- **`AlertsView.vue` 重写为工单工作台**:全量228条 + 前端分页(每页20)+ 规则类型筛选 + 时间/紧急度排序 + 日期/规则号搜索;详情拆「预警信息」(等级/规则编号/类型/响应级别)+ `<AgentTrace>`;**移除回测指标块**(数据仍在 warning API,下轮迁 Analysis)。模拟轨迹按工单等级映射(红/黄不同推理),forecast 用 ARIMA(D-032 非 LSTM)
- **守边界**:Agent 模拟数据带示意标(D-023);源码边界自查排除注释后无故障类型/置信度/运维处置词(D-008);轨迹用 ARIMA;不显「误报」(运维当下不知真值,回测命中分析归 Analysis 评测)
- **核验(独立,非桥接回执)**:`npm run build` 通过(AlertsView 12.76KB);node 复刻 — 全量228/12页、红色80(截断版看不到)、搜索 2025-03 命中26、硬规则筛选60;边界自查 PASS;onMounted 无重复 import
- **下轮**:AnalysisView 加「算法评测」tab 容纳迁出的回测 confusion/metrics/混淆矩阵(task 21)
- **同步**:本条 D-035;`02-dev-plan.md` 模块7大屏行 + 第131行 Agent 归属纠正;论文模块7 Agent 可视化形态(嵌工单详情点单追溯)记一笔

---

## 2026-06-11 模块 5 阶段 C:warning API + AlertsView 据实改形(D-030 第二例)

### D-034:AlertsView 工单接真 + 清越界/杜撰 + Agent 区块标规划中;摘横幅

- **背景**:模块 5 收口前端。AlertsView 原是 D-026 标「规划中」的设计稿,691 行,混了模块5(预警工单)+模块6(Agent 轨迹),且多处**越界 + 杜撰**:IEC 故障类型「低温过热/编码021」、运维建议「立即停运」、置信度 92%、LSTM 预测、编造的规则编号 R002/R005(与 rules.yaml 真实 H/S/T/C 不符)、整套 Agent ReAct 轨迹(模块6未开发)
- **方案(用户选 ③:接真预警 + Agent 标规划中)**,但加边界红线:Agent 区块即使标规划中,**越界/误导内容也必须清除**(IEC故障类型/置信度/LSTM 标规划中也不能留)
- **后端**:`app/api/warning.py`(`/api/warning/backtest` 读 warning_backtest.json,文件不存在 404);main.py 注册;`getWarningBacktest` 入 service/api
- **前端改形(AlertsView 全量重写,691→精简)**:
  - KPI:接 `level_distribution` 四级真值(红80/橙13/黄135/蓝0)+ 总数,可筛选
  - 工单列表:接 `recent_alerts`,据实映射(WO编号/日期/等级/**真实规则编号 H-S-T-C**/响应级别)。标题只说「触发哪些规则 + 规则类型」,**无故障类型/无运维建议**
  - **误报如实标注**:工单按 `true_abnormal` 标「命中真值/误报」——诚实暴露 70% 误报(D-033),不掩饰
  - 回测指标块:接真召回/精确/误报/F1/混淆,注脚说明误报偏高是数据可分性所致
  - Agent 区块:清掉越界内容,保留 5 步**结构示意**(get_today_data/detect_anomaly/forecast_trend(ARIMA 非 LSTM)/check_warning/compose_notice)+ 显眼「模块6·第13周开发」紫色标;删通义千问 qwen-turbo 既成事实表述
  - 删通知文本块(LLM Final Answer 是模块6,且原文含越界);摘 `:planning` 横幅
  - 兜底 FALLBACK 真值常量(断网 recent_alerts 留空不杜撰)
- **核验(独立,非桥接回执)**:后端 curl 两次一致(tp52/fp176/20告警/HTTP200);node 复刻工单映射 + **边界自查 PASS**(工单文本无 过热/放电/故障/置信度/运维/停运 等词);`npm run build` 通过(9.7KB,删假数据后变小);tag class(grn/org/yel)全在 global.css(避开 D-025 拼写坑)
- **顺带修自己的坏代码**:初版误写一个孤立 `computed`(死代码,无订阅不执行)+ `import watch` 放 script 中部 → 清理为单个 watch + import 提顶
- **同步**:本条 D-034;`02-dev-plan.md` 阶段五 AlertsView 行 + 模块7大屏行(仅剩 Analysis 挂规划中);论文模块 5/7 叙事不变(据实展示属实施)

---

## 2026-06-11 模块 5 阶段 B2:预警历史回测 + 误报校准(基准统一 fault_state)

### D-033:预警回测以 fault_state 为基准;CO 阈值校准 + dedup 持续性把误报 93%→70%;剩余为数据弱可分性

- **背景**:模块 5 B2 做历史回测(论文阶段五验证产物)。两个口径决策(用户拍板):
  - **回测基准 = fault_state(非 IEC)**:论文阶段五原写「以 IEC is_abnormal 标签算 TP/FP/FN」,但 D-020 已把检测对比基准从 IEC 改成 fault_state(IEC 是内部打标工具、且「自己跟自己比」)。预警回测必须与检测同一基准,否则两模块两套真值。**统一为 fault_state**
  - **命中口径 = 当日对齐**:第 t 天预警触发 vs 第 t 天 fault_state≠Normal。简单可解释;提前量对齐留未来工作
- **首跑暴露严重误报**:误报率 93.2%、FP=233、红警 208/330 天。**根因(独立核验)**:硬规则 `co>300`(国标注意值)在合成数据正常态 38% 天数即触发——CO 合成基线偏高,与国标值不匹配。非 engine bug,是规则阈值 vs 数据分布不匹配
- **修法 A+B(用户选)**:
  - **B 校准 CO 阈值**:`rules.yaml` 新增 `warning_thresholds` 段,CO 300→900(正常态 95 分位)。engine 加 `_effective_thresholds`(国标叠加覆盖),`_exceeds` 改用有效阈值。**只作用于预警引擎,不动 detect/threshold.ATTENTION_VALUES 国标口径**(国标允许按设备历史基线调注意值)
  - **A 接 dedup 持续性**:backtest 逐日维护每规则命中历史,`passes_persistence` 连续 2 次才算有效预警(滤尖峰),等级分布/告警记录也据此过滤
- **改善结果(已独立核验 JSON)**:误报率 **93.2%→70.4%**、TN 17→74(正常识别翻 4 倍)、红警 208→80。混淆 TP52/TN74/FP176/FN28,F1=0.34
- **⚠️ 诚实记录:剩余 70% 误报是数据弱可分性,非规则缺陷**:CO 正常/异常分布几乎重叠(均值 349 vs 392);模块 3 检测三方法准确率本就 60-80%、IEC 召回仅 40%。预警基于规则+阈值,判别天花板受限于气体浓度对异常的可分性。**停在 A+B,不再硬调阈值**(继续调=为凑指标过拟合合成数据,违 P1 诚实原则)。与 D-029(ARIMA 优)、模块 3(IEC 局限)一脉相承:据实呈现合成数据约束下的方法表现
- **产物**:`scripts/backtest.py` + `data/warning_backtest.json`(混淆+指标+四级分布+最近20告警,前端 AlertsView 数据源)+ `notebooks/figures/warning_backtest.png`(混淆矩阵+等级分布)
- **核验**:test_warning 17 用例零回归(engine 改 _exceeds 签名后,测试走 evaluate 公开接口仍全过)
- **同步**:本条 D-033;`02-dev-plan.md` 阶段五 backtest 行 + 回测基准改 fault_state;`论文梳理.md` 阶段五回测基准 + 误报诚实发现(待补)

---

## 2026-06-11 模块 5 阶段 B1:预警规则引擎算法核心(软规则用 ARIMA)

### D-032:预警规则引擎 + 四级分级 + 误报控制;软规则预测源定为 ARIMA

- **背景**:模块 4 提前完工后顺势提前启动模块 5(原计划第 11-12 周)。用户定:软规则用 ARIMA、本轮只做算法核心
- **关键决策——软规则(基于预测)的预测源 = ARIMA**:论文模块 5 的软规则是「基于预测结果」,但 D-029 实测 LSTM 精度差、ARIMA 全面更优。拿已知不准的 LSTM 做预警依据自相矛盾 → **软规则用 `arima.forecast_arima` 的未来 1-3 天预测**。与 D-029 叙事自洽,答辩话术:「预警软规则采用对比实验中更稳健的 ARIMA 做预测,是基于模块 4 实证结论的工程决策」
- **新增产物(纯算法层,DataFrame/dict 进出,不碰 DB/HTTP)**:
  - `warning/rules.yaml`:可配置规则库。硬规则(国标阈值,口径复用 threshold.ATTENTION_VALUES)+ 软规则(ARIMA 预测超标)+ 趋势规则(涨幅比例)+ 组合规则(产气快+油温高);四级分级元信息 + dedup 参数
  - `warning/engine.py`:`evaluate(current_gases, oil_temp, forecast_df)` → 触发规则列表 + 综合等级(LEVEL_ORDER 取最高)。**硬规则/软规则都复用 `threshold.detect_one`** 判超标(统一总烃口径,不重复实现)。软规则按最早超标日定级:第 1 天(24h)→red,第 2-3 天→orange
  - `warning/dedup.py`:`passes_persistence`(连续 N 次才报,滤尖峰)+ `is_duplicate`(24h 冷却去重)+ `should_push`(综合)。纯函数,历史记录由调用方传入
  - `tests/test_warning.py`:17 用例(Engine 10 + Dedup 7),覆盖硬/软/趋势/组合触发 + 四级取最高 + 去重边界
- **🚧 系统边界**:规则只输出 等级/哪些气体/规则编号/趋势,message 措辞**严禁故障类型**(已检查 rules.yaml 所有 message,只说「超标/上升趋势/综合关注」,无诊断词)
- **核验(独立,非桥接回执)**:`test_warning.py` 17 passed;全套 56 passed(原 39 + 17)零回归。**注:本轮桥接曾注入伪造测试结果(测试名 `test_not_triggered` vs 实际 `test_never_triggered`、多出假汇总行),重写+重跑+核验真实测试名识破**
- **依赖**:PyYAML==6.0.3 补进 requirements(此前靠传递依赖侥幸可用,新机器会装不全)
- **同步**:本条 D-032;`02-dev-plan.md` 阶段五表格(B1 ✅ / B2 回测+API 待下轮);论文模块 5 叙事不变(软规则用 ARIMA 属实施细节,已在 D-029 修订 8 铺垫「ARIMA 更稳健」)

---

## 2026-06-11 模块 4 阶段 C/D:predict API + PredictionView 据实改形(D-030 落地首例)

### D-031:PredictionView 翻转成「ARIMA 胜」+ 接真 + 摘横幅;落盘 JSON 喂 API

- **背景**:模块 4 算法完成后做 C/D(后端接口 + 前端接真)。PredictionView 原是 D-026 标「规划中」的设计稿,但内容与实测(D-029)**全面冲突**:页面写「LSTM MAE 2.14 < ARIMA 3.45,↓38%,创新点⭐」,实测却是 7 气体全部 ARIMA 胜(LSTM 1287 vs ARIMA 301)。直接接真会自相矛盾,硬留设计稿违背 P1 诚实原则 → 触发 D-030「前端可据实改形,但先问」,已列方案征得用户选**方案①据实翻转**
- **数据链(用户选「训练时落盘 JSON」)**:`train_lstm.py` 落 `models/train_history.json`(loss 曲线)→ `compare_predict.py` 汇总指标 + 验证段三序列 + loss,落盘 `data/predict_eval.json` → 后端 `/api/predict/compare` 只读文件返回(守 D-027「在线推理轻量」,ARIMA 每目标日重拟合需数十秒,不能进请求路径)
- **后端**:新增 `app/api/predict.py`(`APIRouter(prefix=/api/predict)`,GET `/compare` 读 JSON,文件不存在则 404 提示先跑脚本、不杜撰);main.py 注册;前端 `service/api/index.js` 加 `getPredictCompare`
- **前端改形(PredictionView 全量重写)**:
  - KPI 翻转:ARIMA 为主色、LSTM 划掉;「ARIMA 胜」徽章;7 气体胜负 7/7;研究结论块
  - 左上柱状图:7 气体 MAE 对比改**对数轴**(量纲跨度极大:co2~1869 vs ch4~0.77);ARIMA 主色、LSTM 灰
  - 左下:验证段真值 vs LSTM vs ARIMA 三线(接 series,42 目标日)
  - 右侧:loss 曲线接**真实落盘** loss_history;架构图保留(LSTM 结构没错)但注脚改「精度未兑现优势」;新增「为什么 ARIMA 更优」原因块(样本量/归一化/序列特性)
  - **删杜撰块**:原「滚动推理 3.42→4.05ppm」「训练成本 7→1 创新点⭐」误导内容
  - **摘掉 `:planning` 横幅**(D-026 收口,本页不再是规划稿)
  - 兜底:`getPredictCompare` 失败回退真值 FALLBACK 常量(防 Demo 断网,断网时曲线留空不杜撰)
- **核验(独立,非桥接回执)**:后端 curl 8011 返真值经统一信封;node 复刻前端 computed 确认 KPI(arimaWins 7/7、arimaMae 301<lstmMae 1287)+ 柱状图 7 点 + 三序列各 42 点 + loss 50 epoch;前端 `npm run build` 通过
- **⚠️ 环境问题(告知用户,未擅动)**:本项目后端锁端口 8000(start.sh + vite proxy),验证时发现 8000 被**另一个项目**(object-storage-console 的 vite)占用 → 跑本项目前需先关那个 vite,否则后端 bind 失败、proxy 打错服务
- **产物入 git 取舍**:`data/predict_eval.json`(评估快照,19KB)入 git 供 Demo;`BE/models/train_history.json`(train 副产物,loss 已汇入 eval.json)加 .gitignore。**踩坑**:.gitignore 不支持行尾注释,`path  # 注释` 整行被当 pattern 致不匹配,注释须独立成行(已修正)
- **同步**:本条 D-031;`02-dev-plan.md` 模块7 大屏行 + 阶段四 PredictionView 行;`论文梳理.md` 修订 8 补「前端已据实呈现」

---

## 2026-06-11 协作原则:前端视图非刚性,可裁剪/改形但须先问

### D-030:前端展示按真实能力裁剪/改形,论文大屏不锁死(硬约束不变)

- **背景**:用户明确——前端页面不是刚性必须的。某模块实现不了或实现得不正确时(如 D-029 实测 LSTM 预测精度差),对应前端视图可去掉或更改形态,不必为凑齐论文模块 7 画的大屏版式硬塞误导性可视化
- **决策**:
  - **可裁剪/改形的范围**:前端视图「展示什么内容、以什么形态展示」。例:PredictionView 原画「逼真 LSTM 预测曲线」,实测 ARIMA 才是主力 → 可改成「LSTM vs ARIMA 对比」或弱化 LSTM,而非硬画一条漂亮 LSTM 曲线
  - **程序约束(用户加的)**:每次裁剪/改形**都要先列证据 + 给方案 + 等用户拍板**,不自行决定删页/改页(承协作约定「质疑方向时先列证据再给方案」)
  - **不可破的硬约束**:① 系统刚性边界(对外不输出诊断/故障类型/健康度评分,IEC 三比值法仅内部用)② P1 诚实原则(不杜撰逼真假数据,D-023)。裁剪只针对「展示形态」,不松动这两条
- **与既有原则的关系**:这是 P1 诚实原则(D-023)的延伸——D-023 是「不杜撰假数据」,D-030 再进一步「连展示什么本身都可按真实能力裁剪,不被前端版式绑架」
- **影响**:论文模块 7 大屏从「锁死规格」降为「设计意向」,实现时按真实能力定稿。具体某页被改时,届时再同步 论文梳理(本次尚无页面实际被改,论文暂不动)
- **同步**:本条 D-030;CLAUDE.md 协作约定区新增同名条目;论文梳理暂不动(待具体页面改动时记)

---

## 2026-06-11 模块 4 阶段 B2:ARIMA 基线 + 滚动预测 + 对比实验(ARIMA 全面胜)

### D-029:LSTM vs ARIMA 实测 ARIMA 全面更优,兜底叙事转正为主叙事;补 matplotlib + 出图

- **背景**:承 D-028(B1 跑通),完成 B2 = `arima.py` + `rolling.py` + `compare_predict.py`,出论文对比素材
- **新增产物**:
  - `algorithms/predict/arima.py`:`forecast_arima(history_df, steps, order=(2,1,2))`,7 气体各跑一个 statsmodels ARIMA(for 循环,单变量)。**兜底**:含大量 0 的气体(c2h2 ~36%)ARIMA 可能不收敛/抛错 → `_forecast_one` try/except 退化为「持平最后观测值」(naive),口径透明;负值 clip 到 0(气体非负)
  - `algorithms/predict/rolling.py`:`rolling_forecast(model, scaler, history_df, steps=3)`,复用 `lstm.predict_step` 迭代回灌得未来 1-3 天。注释明确误差累积、只滚 3 天、供趋势参考不作精确承诺
  - `scripts/compare_predict.py`:验证段(后 20%,42 目标日)单步 walk-forward 对比。LSTM 用前 30 天滑窗、ARIMA 用截至 t-1 全量真值各预测 1 步,同目标日同真值算 MAE/RMSE/MAPE(MAPE 仅真值非 0 处算,避免除零)+ 7 子图
- **实测结果(已独立核验 stdout,非桥接回执)——7 气体全部 ARIMA 胜**:总体均值 MAE **LSTM=935.83 vs ARIMA=301.23**。逐气体(MAE):h2 22.6/18.8、ch4 20.4/0.77、c2h4 83.6/5.5、c2h6 55.1/22.1、c2h2 14.8/1.3、co 370.6/190.8、co2 5983.7/1869.3,ARIMA 项项更低
- **原因(据实)**:① MinMax 全域归一把 normal 变化压窄、LSTM 误差反归一化放大(承 D-028);② 单设备 360 天滑窗后训练样本仅 ~258,对 LSTM 偏少;③ ARIMA 每步全量重拟合 + 一阶差分,对「均值回复 + 强噪声」序列更稳
- **叙事影响(D-027 兜底转正)**:论文创新点 2「LSTM 提升精度」与实测冲突 → 改为对比研究叙事「小样本高波动 DGA 上 ARIMA 较 LSTM 更稳健」。这是有价值的实证结论,与创新点 1 多方法对比方法论一致。**作者已拍板方案 A(2026-06-11)**:创新点 2 标题改「基于 LSTM 与 ARIMA 的 DGA 气体趋势预测对比研究」,正文已重写(据实承认 ARIMA 优 + 原因 + 选型实证价值),论文梳理 修订 8 同步标「已拍板」
- **环境补丁**:3.11 venv 缺 matplotlib(D-027 批量装漏了,旧 png 是 3.9 下生成)→ `pip install matplotlib==3.9.2`(requirements 本就有此行)。另:`compare_predict._plot` 加 try/except ModuleNotFoundError 优雅降级(对齐 compare_detection 既有模式);图内文字改 ASCII(matplotlib 默认字体无 CJK 字形,会渲染成方框,compare_detection 本就只用 ASCII 标签)
- **核验**:`predict_compare.png`(314KB)落盘、0 glyph 警告;`rolling_forecast` smoke 形状 (3,7)、无 NaN、全 ≥0
- **同步**:本条 D-029;`02-dev-plan.md` 阶段四 arima/rolling/compare 行打 ✅;`论文梳理.md` 修订 8 + 总览表 + 核心结论(创新点 2 待作者重写)

### D-additional:预测算法层单元测试(B 收尾)

- `tests/test_predict.py`:pytest 14 用例,覆盖 dataset(窗口形状/缺列/样本不足/归一化/scaler 复用)、train_val_split(时序不打乱)、arima(形状/缺列/非负 clip/全 0 naive 兜底)、rolling(形状/index/无 NaN 非负/history 不足)。**rolling 用 stub model + 真 scaler**,不依赖训练好的 `.h5`,测试不绑落盘产物
- 全套零回归:test_api 8 + test_detect 17 + test_predict 14 = **39 passed**

---

## 2026-06-11 模块 4 阶段 B1:LSTM 算法层 + 训练脚本跑通

### D-028:LSTM 滑窗造样本 + 离线训练落盘,loss 下降跑通(B1);预测精度暴露数据/建模软肋,留 B2 + 兜底叙事

- **背景**:承 D-027(环境就绪),执行阶段 B。用户选「先验证跑通」,本轮收窄为 **B1 = `dataset.py` + `lstm.py` + `train_lstm.py`**;`arima.py`/`rolling.py`/`compare_predict.py` 留 B2 下一轮,降低单轮风险
- **新增产物**:
  - `algorithms/predict/dataset.py`:`make_windows(df, lookback=30) -> (X, y, scaler)`(过去 30 天 7 气体 → 第 31 天 7 气体,单步多输出);`train_val_split_by_time(df, val_ratio=0.2)` **按时间切不 shuffle**。特征只用 7 原始气体(不喂 featured 滑窗派生,避免与 LSTM 自学时序重复)
  - `algorithms/predict/lstm.py`:`load_lstm(path)` 固定 `compile=False`(D-027 踩坑,不带必崩);`predict_step(model, scaler, window_df)` 单步推理,反归一化回原始量纲。**不含训练**(守 D-027 离线训练/在线推理边界)
  - `scripts/train_lstm.py`:`Sequential([LSTM(64), Dense(7)])`(论文写死结构),时序切分不 shuffle、**scaler 只 fit 训练集**(防泄漏),落盘 `BE/models/lstm.h5`(251KB)+ `scaler.pkl`(819B,joblib),`.gitignore` 已排除
- **实跑结果(已独立核验 stdout + 文件字节,非桥接回执)**:train_loss 0.0196→0.0037、val_loss 0.0505→0.0234,**loss 明显下降 = B1「跑通」目标达成**(第 9 周阶段性 bar)。smoke:`load_lstm(compile=False)` + `predict_step` 输出 7 气体、无 NaN、形状对
- **⚠️ 诚实记录:预测精度只是「数量级对、不精确」,不是 bug**:
  - 现象:in-distribution 窗口预测 co2 1850 vs 真实 2710、c2h6 32 vs 20(量级对);偶有小负值(ch4 -2.09)
  - 根因:合成序列**日间波动极大**(normal 月内 co2 在 1593↔2773 跳、co 在 113↔893),且 7 气体跨度巨大(co2 因异常段最高 ~60000、c2h4 ~2000)。MinMax 全域归一把 normal 变化压成极窄子带 → 缩放空间小误差(val_loss 0.023)反归一化后在原始 ppm 看着大;回归器输出略负反归一化即穿底 → 负值
  - 定性:**pipeline 正确**(loss 真降、加载/scaler/形状皆对),问题在数据波动性 + 建模精度,非代码缺陷
- **对论文的意义**:这正是 ARIMA 基线(B2)+ D-027 兜底叙事「ARIMA 在该数据集上更稳健」要讨论的点。B2 compare_predict 出 MAE/RMSE/MAPE 后,据实选叙事(LSTM 胜则讲深度学习,败则讲 ARIMA 稳健 + LSTM 局限)。**精度调优(EarlyStopping / 标准化换 log1p / 加 epoch)留 B2 视对比结果定**,不在 B1 提前优化
- **HDF5 warning**:Keras 提示 `.h5` 是 legacy、建议 `.keras`。**仍用 `.h5`**——论文把 `.h5` 写死为交付产物(D-027),warning 无害
- **同步**:本条 D-028;`02-dev-plan.md` 阶段四 dataset/lstm/train 行打 ✅(标 B1)、arima/rolling/compare 标 B2;论文暂不改(待 B2 对比结果定叙事)

---

## 2026-06-10 提前启动模块 4:环境升级 Python 3.11 + TF(阶段 A)

### D-027:模块 4 定调「离线训练 + 在线推理」+ 框架/环境路线锁定

- **背景**:第 7 周异常检测收尾,提前启动第 9 周核心模块 4(LSTM 趋势预测),为最高风险项(LSTM 跑不通的兜底叙事)留缓冲。动手前锁定三个一直挂起/未显式的架构决策
- **决策 1 框架 = Keras(TensorFlow),不换 PyTorch**:论文模块 4 把框架写死到 API 级细节(`Sequential([LSTM(64), Dense(7)])`、`.h5` 产物)。PyTorch 会逼改论文每处代码示例 + 产物格式(`.pt`),代价远超「工程省事」收益。这与 D-001(SQLite 替 MySQL,ORM 兼容可糊弄)性质不同,框架替换藏不住。**否决 PyTorch**
- **决策 2 架构 = 离线训练 + 在线推理**:训练是重计算 + 落盘 → 放 `scripts/train_lstm.py`(脚本层);推理是轻量 load `.h5` + 滚动 3 步 → 放 `algorithms/predict/`(纯算法层)。把论文「`.h5` 作交付产物」的隐含架构显式化,守住 CLAUDE.md「算法层不依赖 DB/HTTP」铁律,且 API 不会现训现预测超时
- **决策 3 环境 = Homebrew python@3.11,非 pyenv**:D-003 原预案写 pyenv,但本机已有 brew、无 pyenv;毕设是「装一次固定用到答辩」,不需要 pyenv 多版本切换能力。`brew install python@3.11` 一步到位(3.11.12)。**本机是 Intel Mac**(`/usr/local` 路径、wheel 全 x86_64),故用标准 `tensorflow` 而非 requirements 注释里写的 `tensorflow-macos`(那是 Apple Silicon 才需要)
- **阶段 A 执行结果(已验证)**:
  - 装 TF 2.16.2 + Keras 3.14.1 + h5py 3.16.0,numpy 1.26.4 无冲突
  - LSTM hello-world(论文同构 `Sequential([LSTM(64), Dense(7)])`)fit 5 轮 loss 0.218→0.087 下降 ✅
  - 旧后端 3.11 下零回归:app import OK、17 检测单测全过、`uvicorn` 起服务 `curl /api/detect/methods/1` 与 `/api/data/overview` 均 HTTP 200 返真值(360 条/健康率 0.7472,与 D-023 一致)
- **⚠️ 踩坑记录(Keras 3 + `.h5`)**:`load_model('x.h5')` 默认会反序列化 compile 配置,Keras 3.14 报 `Could not deserialize 'keras.metrics.mse'`。**解法:`load_model(path, compile=False)`**(推理本不需要 optimizer/loss,合理且保住 `.h5` 叙事)。阶段 B 写 `train_lstm`/推理时务必带 `compile=False`,否则在线推理加载必崩
- **⚠️ venv 重命名坑(本轮踩到并修正)**:先建 `.venv311` 验证、再 `mv .venv311 .venv` 切换 → `activate` 里 `VIRTUAL_ENV` 仍硬编码旧名,`source activate` 失败。venv 不可移植。**正确做法 = 在目标名 `.venv` 原地重建**(已照做,走 pip 缓存很快)。旧 3.9 venv 验证通过后已删
- **挂起项结算**:勾掉「训练好的 `.h5` 是否纳入 git」→ **否**(`.gitignore` 已排除 `*.h5/*.keras/*.pkl`,通过脚本重训)
- **本次范围**:仅阶段 A(环境)。阶段 B(算法/脚本)、C(API)、D(前端接真 + 摘 D-026「规划中」横幅)另起执行
- **同步**:本条 D-027;`论文梳理.md` 实施期修订 7 + 总览表;`02-dev-plan.md` 阶段四标注

---

## 2026-06-09 DetectionView 右侧阈值表接真(S1)+ 算法层单测 + 未接真视图标注

### D-026:三个未接真视图加「规划中」横幅 + AnalysisView 删 IEC 编码越界展示

- **背景**:还技术债时盘点发现 `PredictionView`/`AnalysisView`/`AlertsView` 三页**既全静态假数据、又无任何标注**,与 DashboardView 已确立的 P1 诚实原则(D-023)冲突。中期检查评委点进 /prediction 看到逼真 LSTM 曲线会误判已完成
- **决策(承 P1 诚实原则)**:
  - **AppHeader 加 `planning` / `planningText` prop**(B1 方案,不在每页手写横幅):置 true 时顶部渲染黄色「规划中」横幅。改 1 组件 + 3 页传参,无重复代码
  - 三页传 `:planning="true"` + 各自说明文案(标注对应模块的开发周次:LSTM 第 9-10 周 / 预警第 11-12 周 / Agent 第 13 周)
- **边界红线(AnalysisView)**:该页「IEC 三比值法 · 编码/判定」块直接展示三比值 `code`(0/2/1),**暴露 IEC 内部推理步骤 = 越界**(IEC 只能内部用,业务页禁止展示推导)
  - 方案甲(保守):删 `编码 {{ r.code }}` 展示行 + 数据数组 code 字段 + 标题改「气体特征比值(衍生指标)」;**保留比值数值**(原始气体算术比属中性衍生指标,不算 IEC 专属推理)
  - 拒绝方案乙(整块删):比值数值本身中性、对特征工程叙事有价值,不必全删
- **核验**:build 通过;改动经 Read 逐处确认真实落盘(本轮桥接注入伪造了多条「已传 planning」假回执,实际三视图首轮未改,靠 Edit「需先 Read」约束 + 逐处 Read 才识破并真正落实)
- **同步**:本条 D-026;dev-plan 模块 7 大屏状态可更新(5 视图标注/接真情况)

### D-025:DetectionView 阈值参考表接 latest 真值,另两块仍留「示意」

- **背景**:DetectionView 右侧三块明细(阈值参考表 / 近 7 日一致性表 / PCA 散点)D-022 时打「示意」标,待联调。逐块评估后端支撑:
  - 阈值参考表:`/data/latest/{id}` 有真实气体值,阈值是国标固定值 → **可接**
  - 近 7 日一致性表:需「逐日三方法检测」接口,后端只有单点 + 全量对比 → 缺
  - PCA 散点:需后端 PCA 输出 → 缺,且对预警叙事无实质价值
- **决策(选项 S1,最小)**:只接阈值参考表;另两块保留「示意」标。理由:用最小代价消除最该接真的欠账,工程力气留给第 9 周 LSTM 核心。近 7 日表(S2)/PCA(S3)价值递减、依赖新后端,中期不值得
- **实现**:`thresholds` 改 computed,接 `latest.gases`。展示 4 个国标判定项(H₂/C₂H₂/总烃/CO),阈值口径与后端 `threshold.py::ATTENTION_VALUES` 一致(h2=150/c2h2=5/总烃=150/co=300)
  - **修正口径错误**:原静态表列「C₂H₄ 100ppm」——国标不单独给单个烃类设注意值,按总烃合并判(后端口径)。接真时改为「总烃」判定项,消除这个与国标/后端不符的展示
  - 分档:超注意值→异常;≥80%→趋近;≥50%→关注;否则正常。未加载显示「—」占位,不杜撰
  - 去掉阈值表的「示意」标(已接真);近 7 日表/PCA 散点保留「示意」
- **核验**:build 通过;curl latest 手算预期值(H₂36.4/C₂H₂1.47/总烃4.2/CO120.5 全「正常」),与 detect 接口 is_abnormal=false 自洽
- **顺带修 bug**:占位行标签类名 `tag-gray`→`tag-gry`(global.css 实际定义无 a)
- **同步**:dev-plan 阶段二 DetectionView 行状态更新(右侧阈值表✅/另两块示意)

### D-additional:算法层单元测试(见 02-dev-plan 阶段二)

- `tests/test_detect.py`:pytest 17 用例,覆盖 threshold/iec/iforest/metrics 契约与边界(正常/超标/缺失/编码边界/除零/可复现);pytest==8.4.2 入 requirements。已提交 372602e

---

## 2026-06-08 前端 DashboardView 接真值 + 修复 .env DB 路径坑

### D-024:修复 .env 用相对 DB 路径导致非 BE 目录启动时连空库 500

- **现象**:DashboardView 接真后,浏览器显示数据全 0,接口 500
- **根因**:`BE/.env` 写了 `DATABASE_URL=sqlite:///./data/app.db`(**相对路径**),盖掉了 `app/config.py` 用 `__file__` 算的绝对路径默认值。从非 BE 目录(如项目根)起 uvicorn 时,`./data/app.db` 指向根目录下的 0 字节空库 → 查询 `monitoring` 报错 → 500 → 前端 catch 回退成 0
- **佐证**:`cd BE` 起服务时 `./data/app.db` 恰好=真身,所以一直没暴露;换目录起才炸。根目录 `data/app.db`、`BE/app.db` 两个 0 字节文件即历史误启动残留
- **修法(方案 A,根治)**:删除 `.env` 中 `DATABASE_URL` 行,回落到 config.py 健壮默认值。验证:从项目根起,生效值=绝对路径 `sqlite:////…/BE/data/app.db`,接口 200 返 360 条真值
- **清理**:删除两个 0 字节空库 `BE/app.db`、`data/app.db`(真身 `BE/data/app.db` 802KB 完好)
- **教训**:SQLite 相对路径配置脆弱、随启动目录漂移;凡路径配置优先用 `__file__` 派生绝对路径。`config.py` 本已正确,坑在 `.env` 覆盖
- **补记(2026-06-09,提交 822e43e)**:当时只改了本地 `BE/.env`,**漏改模板 `BE/.env.example`**(它仍留相对路径且进 git)。`cp .env.example .env` 会让坑通过模板复发。已同步删除 `.env.example` 的相对 `DATABASE_URL`,改为回落绝对默认值;并补 README 数据准备链(原仅 `init_db`/`import_data`,缺 `synthesize_data`/`build_features` 会得空库)

### D-023:DashboardView 接真值(P1:4 块接真 + 6 块标「规划中」)

- **背景**:第 8 周中期检查要演示「数据 → 异常检测 → Dashboard」最小闭环。DashboardView 此前全静态,且含大量未来模块(LSTM/Agent/预警)的逼真占位
- **盘点**:10 个数据块中仅 4 块有后端支撑(overview/latest/detect 已就绪),其余 6 块依赖第 9-13 周才开发的模块
- **决策(选项 P1,诚实标注)**:
  - **4 块接真**:① KPI 行(overview:1 台/360 条/健康率 74.7%/最新状态);② 7 气体雷达(latest.gases,阈值线保留国标固定值);③ 异常检测(detect/methods/1,规则两法);④ 工况仪表(latest.conditions)
  - **6 块标「规划中」黄徽章**:4 级预警饼图、24h 时段、LSTM 预测曲线、Agent 5 步、气体指标(含预测)、活跃预警 —— 中期检查坦白这些是规划设计稿
  - **拒绝 P2(只接不标)**:逼真假数据会让评委误判已完成,追问即穿帮;与 DetectionView D-022 的「示意」标注一致,守「不杜撰」
- **边界与事实对齐**:
  - 删除 detection 块越界的 `021 低温过热`(IEC 故障类型,对外禁止;同 D-022 类问题)
  - 单点检测如实只展示规则两法(阈值/IEC),孤立森林是批量无监督法不适合单点,标「批量法」灰显,其结果在 DetectionView 全量对比中呈现
  - 工况仪表 4 格→3 格:后端只有油温/负载电流/环温,删无数据来源的「温升 ℃/h」;负载从「负载率 1.1」口径改为「电流 250A」口径(后端是电流值)
  - 最新快照 is_abnormal=false → 检测显示「正常(0/2 规则触发)」,KPI 最新状态绿色
- **健壮性**:三接口各自独立 try/catch,任一失败不拖垮其余块;失败回退默认值(非杜撰值)
- **同步**:dev-plan 阶段七「替换前端静态数据」部分提前完成;论文无需改
- **答辩话术**:"中期演示首页四个核心区块(设备概览、气体雷达、异常检测、工况)均为后端真实数据;LSTM 预测、Agent 流水线、预警分级等标注『规划中』,是第 9-13 周的开发计划,当前展示交互设计稿。"

---

## 2026-06-08 前端 DetectionView 接真值

### D-022:DetectionView 定位为「算法对比/答辩演示页」,左侧接真值、右侧打示意标签

- **背景**:第 7 周后端检测三方法 + `/api/detect/_internal/compare` 已就绪(D-020/D-021),但前端 DetectionView 仍是全静态假数据,且存在两处硬伤:
  1. 杜撰指标(阈值 88.2%/IEC 91.5%/IF 94.1%)与真值(60.6%/67.5%/80.3%)矛盾,尤其 IEC 召回杜撰成 87.3%(真值仅 40.7%),**与论文「IEC 局限性大」叙事自相矛盾**
  2. 第 227 行硬编码 `021 → 低温过热 (<300℃)` —— IEC 推出的具体故障类型,**越系统边界**(对外禁止输出故障类型)
- **决策**:
  - **定位**:DetectionView 接 `_internal/compare`,定位为算法对比/答辩演示页(非纯业务大屏)。理由:此页版式本就是为「三方法指标对比 + 混淆矩阵」设计,价值在答辩讲对比、印证选题动机
  - **左侧接真值(X1)**:① 三方法卡片、② 5 项指标柱状图、③ 混淆矩阵全接真值。混淆矩阵展示**最优方法 IsolationForest 真实四格**(55/234/35/36),不做后端未评估的「融合投票」口径
  - **砍 AUC 列**:后端 `binary_metrics` 未算 AUC(规则法无概率分),柱状图 6 项→5 项
  - **右侧打示意标签(Y2)**:近 7 日一致性表、阈值参考表、PCA 散点本周不接真(需单点/时序接口逐日跑),加黄色「示意」徽章,留第 8 周联调
  - **越界即删**:删除 `021 → 低温过热` 整块,补注释说明边界
  - **真值兜底**:页面挂载拉 `getDetectCompare()`,失败回退到内置 `FALLBACK` 真值常量(防答辩 Demo 断网),不回退到杜撰值
- **同步**:① 本条 D-022 ② dev-plan 阶段二「DetectionView 对接」可标部分完成(左侧✅/右侧🔶)③ 论文无需改(未涉及叙事变更,反而消除了与 D-020 的矛盾)
- **答辩话术**:"检测页左侧三方法对比直接读取后端 `_internal` 评估接口的真实指标,与论文实验数据一致;右侧单点明细标注为示意,因为它需要的是业务单点接口,放在第 8 周联调完成。"

---

## 2026-06-05 异常检测三方法对比实验完成

### D-021:Isolation Forest 设计选择 + 三方法对比结果

- **iForest 设计**(`detect/iforest.py`):训练特征用 7 种原始气体,与 iec/threshold **同口径**(不喂滑窗/变化率,避免开小灶);`contamination=0.25` 贴近 ~25% 异常占比——无监督方法需先验异常比例的已知软肋,论文如实讨论
- **统一接口**:三检测器都导出 `detect_df(df) -> pd.Series[0/1]`(承算法层 DataFrame 约定)
- **真实对比结果**(360 天,基准=fault_state,真值异常 91/25.3%):

  | 方法 | 准确率 | 精确率 | 召回率 | F1 | 误报率 |
  |------|------|------|------|------|------|
  | Threshold(国标) | 0.606 | 0.368 | **0.780** | 0.500 | 0.454 |
  | IEC 三比值 | 0.675 | 0.370 | 0.407 | 0.387 | 0.234 |
  | **IsolationForest** | **0.803** | **0.611** | 0.604 | **0.608** | **0.130** |

- **结论**:iForest 综合最优(F1=0.608/误报最低 0.130);阈值法召回最高(0.780)但误报爆表(0.454);IEC 垫底(F1=0.387)→ 强化「单一国标比值法在早期故障局限明显,需多方法+LSTM+Agent」选题动机
- **产物**:`compare_detection.py`、`detection_confusion.png`
- **边界**:对比内部用 fault_state 分组,报表只呈现 is_abnormal(承 D-008)

---

## 2026-06-05 异常检测对比基准变更

### D-020:对比实验 ground truth 从「IEC is_abnormal」改为「合成真值 fault_state」

- **背景**:dev-plan 阶段二原写「以 IEC `is_abnormal` 为基准」评估 threshold/iForest。动手前先用数据验证基准合理性
- **数据证据**(360 天合成时序,`featured_timeseries.csv`):
  - 合成真值 `fault_state` 异常 91 天(25.3%);IEC 现场重算异常 100 天(27.8%)
  - **两者一致率仅 67.5%**(IEC 相对真值:漏报 54、误报 63)
  - 漏报集中在 Thermal Fault <300℃(23)、Discharge of Low Energy(16)等**比值变化慢**的故障
- **根因**(非 bug):合成器用 OU 过程在对数空间渐变生成浓度,`fault_state` 是马尔可夫链状态标签;状态切换有过渡期(`STATE_TRANSITION_BLEND_DAYS`),浓度爬升滞后于状态标签 → IEC 在过渡期判不出;健康态 OU 随机波动偶尔越过 IEC 阈值 → 误报
- **决策**:改用**合成真值 `fault_state` 做 ground truth**,IEC / 阈值法 / Isolation Forest **三法平等评估**
  - 理由 1:合成器自带真实状态标签,是最严谨的 ground truth;让 IEC 自己当基准 = 自己跟自己比,创新性弱
  - 理由 2:IEC 仅 67.5% 一致**恰好强化选题动机** —— 单一国标法有局限 → 需要多方法对比 + LSTM 预测 + Agent 串联
- **系统边界**:对比实验内部可按 fault_state 故障类型分组分析,但论文表格/大屏只呈现 **is_abnormal 二分类指标**(承 D-008 边界)
- **同步**:① 本条 D-020 ② 论文「实施期修订」需追加一项(基准口径变更)③ dev-plan 阶段二「以 IEC 为基准」表述待改
- **答辩话术**:"我们用合成器注入的真实故障状态作为评估基准。实验显示连国际标准 IEC 三比值法也只有 67.5% 的一致率,这正说明依赖单一阈值/比值方法的局限,印证了本系统引入多方法融合与时序预测的必要性。"

---

## 2026-06-05 工况合成修正

### D-019:修复负载周末模式的日期错位 bug

- **背景**:补查工况模拟(dev-plan 阶段一 6/5 任务)时发现 `synthesis.py::synth_load_current` 的周末降载逻辑用硬编码 `(day_idx + 2) % 7`,该偏移是为旧 START_DATE `2025-01-01`(周三)写的
- **真实 bug**:D-015 已把 `DEFAULT_START_DATE` 改为 `2024-04-01`(**周一**),旧公式仍按"起点周三"推算,导致周末降载**整体错位 2 天**(把周六/日当工作日满载,周四/五当周末降载)
- **修正**:函数改收 `cur_date: date` 参数,直接用 `cur_date.weekday() >= 5` 判周末,根治硬编码随 START_DATE 漂移的脆弱性;顺带修掉 docstring 残留的"90 天"过期表述(应为 360 天)
- **下游影响**:seed=42 固定,**气体序列完全不变**,仅 oil_temp/load_current 两列随日期对齐变化。已重跑 `synthesize_data → import_data --reset → build_features`,CSV/SQLite/特征三处产物全部对齐
- **验证**:周一均值 300.8 vs 周六均值 211.5(比值 0.703 ≈ 设计 0.7);SQLite 4/4 周四 load=188.83(满载)、4/6 周六 load=145.2(降载)
- **答辩话术**:若问"工况怎么模拟"——负载按真实日历分工作日/周末(周末 0.7×)+ 年度正弦季节性;环温季节正弦(基准 15℃ ±15℃);油温随负载平方 + 环温耦合,物理三级依赖

---

## 2026-06-04 开发计划细化

### D-018:细化 02-dev-plan.md 并修正过期假设

- **背景**:`02-dev-plan.md` 写于第 6 周初(EDA 之前),内含已被 D-008/D-015 推翻的假设,与论文「实施期修订」矛盾
- **修正**:
  1. 数据规模:744 行 → 360 行单设备时序(744 是原始快照,非 LSTM 输入)
  2. ground truth:Fault 列 → IEC 自动打标(Fault 97.6% 未标注,不可用)
  3. 回测数据:744 原始 → 360 天合成时序(快照无时间维,无法回测时序预警)
  4. 删除"🎯 巧思:Fault 列正好做 ground truth"(该表述错误且越界)
  5. 补系统边界提示:检测对比只呈现 is_abnormal 二分类指标
  6. 实验记录形式:`.ipynb` → `scripts/*.py`(沿用现状)
- **新增**:现状盘点表(模块 1/2 ✅、模块 3 🔶、4/5/6 ⬜)、各阶段产出细化到文件路径
- **形式**:直接修订原文件(非另建 02b),避免两份计划并存不同步;旧版本交 git 历史保管
- **同步**:论文「实施期修订」早已记录(D-011),本次仅计划文档对齐,无需再改论文

---

### D-011:论文梳理同步更新

- **背景**:今日 EDA 决策(D-008/009/010)与论文模块 1 "不做状态演化数据生成"等表述不一致
- **决策**:在 `论文梳理.md` 末尾追加「六、实施期修订」一节,坦诚记录 6 项修订:
  1. MySQL → SQLite
  2. 引入"分布保持的时序构造"(替换"不做状态演化")
  3. Ground truth:Fault 列 → IEC 自动诊断
  4. 工况数据模拟生成
  5. H₂O 列删除
  6. LSTM 目标气体数量预案(7 或 5+2)
- **意图**:答辩对照论文时,所有修订有迹可循,避免"说一套做一套"的指责
- **核心确认**:**论文的目标、创新点、系统架构、4 大核心能力、4 个模块的算法均无变更**

---

## 2026-06-04 前端联调管道打通

### D-017:建立前端数据层 + 验证联调管道

- **vite proxy**(`FE/vite.config.js`):`/api` → `http://localhost:8000`,开发期规避跨域
- **API 封装**(`FE/src/api/index.js`):统一 fetch 封装,导出 5 个接口
  (health/getOverview/getTransformers/getLatest/getTimeseries)
- **验证**:`localhost:5173/api/data/overview` 经 proxy 正确返回后端真实 SQLite 数据
- **联调链路确认通畅**:前端 → vite proxy → FastAPI → SQLite
- **刻意未改任何图表**:Dashboard 大屏的 KPI/饼图/雷达依赖未完成的模块 3/4/5,
  待对应模块完成后再统一接真实数据,避免现在为 1-2 个图破坏既有大屏设计
- **前端用法**:`import api from '@/api'` → `await api.getOverview()`

---

## 2026-06-04 特征工程模块(模块 2)

### D-016:特征工程实现

- **文件**:`BE/app/algorithms/features.py`(纯算法层,输入输出 DataFrame)
- **驱动**:`BE/scripts/build_features.py` → `data/featured_timeseries.csv`
- **48 个特征**,分四类:
  1. **基础衍生**(4):总烃 + IEC 三比值(CH4/H2、C2H2/C2H4、C2H4/C2H6)
  2. **滑窗统计**(28):7 气体 × {mean, std, max, min},window=7,右对齐不泄露未来
  3. **变化率 ⭐**(16):7 气体 × {日产气速率, 百分比速率} + 油温升速率 + 总烃变化率
  4. **归一化**:`MinMaxNormalizer` 类(fit/transform/inverse_transform + to_dict 序列化)
- **关键实现细节**:
  - safe divide:比值/百分比的分母 < 1e-6 时记为 0,杜绝 inf/nan
  - 滑窗 min_periods=1:前几天数据不足时用已有数据,不产生全 NaN
  - 归一化独立于 build_features:依赖 train/test 划分,留给 LSTM 阶段按需调用
- **验证**:真实数据跑通,反归一化往返误差 0.000000;2/21 检出 H2 单日 +187.8% 的预警信号

---

## 2026-06-03 改为单设备方案(360 天单台)

### D-015:从多设备(50 台 × 90 天)改为单设备(1 台 × 360 天)

- **背景**:用户质疑「为什么默认多设备?单设备可以吗?」
- **分析**:论文从未要求多设备;原 743 行本就是 743 台快照(非任一台时序);Agent 创新与单/多设备无关;多设备徒增「全局训练 vs 个体模型」复杂度
- **决策**:改单设备——1 台 × 360 天(跨四季),LSTM 单台训练推理,Agent 每天为该台跑 5 步
- **算法增强**:`StateChain` 加「事件预算」(n_days≥180 启用),保证 360 天注入足够异常(实测 91 天异常/25.3%),避免运气好全程健康
- **同步**:`synthesis.py` 默认 1 台×360 天;论文「一·五」多设备策略改单设备聚焦
- **答辩话术**:「本课题研究预警流程与算法验证,非工业级多设备平台。单设备使数据故事更纯粹(与原始形态一致)、算法更简洁、叙事更聚焦;多设备扩展是工程问题非研究问题,放未来工作」

---

## 2026-06-03 系统边界守护(三处同步加固)

### D-014:明确并固化「预警系统」的边界

- **背景**:用户质疑「只做预警不做诊断是否偏移」;核查发现 IEC 已实现且 `/api/data/overview` 当时直接返回 `Thermal Fault >700℃` 等故障类型,有泄露
- **决策(三处同步加固)**:① API 业务接口只回 `is_abnormal`,故障细节移 `/_internal/state_distribution`;② `04` 加「系统边界(刚性约束)」章节;③ 论文加「一·五、系统边界」节
- **核心规约**:IEC 仅内部用(二分类/状态分组/ground truth);对外只输出二分类 + 预警等级 + 超标气体,不输出故障类型
- **意义**:答辩可清晰回答「为什么不做诊断/评估」,不被质疑越界(边界定义详见 04)

---

## 2026-06-03 时序合成器实现

### D-012:时序合成器算法选型

- **核心算法**:状态机(马尔可夫链)+ OU 过程(对数空间均值回归)
- **关键设计**:
  - **对数空间生成**:应对长尾分布(EDA 显示气体浓度跨 4 个数量级),反对数后自然为正
  - **OU 过程**:`x' = x + θ*(target - x) + σ*N(0,1)`,半衰期 ~4.6 天 → 物理现实的"日变化缓慢"
  - **状态切换平滑**:不瞬间跳变,5 天过渡期,贴合渐进劣化
  - **状态停留**:几何分布,异常态平均持续 21 天
- **参数标定**:90 天周期内,健康 73% / 异常 27%(在 70-85% 设计区间)

### D-013:数据清洗——修正原始数据集中的 `'-'` 占位

- **背景**:原 xlsx 文件中 7 行的 CO/CO2 列写成 `'-'` 字符串,EDA 脚本之前漏处理
- **修复**:`load_rows` 中统一把 `-/na/n/a/空字符串` 视为 None(Fault 列除外)
- **影响**:CO 缺失率从 21.8% → **22.5%**(7 行回归正确分类),其余分布不变

---

## 2026-06-03 EDA 阶段重大调整

### D-008:Fault 列不可用作 ground truth → 改用 IEC 自动打标

- **背景**:EDA 发现原始 743 行中,**97.6% 的 `Fault` 列值为 `'NA'`**,有效标签仅 18 行(No Fault 14 / Electrical 2 / Thermal 2)
- **问题**:无法支撑"用 Fault 列做 ground truth 评估异常检测算法"的论文规划
- **决策**:**用 IEC 60599 三比值法对全量 743 行自动诊断,生成"参考标签"**
  - 阈值法、Isolation Forest 与 IEC 标签做对比 → 评估"一致性与互补性"
  - 时序合成器的状态分组也基于 IEC 诊断结果,而非 Fault 列
- **论文叙事**:见 `docs/03-data-strategy.md` 调整后版本
- **为什么不是循环论证**:被评估的是"阈值法/IF",IEC 是国际标准,以标准为参照评估非标准方法,方法论成立
- **影响范围**:模块 3(异常检测)、模块 5(预警决策回测)的评估方式都需要按此思路重写

### D-009:数据集字段调整

- **删除 `H2O` 列**:100% 全空,无信息
- **CO/CO2** 缺失约 22%/31%:LSTM 训练时仅用有值样本(影响"7 种气体同步预测",可能要降级为 5 种气体同步 + CO/CO2 单独建模)
- **O2/N2** 缺失 34%:仅作辅助分析,不进 LSTM

### D-010:LSTM 预测目标气体数量待定

- **原计划**:7 种气体同步预测
- **新风险**:CO(22% 缺失)、CO2(31% 缺失)缺值多
- **应对**:在合成器中**对所有 7 种气体都生成完整时序**(由模型/规则填补缺失),保留"7 气体同步预测"的论文叙事
- **备选**:实在不行,降级为 5 气体同步(H2/CH4/C2H4/C2H6/C2H2)+ CO/CO2 独立 ARIMA

---

## 2026-06-02 项目正式开发启动

### D-006:依赖分批安装策略(踩坑教训)

- **背景**:一次性 `pip install -r requirements.txt` 在 Python 3.9 + macOS 上很慢(可能触发部分包源码编译),且 jupyter 体积很大
- **决策**:**分阶段装**
  - 阶段一(已完成):FastAPI + SQLAlchemy + Pydantic 等后端最小集合
  - 阶段一收尾(EDA 前):pandas + numpy + openpyxl + jupyter + matplotlib + seaborn
  - 阶段二:scikit-learn + statsmodels(异常检测 + ARIMA)
  - 阶段四:tensorflow / keras(LSTM,届时 Python 升级到 3.10/3.11 同步进行)
  - 阶段六:langchain + dashscope
- **`requirements.txt` 中已用注释标记**哪些包延后装
- **教训**:`uvicorn[standard]` 在 zsh 里要加引号 → `'uvicorn[standard]'`

### D-007:Python 3.9 兼容性已知陷阱

- **PEP 604**(`str | None`)在 Python 3.9 不可用 → 全部改为 `Optional[str]`
- **`list[str]` 等内置泛型**在 3.9 用作类型注解会出错 → 改为不写返回类型,或 `List[str]`
- **SQLAlchemy `Mapped[date]`**:`date` 既是类型又是字段名时会冲突 → 用 `from datetime import date as DateType` 别名导入
- **临时方案**:已在代码中规避;**第 9 周升级 Python 3.11 后**:可以用回原生写法

### D-001:数据库选型 MySQL → SQLite

- **决策**:用 SQLite 替代论文规划的 MySQL
- **理由**:零安装、数据量级足够、部署演示零风险
- **风险**:答辩可能被问"为什么不用 MySQL"
- **应对话术**:"通过 SQLAlchemy ORM 实现,语法兼容 MySQL,数据量级下 SQLite 已满足且更轻量"
- **细节**:见 [01-tech-stack.md](./01-tech-stack.md)

### D-002:数据策略——时序合成(方案 B)

- **背景**:原始数据集是快照型,无时间戳;LSTM 需要时序
- **决策**:基于真实分布,通过状态机演化 + 平滑扰动构造时序
- **数据规模目标**:约 50 台虚拟变压器 × 90 天 ≈ 4500 行
- **论文表述**:坦诚说明数据来源与合成方法,定位为"验证预测+预警完整流程"
- **细节**:见 [03-data-strategy.md](./03-data-strategy.md)

### D-003:Python 版本暂保持 3.9.6

- **现状**:macOS 系统自带 Python 3.9.6
- **决策**:当前阶段不动,**第 9 周做 LSTM 前升级到 3.10/3.11**
- **理由**:避免现在折腾环境,优先推进业务进度;TF 在 3.9/Apple Silicon 兼容度稍弱但能跑
- **升级方式预案**:pyenv 或 conda,不动系统 Python

### D-004:本周(第 6 周)目标确定

- 周末前实现"前端 → API → SQLite"最小闭环
- Dashboard 用真实数据(替换静态模拟)
- 详见 [02-dev-plan.md](./02-dev-plan.md) 阶段一

### D-005:文档维护机制

- 在 `docs/` 沉淀所有决策
- 每次重大变更同步更新本文件
- 文档面向"未来的自己"和"答辩评委"

---

## 待决策(挂起)

- [ ] 是否需要为 Agent 准备本地降级 LLM(如 Ollama),以防通义千问 API 不稳定?
- [ ] 训练好的 LSTM `.h5` 文件是否要纳入 git?(大概率不,通过 git-lfs 或 .gitignore 排除)
- [ ] 部署方式:答辩 Demo 用本地启动还是简单容器化?(倾向本地)
