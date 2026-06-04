# 数据策略:从快照数据集到时序数据集

## 原始数据集

- **文件**:`FinalDataSet_DGA.xlsx`
- **规模**:**743 行 × 12 列**(原以为 744,实际 743)
- **来源**:公开 DGA 数据集(具体来源待补充)

### 字段结构

```
Transformer | H2 | CH4 | C2H4 | C2H6 | C2H2 | CO | CO2 | O2 | N2 | H2O | Fault
```

- 第一列 `Transformer`:整数编号(1~743,**每行一个,不重复**——确认是"快照集合"而非时序)
- 7 种 DGA 气体:H2, CH4, C2H4, C2H6, C2H2, CO, CO2
- 辅助气体:O2, N2, H2O
- `Fault`:故障标签

### EDA 关键发现(2026-06-03)

#### 1. 缺失值情况

| 列 | 缺失率 | 处理 |
|----|-------|------|
| H2, CH4, C2H4, C2H6 | 0% | 完整可用 |
| C2H2 | 0.1%(1 行) | 用 0 填充 |
| CO | 21.8% | 训 LSTM 时仅用有值样本,或按变压器均值插值 |
| CO2 | 31.4% | 同上 |
| O2, N2 | 34.2% | 仅用作辅助分析,不进 LSTM |
| **H2O** | **100% 全空** | **直接删除** |

#### 2. 🔴 Fault 标签严重不均衡

```
NA               725 (97.6%)   ← 未标注,数量占绝大多数
No Fault          14 (1.9%)
Electrical Fault   2 (0.3%)
Thermal Fault      2 (0.3%)
```

**影响**:原计划用 `Fault` 列做 ground truth 评估异常检测/规则回测,**该路径几乎不可行**(有效标签仅 18 行,故障类型各仅 2 行)。

#### 3. 数值分布:极端长尾

| 气体 | min | max | mean |
|------|-----|-----|------|
| H2 | 0 | 23349 | 348 |
| CH4 | 0 | 11646 | 160 |
| C2H4 | 0 | 46976 | 282 |
| C2H2 | 0 | 9740 | 94 |

- **NA 样本下气体均值高、方差大**(H2 std=1694)→ 推断这 725 个 NA 样本**包含大量已故障变压器,只是没人标注**
- **No Fault 样本气体浓度极低**(H2 mean=6.79)→ 这是真正的健康基线

#### 4. Fault 状态下的气体特征(用于合成器参数化)

| Fault | n | H2 mean | CH4 mean | C2H2 mean |
|-------|---|---------|----------|-----------|
| No Fault | 14 | 6.79 | 29.29 | 1.00 |
| Thermal | 2 | 423 | 1062 | 4.90 |
| Electrical | 2 | 293 | 192 | 1093.50 |
| NA | 725 | 354.96 | 160.16 | 92.96 |

符合 IEC 60599 经验:Thermal Fault 以 CH4 突出,Electrical Fault 以 C2H2 突出。

## 🔄 调整后的数据策略

### 核心变更:用 IEC 三比值法做"自动打标"替代不可靠的 Fault 列

| 用途 | 原方案 | 新方案 |
|------|--------|--------|
| Ground truth 来源 | Fault 列(不可用) | IEC 60599 三比值法对 743 行**自动诊断** |
| 异常检测对比的评估 | 阈值法/IF vs Fault 列 | 阈值法/IF vs IEC 自动诊断结果 |
| 时序合成器的状态库 | 按 Fault 分组采样 | 按 IEC 自动诊断结果分组采样 |

**论文叙事**:

> 原始公开数据集中 97.6% 样本未标注故障状态,无法直接作为算法评估的 ground truth。本文采用 IEC 60599 国际标准三比值法对全量样本进行自动诊断,得到"参考标签";阈值法、Isolation Forest 等其他异常检测方法以此为基准进行横向对比,评估各方法与国际标准的一致性与互补性。

**为什么不是循环论证**:被评估的是"阈值法"和"Isolation Forest",而 IEC 是国际标准。这是"以国标为参照评估非国标方法",方法论上成立。

## 时序合成方案(方案 B,基于 EDA 后修正)

### 核心思路

把 743 行当作 743 个**独立样本快照**,基于真实分布**为每台虚拟变压器构造时序演化**。

### 实现策略(修订版)

1. **数据分组依据:IEC 自动诊断结果**(而非不可靠的 Fault 列)
   - 通过 IEC 60599 三比值法将 743 行分为:健康 / 局部放电 / 低能放电 / 高能放电 / 低温过热 / 中温过热 / 高温过热 等
   - 每组形成"状态分布池"

2. **状态机演化**:
   - 每台虚拟变压器初始为"健康"
   - 90 天内,按马尔可夫链小概率向某种异常状态迁移
   - 大部分虚拟变压器维持健康(模拟真实运维 70-80% 正常率)

3. **采样规则**:
   - 在某状态内,从该状态的分布池抽样均值 + 用真实样本 std 控制噪声
   - **相邻日变化幅度受限**(关键!气体浓度日变化通常缓慢,贴近物理现实)
   - **对数空间扰动**(应对长尾分布,避免负值)

4. **工况模拟**(数据集没有,本文合成):
   - 油温:基础温度 + 日波动 + 负载相关项,合理区间 30-90℃
   - 负载电流:工作日/周末模式,正弦周期波动
   - 环境温度:季节性正弦 + 日内波动

### 论文表述方案

在论文「数据采集」章节坦诚说明:

> 本研究使用的公开 DGA 数据集为快照型样本,本文基于真实样本的分布特征,通过状态机演化与平滑扰动构造时序数据,以验证 LSTM 时序预测流程的完整性。该方法在保留真实样本分布特征的同时,引入了符合物理规律的时序演化,确保预测模型训练的有效性。

**这是常见做法**(数据增强、半合成数据集),答辩站得住脚。

### 输出格式

目标 CSV(`data/synthetic_timeseries.csv`):

```
transformer_id, date, H2, CH4, C2H4, C2H6, C2H2, CO, CO2, O2, N2, H2O,
oil_temp, load_current, ambient_temp, fault_state
```

- `transformer_id`:虚拟变压器 ID(1-N,基于原始 Transformer 列)
- `date`:合成日期(如 2025-01-01 ~ 2025-03-31,90 天)
- 气体浓度列:11 个
- 工况列:3 个
- `fault_state`:演化过程中的状态(便于回测验证)

### 数据规模(单设备方案,2026-06-03 调整)

- **1 台虚拟变压器 × 360 天 = 360 行**
- 时序跨度覆盖完整四季,体现环境温度的季节性变化
- 与原始 743 行真实样本规模相当(略少),信息密度合理
- 启用「事件预算」机制保证 360 天内至少注入若干次异常事件,避免单条链运气好全程健康

## 数据库设计(SQLite)

### 表结构(初稿,EDA 后可能调整)

```sql
-- 监测数据表(时序)
CREATE TABLE monitoring (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transformer_id INTEGER NOT NULL,
  date DATE NOT NULL,
  h2 REAL, ch4 REAL, c2h4 REAL, c2h6 REAL, c2h2 REAL,
  co REAL, co2 REAL, o2 REAL, n2 REAL, h2o REAL,
  oil_temp REAL, load_current REAL, ambient_temp REAL,
  fault_state TEXT,
  UNIQUE(transformer_id, date)
);

-- 预警表
CREATE TABLE warnings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  transformer_id INTEGER NOT NULL,
  triggered_at TIMESTAMP NOT NULL,
  level TEXT NOT NULL,            -- red/orange/yellow/blue
  rule_type TEXT NOT NULL,        -- hard/soft/combo
  rule_id TEXT,
  message TEXT,
  agent_review TEXT,              -- LLM 复核意见
  resolved INTEGER DEFAULT 0
);

-- Agent 执行日志表
CREATE TABLE agent_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TIMESTAMP NOT NULL,
  transformer_id INTEGER,
  status TEXT,                    -- success/failed/fallback
  trace JSON,                     -- 完整 ReAct 轨迹
  duration_ms INTEGER
);
```

## 维护

- **EDA 完成后**(6/3),回填"已发现的问题"小节的真实统计数字
- **合成器实现后**,补充实际生成参数与 seed 值,保证可复现
