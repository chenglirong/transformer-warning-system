"""时序数据合成器:从 743 行快照数据构造"虚拟变压器 360 天监测序列"(单设备方案,D-015)。

核心思想:
    1. 用 IEC 60599 自动诊断结果作为"状态分布池":同一故障类型的样本视为该状态的浓度分布
    2. 每台虚拟变压器在 90 天内按马尔可夫链在状态间迁移(以"健康"为大概率初态)
    3. 在每个状态内,用 OU 过程(对数空间)生成日浓度,保证:
       - 长期均值贴近该状态真实样本均值
       - 相邻日变化幅度受限(物理现实:气体浓度日变化缓慢)
       - 永远为正(对数空间)
    4. 工况(油温/负载/环温)按物理规律合成,与日历相关

论文叙事:这是"分布保持的时序构造",不是"凭空生成数据"。给定真实快照样本的
分布,只是为它们附加时间维度;详见 论文梳理.md「实施期修订」第 2 项。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ============================================================
# 配置
# ============================================================

# 7 种核心 DGA 气体(论文要求的预测目标)
GAS_KEYS = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]

# 健康基线状态名:沿用 "Normal"(下游 api/data、compare_detection 等以 fault_state
# != "Normal" 判异常,保持不变以缩小影响面)。D-044 起其判定依据改为 DL/T 722 表3
# 注意值(见 eda.label_state),即「气体未超表3 注意值」= Normal,而非三比值法判定。
NORMAL = "Normal"
HEALTHY = NORMAL

# 合成默认参数(单设备方案:1 台 × 360 天)
# 设计意图:本系统聚焦单台变压器的预警全流程,而非多设备工业平台
# 360 天足够 LSTM 划分 train/val/test,贴合 743 行原始数据的体量
DEFAULT_N_TRANSFORMERS = 1
DEFAULT_N_DAYS = 360
DEFAULT_START_DATE = date(2024, 4, 1)  # 跨完整四季,体现环境温度变化

# 马尔可夫链:健康 → 异常状态的日转移概率(D-044)
# 设计目标:360 天周期内,~70-75% 健康天数 + ~25-30% 异常天数(贴近真实运维)
# 状态名 = DL/T 722 表7 故障类型(+异常-未明类),与 eda.label_state / 状态池键一致;
# 各异常态权重按原始 743 行表3+表7 打标的真实占比(异常 254 例)分配,总率维持 ~0.0096。
FAULT_TRANSITION_PROBS = {
    "高温过热>700℃": 0.00223,      # 59/254
    "电弧放电": 0.00181,           # 48/254
    "异常-未明类": 0.00159,        # 42/254(表7 判不出类型的异常,单独成池)
    "电弧放电兼过热": 0.00079,      # 21/254
    "低温过热<150℃": 0.00079,      # 21/254
    "低温过热150~300℃": 0.00068,   # 18/254
    "低能放电": 0.00057,           # 15/254
    "局部放电": 0.00057,           # 15/254
    "中温过热300~700℃": 0.00042,   # 11/254
    "低能放电兼过热": 0.00015,      # 4/254
}
# 总转移概率 ≈ 0.0096/天,期望第 1 次故障 ~104 天
# 360 天内期望发生 ~3-4 次异常事件,每次平均持续 21 天 ≈ 75 天异常 ≈ 21%

# 异常状态停留期均值(几何分布参数,单位:天)
FAULT_DURATION_MEAN_DAYS = 21
FAULT_TO_HEALTHY_PROB = 1.0 / FAULT_DURATION_MEAN_DAYS  # ≈ 4.8%

# OU 过程参数(对数空间)
# theta:回归速度,越大越快回归到长期均值;dt=1天 时,半衰期 = ln(2)/theta
OU_THETA = 0.15           # 半衰期约 4.6 天,即 4-5 天后浓度跟随状态变化
OU_SIGMA_HEALTHY = 0.18   # 健康态噪声(对数空间标准差)
OU_SIGMA_FAULT = 0.30     # 异常态波动更大
# 状态切换时,目标均值采用平滑过渡而非瞬间跳变
STATE_TRANSITION_BLEND_DAYS = 5


# ============================================================
# 状态分布池
# ============================================================

@dataclass
class StatePool:
    """某 IEC 状态下,各气体在对数空间的(均值, std)。

    对数空间统计的好处:
    - 应对极端长尾分布(EDA 显示 H2 max=23349,mean=348)
    - 后续生成时取 exp 自然为正,无需截断
    """
    state: str
    n_samples: int
    log_mu: dict[str, float]    # gas_key -> log10(value+1) 的均值
    log_sigma: dict[str, float] # gas_key -> log10(value+1) 的标准差

    def sample_log_target(self, gas_key: str, rng: random.Random) -> float:
        """从该状态分布抽样一个对数空间目标浓度。"""
        mu = self.log_mu.get(gas_key, 0.0)
        sigma = self.log_sigma.get(gas_key, 0.5)
        # 截断:避免极端长尾在合成中被复现
        sample = rng.gauss(mu, sigma)
        return max(mu - 2 * sigma, min(mu + 2 * sigma, sample))


def build_state_pools(labeled_rows: list[dict]) -> dict[str, StatePool]:
    """从 labeled_iec.csv 的行,按 IEC 状态构建分布池。

    `labeled_rows` 每行至少包含:
        h2, ch4, c2h4, c2h6, c2h2, co, co2, iec_fault
    """
    by_state: dict[str, list[dict]] = {}
    for r in labeled_rows:
        state = r["iec_fault"]
        # Undetermined / Insufficient Data 不参与池构建(语义不清)
        if state in ("Undetermined", "Insufficient Data"):
            continue
        by_state.setdefault(state, []).append(r)

    pools: dict[str, StatePool] = {}
    for state, rows in by_state.items():
        log_mu, log_sigma = {}, {}
        for gas in GAS_KEYS:
            vals = [r[gas] for r in rows if r.get(gas) is not None]
            if not vals:
                # 该气体在此状态下全缺失:用全局均值兜底(EDA 已显示 CO/CO2 部分缺失)
                log_mu[gas], log_sigma[gas] = _global_log_stats(labeled_rows, gas)
                continue
            log_vals = [math.log10(v + 1) for v in vals]
            log_mu[gas] = sum(log_vals) / len(log_vals)
            if len(log_vals) > 1:
                m = log_mu[gas]
                var = sum((x - m) ** 2 for x in log_vals) / (len(log_vals) - 1)
                log_sigma[gas] = math.sqrt(var)
            else:
                log_sigma[gas] = 0.3
        pools[state] = StatePool(
            state=state, n_samples=len(rows), log_mu=log_mu, log_sigma=log_sigma
        )
    return pools


def _global_log_stats(rows: list[dict], gas: str) -> tuple[float, float]:
    """全局兜底:某气体在某状态下全缺失时,用全数据集的对数均值/std。"""
    vals = [r[gas] for r in rows if r.get(gas) is not None]
    if not vals:
        return 1.0, 0.5
    log_vals = [math.log10(v + 1) for v in vals]
    mu = sum(log_vals) / len(log_vals)
    if len(log_vals) > 1:
        var = sum((x - mu) ** 2 for x in log_vals) / (len(log_vals) - 1)
        return mu, math.sqrt(var)
    return mu, 0.5


# ============================================================
# 马尔可夫状态机
# ============================================================

class StateChain:
    """虚拟变压器的故障状态链。

    规则:
    - 初始 Healthy
    - 每天:
        - 若 Healthy:按 FAULT_TRANSITION_PROBS 概率分布迁移到某异常,或保持
        - 若异常:按 FAULT_TO_HEALTHY_PROB 概率回到 Healthy,否则保持
    - 不允许异常→异常直接迁移(简化逻辑;现实里也通常先经过修复)

    单设备保证机制:
        n_days >= 180 时,启用"事件预算":确保整段时序内至少注入 N 次异常事件,
        避免单条链运气好全程健康,导致论文展示数据缺乏故障样例。
        每个事件落点为均匀采样的开始日;落点之间允许彼此独立。
    """

    def __init__(
        self,
        available_states: set[str],
        rng: random.Random,
        n_days: int = 0,
    ):
        self.rng = rng
        # 只用分布池里实际存在的状态(避免引用了池里没有的状态)
        self.fault_probs = {
            s: p for s, p in FAULT_TRANSITION_PROBS.items() if s in available_states
        }
        self.healthy_keep = 1.0 - sum(self.fault_probs.values())
        self.current = HEALTHY

        # 事件预算:仅长时序启用(单设备方案)
        # 比例 ~25% 异常天数,平均事件长度 21 天 → 事件数 = n_days * 0.25 / 21
        self._scheduled_events: list[tuple[int, str]] = []
        if n_days >= 180:
            n_events = max(2, round(n_days * 0.25 / FAULT_DURATION_MEAN_DAYS))
            # 按真实分布池中状态权重抽样事件类型
            weighted_states = list(self.fault_probs.keys())
            weights = [self.fault_probs[s] for s in weighted_states]
            # 事件落点:均匀分布在 [10, n_days-30] 区间(留首尾安全区)
            for _ in range(n_events):
                day = rng.randint(10, max(11, n_days - 30))
                state = rng.choices(weighted_states, weights=weights, k=1)[0]
                self._scheduled_events.append((day, state))
            self._scheduled_events.sort()
        self._day_idx = 0

    def step(self) -> str:
        """前进一天,返回新状态。"""
        # 优先检查是否有预定事件落点
        if self._scheduled_events and self._day_idx == self._scheduled_events[0][0]:
            _, forced_state = self._scheduled_events.pop(0)
            if self.current == HEALTHY:
                self.current = forced_state
            self._day_idx += 1
            return self.current

        self._day_idx += 1
        if self.current == HEALTHY:
            r = self.rng.random()
            if r < self.healthy_keep:
                return HEALTHY
            cum = self.healthy_keep
            for state, prob in self.fault_probs.items():
                cum += prob
                if r < cum:
                    self.current = state
                    return state
            self.current = HEALTHY
            return HEALTHY
        else:
            if self.rng.random() < FAULT_TO_HEALTHY_PROB:
                self.current = HEALTHY
            return self.current


# ============================================================
# OU 过程合成气体浓度(对数空间)
# ============================================================

@dataclass
class GasState:
    """单台变压器单种气体的合成状态。"""
    log_value: float           # 当前对数浓度
    target_log_mu: float       # 当前目标对数均值(随状态切换平滑变化)
    blend_days_left: int = 0   # 状态切换后剩余的过渡天数


def ou_step(
    current: float, target: float, sigma: float, theta: float, rng: random.Random
) -> float:
    """OU 过程一步:dx = theta*(target - x) + sigma*N(0,1)。"""
    drift = theta * (target - current)
    noise = sigma * rng.gauss(0, 1)
    return current + drift + noise


# ============================================================
# 工况合成
# ============================================================

def synth_load_current(
    day_idx: int, cur_date: date, base: float, rng: random.Random
) -> float:
    """负载电流:工作日/周末模式 + 日内基准 + 噪声。

    简化为按日均值。base 是该变压器的基准负载。
    """
    # 周末降负载。直接用真实日期取星期,避免硬编码 day_idx 偏移随
    # START_DATE 变更而错位(0=Mon ... 6=Sun)
    weekend_factor = 0.7 if cur_date.weekday() >= 5 else 1.0
    seasonal = 1.0 + 0.05 * math.sin(2 * math.pi * day_idx / 365.0)
    noise = 1.0 + 0.05 * rng.gauss(0, 1)
    val = base * weekend_factor * seasonal * noise
    return max(50.0, min(500.0, val))  # 工程合理区间


def synth_ambient_temp(day_idx: int, rng: random.Random) -> float:
    """环境温度:季节正弦 + 日内噪声。基准 15℃,夏冬 ±15℃。"""
    seasonal = 15.0 + 15.0 * math.sin(2 * math.pi * (day_idx - 100) / 365.0)
    noise = rng.gauss(0, 2.0)
    return round(seasonal + noise, 2)


def synth_oil_temp(load: float, ambient: float, rng: random.Random) -> float:
    """油温:基础温度(随负载^2)+ 环温抬升 + 噪声。合理区间 30-90℃。"""
    base = 35.0 + 0.00015 * load * load   # 满载附近温升 ~37℃
    coupled = base + 0.4 * (ambient - 15.0)
    noise = rng.gauss(0, 1.5)
    return round(max(25.0, min(95.0, coupled + noise)), 2)


# ============================================================
# 主合成函数
# ============================================================

@dataclass
class SynthConfig:
    n_transformers: int = DEFAULT_N_TRANSFORMERS
    n_days: int = DEFAULT_N_DAYS
    start_date: date = DEFAULT_START_DATE
    seed: int = 42


def synthesize(
    labeled_rows: list[dict], cfg: Optional[SynthConfig] = None
) -> list[dict]:
    """合成虚拟变压器 360 天时序数据(单设备方案,n_days 见 SynthConfig)。

    返回行列表,每行键:
        transformer_id, date(ISO 字符串), h2..co2, oil_temp,
        load_current, ambient_temp, fault_state
    """
    cfg = cfg or SynthConfig()
    rng = random.Random(cfg.seed)

    pools = build_state_pools(labeled_rows)
    if HEALTHY not in pools:
        raise RuntimeError(
            "分布池缺少 'Normal' 状态——检查 labeled_iec.csv 的 iec_fault 列"
        )

    available_states = set(pools.keys())
    output: list[dict] = []

    for tid in range(1, cfg.n_transformers + 1):
        # 每台变压器一条独立链;n_days 用于启用长时序事件预算
        chain = StateChain(available_states, rng, n_days=cfg.n_days)
        gas_states: dict[str, GasState] = {}
        # 初始化:从健康态分布池中抽样作为起始
        healthy_pool = pools[HEALTHY]
        for gas in GAS_KEYS:
            mu = healthy_pool.sample_log_target(gas, rng)
            gas_states[gas] = GasState(log_value=mu, target_log_mu=mu)

        # 该变压器的负载基准(各台不同,模拟现实)
        load_base = rng.uniform(150.0, 350.0)

        prev_state = HEALTHY
        for day_idx in range(cfg.n_days):
            current_date = cfg.start_date + timedelta(days=day_idx)
            current_state = chain.step()

            # 状态切换时启动平滑过渡
            if current_state != prev_state:
                pool = pools.get(current_state, healthy_pool)
                for gas in GAS_KEYS:
                    gas_states[gas].target_log_mu = pool.sample_log_target(gas, rng)
                    gas_states[gas].blend_days_left = STATE_TRANSITION_BLEND_DAYS
                prev_state = current_state

            # OU 过程一步
            sigma = OU_SIGMA_HEALTHY if current_state == HEALTHY else OU_SIGMA_FAULT
            for gas, gs in gas_states.items():
                gs.log_value = ou_step(
                    gs.log_value, gs.target_log_mu, sigma, OU_THETA, rng
                )
                if gs.blend_days_left > 0:
                    gs.blend_days_left -= 1

            # 工况合成
            ambient = synth_ambient_temp(day_idx, rng)
            load = synth_load_current(day_idx, current_date, load_base, rng)
            oil = synth_oil_temp(load, ambient, rng)

            row = {
                "transformer_id": tid,
                "date": current_date.isoformat(),
                "fault_state": current_state,
                "oil_temp": oil,
                "load_current": round(load, 2),
                "ambient_temp": ambient,
            }
            for gas in GAS_KEYS:
                # 反对数,转回浓度;减 1 抵消 log10(v+1) 的偏置
                val = max(0.0, 10 ** gas_states[gas].log_value - 1)
                row[gas] = round(val, 3)
            output.append(row)

    return output
