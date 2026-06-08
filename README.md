# 电力设备健康管控智能体设备预警系统研究与实现

本科毕业设计。以变压器溶解气体分析(DGA)为切入点,基于 LSTM 多输出预测 + LangChain Agent,构建电力设备健康管控的全链路智能体预警系统。

## 项目结构

```
.
├── FE/              Vue3 + ECharts 前端
├── BE/              FastAPI + SQLite 后端
├── data/            原始 + 合成数据
├── notebooks/       Jupyter 实验
├── docs/            开发文档(决策、规划、架构)
├── 论文梳理.md
└── 开题报告PPT大纲.md
```

## 快速开始

### 后端

```bash
cd BE
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.init_db
uvicorn app.main:app --reload
```

→ http://localhost:8000/docs

### 前端

```bash
cd FE
npm install     # 已 install 过可跳过
npm run dev
```

→ http://localhost:5173

## 文档导航

- 📋 [开发文档总索引](./docs/00-INDEX.md)
- 🎯 [第 6-15 周开发规划](./docs/02-dev-plan.md)
- 🏗 [系统架构](./docs/04-architecture.md)
- 📝 [关键决策日志](./docs/05-decisions-log.md)
- 📊 [论文梳理](./论文梳理.md)
