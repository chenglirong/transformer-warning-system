"""DGA 时序合成器(v2 数据地基,难点1)。

目标:原始 `FinalDataSet_DGA.xlsx` 是 743 条**无时间戳**快照,做不了产气速率/趋势。
为给检测/诊断/告警/趋势全链路一个统一输入,基于其**真实统计分布**合成
「单台虚拟变压器 × 360 天」DGA 时序,保持:

  1. 分布形态 —— 各气体对数正态、强右偏(原始偏度 6~17),故全程在 log10 空间建模。
  2. 气体相关性 —— 烃类强相关(CH₄-C₂H₄/C₂H₆ log 空间 0.6~0.78),用 Cholesky
     对每日 driving noise 着色注入,而非逐气体独立生成。
  3. 故障物理特征 —— 异常态锚点直接取自数据集**真实故障样本**:
     放电←Electrical Fault(C₂H₂ 显著↑)、过热←Thermal Fault(C₂H₄/CH₄↑、C₂H₂ 低),
     健康←No Fault。与 DL/T 722 特征气体法/三比值/Duval 判型方向吻合。

答辩口径(P1 诚实):这是「分布保持的时序构造」,不是凭空生成——给真实快照分布
附加时间维度。合成数据上只论证方法可行,不吹真实精度。真实故障样本各仅 2 条
(Electrical/Thermal),故异常态锚点用其均值 + 固定 log-σ,如实交代样本稀疏。

本模块属纯算法层:输入输出都是 DataFrame,不碰 DB/HTTP。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ============================================================
# 气体口径(蓝图:7 种全用平等;烃类有 Analysis 锚点,CO/CO₂ 用 xlsx 有值部分)
# ============================================================

# 5 烃类:100% 完整,检测/诊断/相关性建模核心
HYDROCARBONS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]
# CO/CO₂:原始覆盖较低、锚点弱于烃类(答辩如实交代),但仍是表5主判据
OXIDES = ["co", "co2"]
AUX_GASES = OXIDES  # 兼容旧名;语义非「辅助」
GAS_KEYS = HYDROCARBONS + OXIDES

# 原始 xlsx 长列名 → 短键
RAW_COLUMN_MAP = {
    "Hydrogen (H2)": "h2",
    "Methane (CH4)": "ch4",
    "Ethylene (C2H4)": "c2h4",
    "Ethane (C2H6)": "c2h6",
    "Acetylene (C2H2)": "c2h2",
    "Carbon Monoxide (CO)": "co",
    "Carbon Dioxide (CO2)": "co2",
}

NORMAL = "Normal"
# 异常态命名 = 故障机理大类(对齐 Duval/三比值:放电→D1/D2、过热→T1/T2/T3)
DISCHARGE = "放电"
OVERHEAT = "过热"
FAULT_STATES = [DISCHARGE, OVERHEAT]

# 原始 Fault 标签 → 状态(异常态锚点取自真实故障样本)
FAULT_LABEL_MAP = {
    "No Fault": NORMAL,
    "Electrical Fault": DISCHARGE,
    "Thermal Fault": OVERHEAT,
}


# ============================================================
# 分布锚点(全部从原始 DataFrame 现算,不硬编码)
# ============================================================

@dataclass
class Anchors:
    """合成所需的真实统计锚点(log10(v+1) 空间)。"""
    # state -> gas -> 目标对数均值
    log_mu: dict[str, dict[str, float]]
    # state -> gas -> 对数标准差(状态内波动)
    log_sigma: dict[str, dict[str, float]]
    # 5 烃类 log 空间相关矩阵(顺序同 HYDROCARBONS)
    corr: np.ndarray
    # gas -> log 空间浓度上限(原始历史最高值,防合成爆表)
    log_cap: dict[str, float]


# 真实故障样本各仅 2 条,std 不可估,异常态用固定 log-σ
_FAULT_LOG_SIGMA = 0.35
# 健康态 log-σ 上限:对数空间 σ 大会指数级放大尾部,健康段偶尔飙到几千 → 被检测
# 误判成异常。健康均值本就低(总烃≈50ppm),健康变压器读数本就平稳,故大幅收窄
# 波动(0.15),让健康段死死稳在注意值1(120)以下,检测事件只剩真实故障段。
_HEALTHY_LOG_SIGMA_CAP = 0.15


def _log10p(s: pd.Series) -> pd.Series:
    """log10(v+1):压极端长尾,且天然为正。"""
    return np.log10(s.clip(lower=0) + 1.0)


def build_anchors(raw: pd.DataFrame) -> Anchors:
    """从原始快照 DataFrame 计算合成锚点。

    `raw` 需含 `Fault` 列 + RAW_COLUMN_MAP 的原始气体列(长名),或已重命名的短键列。
    """
    df = raw.rename(columns=RAW_COLUMN_MAP).copy()
    for g in GAS_KEYS:
        df[g] = pd.to_numeric(df[g], errors="coerce")

    log_mu: dict[str, dict[str, float]] = {}
    log_sigma: dict[str, dict[str, float]] = {}

    for label, state in FAULT_LABEL_MAP.items():
        sub = df[df["Fault"] == label]
        mu, sigma = {}, {}
        is_fault = state != NORMAL
        for g in GAS_KEYS:
            vals = _log10p(sub[g].dropna())
            if len(vals) == 0:
                # 该状态该气体全缺(如 No Fault 的 CO/CO₂)→ 用全体中位数兜底
                allv = _log10p(df[g].dropna())
                mu[g] = float(allv.median()) if len(allv) else 0.0
                sigma[g] = float(allv.std()) if len(allv) > 1 else 0.3
                continue
            # 健康态用中位数(对数正态下代表"典型值",不被长尾均值拉高导致健康段
            # 总烃超注意值);异常态用均值(体现真实故障样本的整体抬升)。
            mu[g] = float(vals.mean()) if is_fault else float(vals.median())
            if is_fault:
                sigma[g] = _FAULT_LOG_SIGMA  # 真实故障样本仅 2 条,std 不可估
            else:
                s = float(vals.std()) if len(vals) > 1 else _HEALTHY_LOG_SIGMA_CAP
                sigma[g] = min(s, _HEALTHY_LOG_SIGMA_CAP)  # 封顶,收窄健康段波动
        log_mu[state] = mu
        log_sigma[state] = sigma

    # 相关矩阵:全体 743 行 log 空间(最稳),仅 5 烃类(CO/CO₂ 无锚点不入矩阵)
    log_hc = pd.DataFrame({g: _log10p(df[g]) for g in HYDROCARBONS}).dropna()
    corr = log_hc.corr().to_numpy()

    # 浓度上限:原始历史最高值(log 空间),防合成尾部爆表超出真实量级
    log_cap = {g: float(_log10p(df[g].dropna()).max()) for g in GAS_KEYS}

    return Anchors(log_mu=log_mu, log_sigma=log_sigma, corr=corr, log_cap=log_cap)


def _cholesky_psd(corr: np.ndarray) -> np.ndarray:
    """Cholesky 分解;必要时加抖动保证正定(经验相关矩阵偶尔非 PD)。"""
    for jitter in (0.0, 1e-6, 1e-4, 1e-2):
        try:
            return np.linalg.cholesky(corr + jitter * np.eye(len(corr)))
        except np.linalg.LinAlgError:
            continue
    # 兜底:退化为独立(单位阵)
    return np.eye(len(corr))


# ============================================================
# 马尔可夫状态机(健康 ~75% / 异常 ~25%,事件预算保必现)
# ============================================================

# 异常事件平均持续天数 → 每次事件 ~60 天。真实故障(表D.1)一旦发生,气体维持
# 高位平台数月不回落(不是尖峰几天就消)。事件拉长 → 相对产气速率是「阶跃到位后
# 平台窄波动」而非「几天冲几万%又跌回」,速率峰值回归合理(几百%量级,非几万)。
FAULT_DURATION_MEAN_DAYS = 60


@dataclass
class StateChain:
    """虚拟变压器故障状态链。

    单设备方案下用**确定性事件区间**(非低概率转移碰运气):把目标异常天数拆成
    若干事件,放电/过热交替、均匀铺满 360 天且互不重叠,保证:
      - 两类异常都充分出现(不会一类几十天、另一类几天);
      - 异常比精确 ≈ 1-healthy_ratio;
      - 事件跨四季分布。
    事件时长在均值 FAULT_DURATION_MEAN_DAYS 上下随机(±30%),避免整齐划一失真。
    """
    n_days: int
    rng: np.random.Generator
    healthy_ratio: float = 0.75
    current: str = NORMAL
    # day_idx -> 该天所属异常态(仅异常天有键)
    _plan: dict[int, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        fault_days = round(self.n_days * (1.0 - self.healthy_ratio))
        n_events = max(2, round(fault_days / FAULT_DURATION_MEAN_DAYS))

        # 每个事件时长:总异常天数按事件数均分 ±30% 抖动
        base = fault_days / n_events
        durations = [
            max(5, round(base * (1.0 + self.rng.uniform(-0.3, 0.3))))
            for _ in range(n_events)
        ]
        # 健康天数在 (n_events+1) 段间隔里分配(首尾+事件间),均分
        gap_total = self.n_days - sum(durations)
        n_gaps = n_events + 1
        gap = max(5, gap_total // n_gaps)

        # 依次铺:gap → 事件 → gap → 事件 …,类型交替
        cursor = gap
        for i, dur in enumerate(durations):
            state = FAULT_STATES[i % len(FAULT_STATES)]
            for d in range(cursor, min(cursor + dur, self.n_days)):
                self._plan[d] = state
            cursor += dur + gap
        self._day = 0

    def step(self) -> str:
        self.current = self._plan.get(self._day, NORMAL)
        self._day += 1
        return self.current


# ============================================================
# OU 过程(对数空间日间平滑)
# ============================================================

# theta:OU 回归速度。稳态方差 ≈ σ²/(2θ) —— θ 越大,浓度被拉回目标越快、
# 长期游走幅度越小。故障态用小 θ(0.15,半衰期~4.6天,让浓度有时间爬升到故障
# 高位);健康态用大 θ(0.45,回归快),把健康段死死钉在低位均值附近,避免随机
# 游走甩出高尾被检测误判成异常。
# 故障态回归速度:目标本身在 FAULT_RAMP_DAYS 内渐变到位(见主循环),θ 只需让浓度
# 贴着渐变目标走,取适中 0.5(过小则滞后于目标、过大则日抖被放大)。
OU_THETA_FAULT = 0.5
OU_THETA_HEALTHY = 1.2   # 健康段回归更狠(半衰期~0.6天),压日间游走
# 故障目标爬升期(天):事件起始后,烃类目标在 log 空间线性从健康位爬到故障位的
# 时长。真实产气数周累积(表D.1 从 3月健康到 5月故障历时约 2 个月),取 21 天让
# 相对速率是「持续爬坡」而非阶跃。之后维持高位平台直到事件结束。
FAULT_RAMP_DAYS = 21
# 健康段日 driving noise 衰减:真实变压器健康段读数天与天之间本就平稳,日环比
# 波动应 <10%(722 相对速率月注意值)。全额 log-σ(0.15)的日噪声会造成 ~30%
# 日抖,让 722 相对速率(%/月)在健康段天天假超 10%。乘 0.35 把日抖压到 <8%,
# 使「预/处置研判」只在异常段真实爬升时触发。仅缩日间噪声,不动均值/相关性/上限。
HEALTHY_NOISE_SCALE = 0.35
# 故障段日噪声缩放:爬坡期若叠满额日抖,月环比仍会被单日噪声推出几千%假尖峰。
# 收到 0.5 让爬坡曲线干净(趋势=渐进爬升,不是锯齿),故障高位平台也窄幅波动。
FAULT_NOISE_SCALE = 0.5
# CO/CO₂ 日噪声:略低于烃类(原始覆盖率弱、σ 易放大),但仍跟状态目标爬升(7 气平等)
OXIDE_NOISE_SCALE = 0.45
# 过热态「涉纸」加强:表5「油和纸过热」主特征含 CO。真实 Thermal 仅 2 条,CO 锚点
# 可能偏弱 → 过热终态 CO 目标取 max(故障锚点, 健康锚点+抬升)。
OVERHEAT_CO_LIFT = 0.55   # log10 空间相对健康的最低抬升(约 ×3.5)
OVERHEAT_CO2_LIFT = 0.35  # CO₂ 次要特征,抬升略小



@dataclass
class SynthConfig:
    n_days: int = 360
    start_date: date = date(2024, 4, 1)  # 跨完整四季
    seed: int = 42
    healthy_ratio: float = 0.75
    transformer_id: int = 1  # 单设备方案


def synthesize(raw: pd.DataFrame, cfg: SynthConfig | None = None) -> pd.DataFrame:
    """合成单台虚拟变压器 360 天 DGA 时序。

    Args:
        raw: 原始快照 DataFrame(含 Fault 列 + 气体列,长名或短键均可)。
        cfg: 合成配置。

    Returns:
        DataFrame,列:transformer_id, date(ISO 字符串), h2..co2, fault_state
    """
    cfg = cfg or SynthConfig()
    rng = np.random.default_rng(cfg.seed)

    anchors = build_anchors(raw)
    L = _cholesky_psd(anchors.corr)  # 5x5,烃类着色矩阵
    chain = StateChain(cfg.n_days, rng, healthy_ratio=cfg.healthy_ratio)

    # 初值:从健康态锚点起步
    log_val = {g: anchors.log_mu[NORMAL][g] for g in GAS_KEYS}
    target = dict(log_val)
    target_start = dict(log_val)  # 故障爬升起点(切入故障当天的实测)
    target_end = dict(log_val)    # 故障爬升终态(故障高位平台目标)
    ramp_day = 0                  # 故障爬升已进行天数
    prev_state = NORMAL

    rows: list[dict] = []
    for day_idx in range(cfg.n_days):
        cur_date = cfg.start_date + timedelta(days=day_idx)
        state = chain.step()

        # 状态切换 → 记录事件起点,目标均值改为**逐日渐变到位**(不是一次设到高位靠
        # OU 追):真实故障是数周累积产气,目标应线性(log 空间)从健康位滑向故障位,
        # 让总烃是「持续数百%/月爬坡」而非「单日跳几万%」的假尖峰。
        if state != prev_state:
            for g in HYDROCARBONS:
                mu = anchors.log_mu[state][g]
                sig = anchors.log_sigma[state][g]
                target_end[g] = mu + rng.normal(0, sig * 0.5)  # 事件终态目标(个体差异)
                target_start[g] = log_val[g]                    # 从当前值起爬
            for g in OXIDES:
                mu = anchors.log_mu[state][g]
                sig = anchors.log_sigma[state][g]
                end = mu + rng.normal(0, sig * 0.4)
                # 过热:保证 CO/CO₂ 相对健康有可见抬升(表5 油和纸过热)
                if state == OVERHEAT:
                    floor = {
                        "co": anchors.log_mu[NORMAL]["co"] + OVERHEAT_CO_LIFT,
                        "co2": anchors.log_mu[NORMAL]["co2"] + OVERHEAT_CO2_LIFT,
                    }[g]
                    end = max(end, floor)
                target_end[g] = end
                target_start[g] = log_val[g]
            ramp_day = 0
            prev_state = state

        theta = OU_THETA_HEALTHY if state == NORMAL else OU_THETA_FAULT
        # 日噪声缩放:健康段压最狠(读数平稳),故障段中等(平台窄波动,不锯齿)
        noise_scale = HEALTHY_NOISE_SCALE if state == NORMAL else FAULT_NOISE_SCALE
        # 故障段:目标在 RAMP_DAYS 内 log 空间线性爬到终态,之后维持高位平台
        if state != NORMAL:
            frac = min(1.0, ramp_day / FAULT_RAMP_DAYS)
            for g in GAS_KEYS:
                target[g] = target_start[g] + frac * (target_end[g] - target_start[g])
            ramp_day += 1
        else:
            for g in GAS_KEYS:
                target[g] = anchors.log_mu[NORMAL][g]
        # 烃类:Cholesky 着色噪声(注入相关性)
        z = rng.standard_normal(len(HYDROCARBONS))
        colored = L @ z
        for j, g in enumerate(HYDROCARBONS):
            sig = anchors.log_sigma[state][g]
            drift = theta * (target[g] - log_val[g])
            log_val[g] = min(log_val[g] + drift + sig * noise_scale * colored[j],
                             anchors.log_cap[g])
        # CO/CO₂:独立 OU,但目标随状态爬升(与烃类同日程);噪声略收、上限夹死
        for g in OXIDES:
            sig = anchors.log_sigma[state][g]
            drift = theta * (target[g] - log_val[g])
            noise = sig * noise_scale * OXIDE_NOISE_SCALE * rng.standard_normal()
            log_val[g] = min(log_val[g] + drift + noise, anchors.log_cap[g])

        row = {
            "transformer_id": cfg.transformer_id,
            "date": cur_date.isoformat(),
            "fault_state": state,
        }
        for g in GAS_KEYS:
            row[g] = round(max(0.0, 10 ** log_val[g] - 1.0), 3)
        rows.append(row)

    # 列序:元信息 + 7 种特征气体
    cols = ["transformer_id", "date"] + GAS_KEYS + ["fault_state"]
    return pd.DataFrame(rows)[cols]

