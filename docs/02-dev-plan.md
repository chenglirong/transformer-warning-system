# 9 周开发规划(第 6-15 周)

> 起点:2026/06/02(第 6 周周一) | 终点:第 15 周答辩
> 节奏:每天可投入开发

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
| 6/3 周二 | EDA:探索 744 行,搞清缺失值/分布/Fault 类别 | `notebooks/01_eda.ipynb` |
| 6/4 周三 | 设计 + 实现时序合成器 | `data/synthetic_timeseries.csv` |
| 6/5 周四 | 工况模拟(油温/负载/环温)+ 数据入库 | SQLite `.db` 文件 |
| 6/6 周五 | 特征工程模块 | `BE/app/algorithms/features.py` |
| 6/7-6/8 周末 | 前端 → API → SQLite 最小闭环 | Dashboard 显示真实数据 |

**🎯 周末交付**:Dashboard 所有 KPI 来自 SQLite 真实数据。

---

## 阶段二:异常检测(第 7 周,6/9-6/15)

| 任务 | 输出 |
|------|------|
| 阈值法(国标 DL/T 722) | `algorithms/detect/threshold.py` |
| IEC 三比值法 | `algorithms/detect/iec.py` |
| Isolation Forest | `algorithms/detect/iforest.py` |
| 三方法对比实验(Fault 列做 ground truth) | `notebooks/02_detection_compare.ipynb` |
| 准确率/召回率/误报率对比表 → 论文素材 | 表格 + 混淆矩阵图 |
| DetectionView 对接真实 API | `/api/detect` |

**🎯 巧思**:`Fault` 列正好做 ground truth,这是数据集的天然优势。

---

## 阶段三:中期检查(第 8 周,6/16-6/22)

**这周不开发新功能**,做整合:

- 把阶段一、二的成果完整对接到前端
- 准备中期检查材料(进度报告 + Demo)
- 处理一切积压的小问题

**🎯 中期交付**:数据 → 后端 API → 前端真实展示的最小闭环全通。

---

## 阶段四:LSTM 预测(第 9-10 周,6/23-7/6)⭐核心

| 任务 | 输出 |
|------|------|
| 滑窗造样本(30 天 → 第 31 天) | `algorithms/predict/dataset.py` |
| ARIMA 基线(7 气体 for 循环) | `algorithms/predict/arima.py` |
| LSTM 多输出回归 `Sequential([LSTM(64), Dense(7)])` | `algorithms/predict/lstm.py` + `model.h5` |
| 滚动预测(迭代 3 次 → 1-3 天) | `algorithms/predict/rolling.py` |
| 对比实验(MAE/RMSE/MAPE) | `notebooks/03_predict_compare.ipynb` |
| PredictionView 对接 | `/api/predict/lstm` |

**⚠️ 风险预案**(论文已写):
- 第 9 周末必须能"跑通"(loss 下降即可)
- 第 10 周再调精度
- 跑不通启用论文里的兜底叙事(改写为"ARIMA 在该数据集上更稳健")

---

## 阶段五:预警决策(第 11-12 周,7/7-7/20)⭐核心

| 任务 | 输出 |
|------|------|
| 规则引擎核心(YAML/JSON 配置化) | `algorithms/warning/rules.yaml` |
| 三类规则:硬规则、软规则、组合规则 | `algorithms/warning/engine.py` |
| 四级分级(红橙黄蓝) | 同上 |
| 误报控制:连续 N 次触发 + 24h 去重 | `algorithms/warning/dedup.py` |
| 历史回测(744 条原始数据) | `notebooks/04_backtest.ipynb` |
| AlertsView 对接 | `/api/warning/check` |

**🎯 巧思**:回测时用 Fault 标签算 TP/FP/FN → 论文素材。

---

## 阶段六:LangChain Agent(第 13 周,7/21-7/27)⭐⭐⭐最大创新

严格按论文规划(354-371 行),**不要扩展**:

| 任务 | 行数 |
|------|------|
| 4 个 `@tool` 封装 | ~80 |
| ReAct Prompt 模板(写死 5 步) | ~30 |
| AgentExecutor + 定时调度 | ~40 |
| 降级处理(Agent 失败 → 纯 Pipeline) | ~20 |
| Agent 执行轨迹接入 AnalysisView | `/api/agent/run` |

**⚠️ 提前**:第 12 周末就跑通 LangChain hello world,确认 API key/环境 OK。

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
