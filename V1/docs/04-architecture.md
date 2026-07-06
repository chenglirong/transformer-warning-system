# 系统架构与目录约定

> **职责**:分层架构、目录约定、系统边界(刚性约束)、接口清单。查「能不能这么写代码/边界在哪」时看这里。实验分析见 07,答辩话术见 08。

## 四层架构

```
┌─────────────────────────────────────────────────┐
│  应用层  Vue3 + ECharts 监控大屏(FE/)           │
└──────────────────┬──────────────────────────────┘
                   │ HTTP / JSON
┌──────────────────┴──────────────────────────────┐
│  智能层  LangChain Agent(BE/app/agent/)         │
│         通义千问 + 4 个 @tool + ReAct 流程       │
└──────────────────┬──────────────────────────────┘
                   │ 函数调用
┌──────────────────┴──────────────────────────────┐
│  算法层  异常检测 + LSTM 预测 + 规则决策          │
│         (BE/app/algorithms/)                     │
└──────────────────┬──────────────────────────────┘
                   │ SQLAlchemy ORM
┌──────────────────┴──────────────────────────────┐
│  数据层  SQLite(BE/data/app.db)                 │
└─────────────────────────────────────────────────┘
```

## 目录结构

```
transformer-warning-system/
├── FE/                          ✅ 已有 Vue3 前端
│   └── src/
│       ├── views/               5 个视图(Dashboard/Detection/Prediction/Analysis/Alerts)
│       ├── components/          通用组件
│       ├── composables/         组合式 API
│       └── utils/
│
├── BE/                          🆕 后端
│   ├── app/
│   │   ├── main.py              FastAPI 入口
│   │   ├── config.py            配置(环境变量、路径)
│   │   ├── deps.py              依赖注入(DB session 等)
│   │   │
│   │   ├── api/                 路由层(薄)
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── data.py          数据查询
│   │   │   ├── detect.py        异常检测
│   │   │   ├── predict.py       LSTM 预测
│   │   │   ├── warning.py       预警
│   │   │   └── agent.py         Agent 执行
│   │   │
│   │   ├── db/                  数据访问层
│   │   │   ├── __init__.py
│   │   │   ├── session.py       SQLAlchemy 引擎、Session
│   │   │   ├── models.py        ORM 模型
│   │   │   └── schema.sql       原始 DDL(参考)
│   │   │
│   │   ├── algorithms/          算法层(核心)
│   │   │   ├── features.py      特征工程
│   │   │   ├── detect/          异常检测三方法
│   │   │   ├── predict/         LSTM + ARIMA
│   │   │   └── warning/         规则引擎
│   │   │
│   │   └── agent/               LangChain Agent
│   │       ├── tools.py         4 个 @tool
│   │       ├── prompts.py       ReAct 模板
│   │       └── executor.py      AgentExecutor 包装
│   │
│   ├── scripts/                 一次性脚本
│   │   ├── init_db.py           建表
│   │   ├── synthesize_data.py   合成时序数据
│   │   ├── import_data.py       导入 SQLite
│   │   └── train_lstm.py        训练 LSTM
│   │
│   ├── models/                  训练好的模型(.h5)
│   ├── data/                    SQLite 数据库文件
│   │   └── app.db
│   │
│   ├── tests/                   pytest
│   ├── requirements.txt
│   ├── .env.example             环境变量模板
│   └── README.md
│
├── data/                        🆕 原始数据 + 合成数据
│   ├── raw/
│   │   └── FinalDataSet_DGA.xlsx
│   ├── synthetic_timeseries.csv
│   └── README.md
│
├── notebooks/                   🆕 实验 notebook
│   ├── 01_eda.ipynb
│   ├── 02_detection_compare.ipynb
│   ├── 03_predict_compare.ipynb
│   └── 04_backtest.ipynb
│
├── docs/                        🆕 本目录
└── 论文梳理.md
```

## 系统边界(刚性约束)⭐

本系统是「**预警系统**」,不是「故障诊断系统」也不是「健康评估系统」。
答辩时必问的核心边界,**所有代码与文档都必须守住**。

### ✅ 系统对外输出

- 预警等级(红 / 橙 / 黄 / 蓝)
- 哪些气体超标 / 趋势异常
- 预测的未来 1-3 天浓度趋势
- 触发的预警规则编号(rule_id)
- 二分类的健康状态(healthy / abnormal)

### ❌ 系统对外**不**输出

- 「故障类型是 XXX」(那是诊断系统的职责)
- 「健康度评分 X 分」(那是状态评估的职责)
- 「建议立即停机检修」(那是运维决策的职责)

### ⚠️ IEC 三比值法的边界使用

IEC 三比值法虽然能输出具体故障类型(如 Thermal Fault >700℃),但本系统中:

| 用途 | 是否允许 |
|------|---------|
| 异常二分类(`is_abnormal`) | ✅ 允许 |
| 合成器的状态分组依据 | ✅ 允许(内部数据生成) |
| Ground truth 评估算法准确率 | ✅ 允许(内部回测) |
| 在 Dashboard / 预警通知 / 任何对外接口暴露具体故障类型 | ❌ **禁止** |

### API 边界规约

- **业务接口**(`/api/data/...`、`/api/warning/...`、`/api/agent/...`):只输出 `is_abnormal: bool`,**不**输出 `fault_state` 字段
- **内部接口**(`/api/data/_internal/...`):允许暴露细节,但前缀 `_internal`,前端 Dashboard **不消费**
- **数据库层**(`monitoring.fault_state` 列):保留具体状态,仅供内部回测

### 答辩话术(必备)

> Q:你这个系统和故障诊断系统有什么区别?
>
> A:本系统聚焦「前瞻性预警」,回答「何时报警、报几级、如何响应」三个问题;不回答「故障原因是什么、健康度多少」。IEC 三比值法在算法层使用,但**仅作为内部异常二分类工具**,系统对外不输出故障类型,边界严格守住。

> Q:为什么不做诊断和评估?
>
> A:三个原因:① 学术诚实——诊断需专家标注的真实故障数据,公开集无法支撑;② 避免越界——本课题聚焦预警全链路,诊断/评估属另一方向;③ 工程务实——毕设时间内做扎实一件事胜过样样不深。
>
> (实测数据支撑的详细话术见 [08-答辩问答](./08-defense-qa.md);实验分析见 [07-翻车分析](./07-failure-analysis.md))

---

## 分层职责约定

| 层 | 职责 | 禁止 |
|----|------|------|
| **api/** | 参数校验、调用 algorithms、返回 JSON | ❌ 写算法逻辑<br>❌ 直接写 SQL |
| **algorithms/** | 纯算法,输入 DataFrame/array,输出结果 | ❌ 依赖 FastAPI/请求上下文<br>❌ 直接读数据库(应通过参数传入) |
| **db/** | ORM 模型、Session 管理 | ❌ 业务逻辑 |
| **agent/** | LLM 编排、ReAct 流程 | ❌ 重复实现 algorithms 已有逻辑 |

## 接口约定(实际端点,2026-06-12 校准)

```
GET  /api/health
# 数据
GET  /api/data/transformers          # 变压器列表
GET  /api/data/timeseries/{tid}      # 单台时序(可加 ?days=&end=)
GET  /api/data/latest/{tid}          # 最新一日(含 features 衍生指标)
GET  /api/data/snapshot/{tid}        # 指定日快照 ?on=YYYY-MM-DD
GET  /api/data/dates/{tid}           # 全部日期+二分类(日期选择器)
GET  /api/data/overview              # 全局概览
GET  /api/data/_internal/state_distribution   # [内部]状态分布
# 检测
GET  /api/detect/methods/{tid}       # 最新日三方法判定+投票
GET  /api/detect/recent/{tid}        # 近 N 日三方法逐日+投票 ?days=7
GET  /api/detect/_internal/compare   # [内部]三方法全量对比指标
# 预测
GET  /api/predict/compare            # ARIMA vs LSTM 评估+曲线+滚动预测
# 预警
GET  /api/warning/backtest           # 回测混淆/指标/四级分布/全量告警
# Agent(模块 6 待开发)
POST /api/agent/run                  # 手动触发 Agent 全流程
GET  /api/agent/runs                 # Agent 执行历史
```

> 边界:业务接口只回 is_abnormal,内部评估走 `/_internal/*`。Agent 端点待模块 6。

## 跨域

- FE 端 Vite 开发服务默认 `:5173`,BE 端 FastAPI `:8000`
- BE 用 `CORSMiddleware` 允许 `http://localhost:5173`
