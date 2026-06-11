# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

本科毕业设计,正式论文标题:**《电力设备健康管控智能体设备预警系统研究与实现》**。以变压器溶解气体分析(DGA)数据为切入点,构建"数据合成 → 异常检测 → 时序预测 → 智能预警"全链路。最大创新点是 **LangChain Agent 端到端串联预警流程**。

时间窗:第 6-15 周(2026/06/02 ~ 08/10),第 8 周中期检查,第 15 周答辩。

## 协作约定(重要,优先遵守)

- **用户说"继续开发"时,先按顺序读 `docs/02-dev-plan.md`(定位当前第几周该做什么)和 `docs/05-decisions-log.md`(上次进度 + 挂起项),确认任务后再动手。** 不要直接写代码。
- **用户会主动质疑方向**("必须这么做吗""是否偏移")。遇到这类问题:先读论文/docs 对应段落 → 列证据强度(强/中/弱)→ 给 2-3 个备选 + 推荐 → 等用户拍板。不要顺着附和。
- **三处同步原则**:任何影响论文叙事的决策,必须同步更新 ① `docs/05-decisions-log.md`(新决策追加到顶部,编号 D-XXX)② `论文梳理.md` 末尾「实施期修订」节。
- **答辩前置思维**:每个技术决策都预想"评委会怎么问",话术沉淀进 `docs/04-architecture.md`。
- **前端视图非刚性,可裁剪/改形但须先问(D-030)**:论文模块 7 画的大屏不是锁死的规格。当某模块实现不了、或实现得不正确(如 LSTM 预测精度差)时,对应前端视图的「展示什么、以什么形态展示」可以删掉或改形(如把「LSTM 预测曲线」改成「LSTM vs ARIMA 对比」),不必为凑齐版式硬塞误导性可视化。**但每次裁剪/改形都要先列证据 + 给方案 + 等用户拍板,不自行决定。** 不可破的硬约束不变:系统刚性边界(不输出诊断/故障类型/健康评分,IEC 仅内部)+ P1 诚实原则(不杜撰逼真假数据,D-023)。

## 系统刚性边界(API / 文档 / 答辩都必须守住)

这是一个**预警系统,不是诊断/评估系统**。

- **对外可输出**:预警等级、哪些气体超标、未来 1-3 天趋势、触发的规则编号、二分类健康状态(`is_abnormal`)。
- **对外禁止输出**:具体故障类型(如 "Thermal Fault >700℃")、健康度评分、运维建议 —— 那是诊断/评估/决策系统的职责。
- **IEC 60599 三比值法**:仅允许**内部**使用(异常二分类、合成器状态分组、ground truth 打标)。**禁止**在 Dashboard / 预警通知 / 任何业务 API 暴露其推出的具体故障类型。业务接口只返回 `is_abnormal: bool`,内部细节走 `/_internal/*`。

## 架构

后端严格分层,**算法层与 Web/DB 解耦**是核心约定:

- `BE/app/api/` —— 路由层(薄,只做 HTTP,不写业务逻辑)
- `BE/app/algorithms/` —— **纯算法层,输入输出都是 DataFrame,不依赖 DB/HTTP**。子目录:`detect/`(异常检测,含 `iec.py`)、`predict/`(LSTM)、`warning/`(预警规则)、`synthesis.py`(时序合成)、`features.py`(特征工程)
- `BE/app/db/` —— SQLAlchemy ORM 模型 + session
- `BE/app/core/` —— 通用响应封装
- `BE/app/agent/` —— LangChain Agent(待开发,最大创新点)
- `BE/scripts/` —— 一次性脚本(建库、合成、训练),用模块方式跑:`python -m scripts.xxx`
- `FE/src/service/` —— 前端数据层(统一 fetch 封装);`vite.config.js` 里 `/api` proxy 到 `:8000` 规避跨域

数据流(脚本按此顺序跑):
`synthesize_data.py` → `data/synthetic_timeseries.csv` → `import_data.py`(入 SQLite)/ `build_features.py` → `data/featured_timeseries.csv`;`eda.py` → `notebooks/figures/*.png`。

## 常用命令

```bash
# 一键起前后端(需先建好 BE/.venv 和 FE/node_modules)
./start.sh

# 后端单独启动
cd BE && source .venv/bin/activate
python -m scripts.init_db          # 建表
uvicorn app.main:app --reload      # → http://localhost:8000/docs

# 前端单独启动
cd FE && npm run dev               # → http://localhost:5173
```

## 关键技术约束

- **Python 3.9.6**(macOS 系统自带,第 9 周做 LSTM 时才升级 3.11)。3.9 兼容陷阱见 `docs/06-python-cheatsheet.md`:
  - 不能用 `str | None`(PEP 604)→ 用 `Optional[str]`
  - 不能用 `list[str]` 作注解 → 用 `List[str]`
  - SQLAlchemy `Mapped[date]` 与字段名 `date` 冲突 → `from datetime import date as DateType`
- **依赖分批装**,别一次性 `pip install -r requirements.txt`(3.9 下慢/易卡)。requirements.txt 内有注释标记延后的包。zsh 下 `'uvicorn[standard]'` 要加引号。
- **数据库 SQLite**(替代论文写的 MySQL),通过 SQLAlchemy ORM,语法兼容。

## 数据事实(答辩关键,改动需同步论文)

- 原始 `data/raw/FinalDataSet_DGA.xlsx`:743 行快照样本,**无时间戳**,`Fault` 列 97.6% 未标注。
- 合成数据:**1 台虚拟变压器 × 360 天**(单设备方案),健康约 75% / 异常约 25%,跨完整四季。
- Ground truth:用 IEC 60599 三比值法对全量自动打标(`data/labeled_iec.csv`),阈值法/Isolation Forest 等非国标方法以此为基准做对比。

## 文档体系

`docs/` 是项目记忆,所有已确定的决策/选型/规划都在这里(不存临时讨论)。索引见 `docs/00-INDEX.md`。写决策要写**理由**,面向"未来的自己"和"答辩评委"。
