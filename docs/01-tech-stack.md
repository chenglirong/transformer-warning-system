# 技术选型与理由

> 最终选型,与论文梳理可能略有差异之处已说明。

## 选型总表

| 层级 | 选型 | 与论文梳理差异 | 理由 |
|------|------|---------------|------|
| 前端 | Vue3 + Vite + Tailwind + ECharts + iconify | 一致 | 已搭建 |
| 后端 | **FastAPI**(Python) | 一致 | 自带 Swagger 文档(答辩加分)、异步支持(Agent 调 LLM 不阻塞)、Pydantic 类型校验 |
| 数据库 | **SQLite** ⚠️ | 论文写的 MySQL | 零安装(Python 自带)、数据量(几万行)绰绰有余、一个 `.db` 文件易部署、答辩演示零风险 |
| ML 框架 | TensorFlow + Keras | 一致 | 论文已定,第 9 周再装 |
| 时序基线 | ARIMA(statsmodels) | 一致 | - |
| 异常检测 | 阈值法 + IEC 三比值 + Isolation Forest(sklearn) | 一致 | - |
| Agent 框架 | LangChain | 一致 | - |
| LLM | 通义千问 qwen-turbo(通过 LangChain ChatTongyi) | 一致 | 国产、有免费额度 |

## 关键差异说明:为什么把 MySQL 换成 SQLite

**这是相对论文梳理的唯一选型变更**,需要在答辩或论文里有说法:

- **数据量级**:本项目数据量在万行级别,SQLite 性能完全胜任
- **工程务实**:SQLite 零运维成本,降低部署与演示风险
- **论文表述**:可在论文里写"使用 SQLite 作为关系型数据库,后续可平滑迁移至 MySQL"
- **代码兼容**:通过 SQLAlchemy ORM 编写,后续切换 MySQL 仅需改连接字符串

**评委如果问"为什么不用 MySQL"**:答"SQLite 与 MySQL 在 SQL 语法层兼容,本项目数据量级下 SQLite 已满足需求且部署更轻;通过 SQLAlchemy 抽象层实现可平滑迁移"。

## Python 环境

- **当前**:Python 3.9.6(macOS 系统自带)
- **建议升级时机**:第 9 周开始做 LSTM 前,升级到 3.10 或 3.11(TensorFlow 在 Apple Silicon 上的支持更稳)
- **升级方式**:用 pyenv 或 conda,避免动系统 Python

## 暂不引入的技术

按论文"不做"清单严格执行,这里再次明确:

- ❌ Transformer / Informer 等高级时序模型
- ❌ GRU / Prophet 等额外基线
- ❌ Autoencoder 异常检测
- ❌ 置信区间估计、动态阈值学习、多模型投票
- ❌ RAG 知识库、多 Agent 协作、复杂 Memory 管理
- ❌ AHP 层次分析

这些都明确写在"未来工作"章节,**不在本项目范围内**。
