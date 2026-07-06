"""预警规则引擎(论文模块 5 核心 ⭐)。

输入「当前气体 + 工况 + ARIMA 未来 1-3 天预测」,按 rules.yaml 逐条匹配,
输出触发的规则列表 + 综合预警等级(四级取最高)。

职责(纯算法层,承 CLAUDE.md「算法层不依赖 DB/HTTP」):
    - 输入是 dict / DataFrame,输出是 dict,不碰请求上下文或数据库
    - 落库(warnings 表)由 API / 脚本层做,不在这里

三类规则(论文模块 5):
    hard  硬规则——当前已超国标注意值。复用 detect/threshold.detect_one 判定,
          不重复实现总烃口径
    soft  软规则——ARIMA 预测未来 1-3 天内超标(ARIMA 选型见 D-029:实测较
          LSTM 更稳健,故预警的预测依据用 ARIMA)。对预测每天同样用
          threshold.detect_one 判,找最早超标日定级(第 1 天=24h 内→red,
          第 2-3 天→orange)
    combo 组合规则——多指标关联:① 产气速率快 + 油温高(依赖预测);
          ② CO₂/CO<3 + 已有气体超注意值 → 关注固体绝缘(DL/T 722 §10.2.3.1,当前态)

另有 trend(趋势)规则:未到超标但涨势明显 → yellow。

🚧 系统边界(D-008):只输出 等级 / 哪些气体 / 规则编号 / 趋势,
    message 不含具体故障类型(诊断系统职责)。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

from app.algorithms.detect import threshold
from app.algorithms.detect.threshold import ATTENTION_VALUES

RULES_PATH = Path(__file__).resolve().parent / "rules.yaml"

# 等级排序(取最高级用),数字越大越紧急
LEVEL_ORDER: Dict[str, int] = {"blue": 1, "yellow": 2, "orange": 3, "red": 4}

# 产气速率/涨幅判据的适用门槛:总烃起始含量 ≥ 10 μL/L(国标 DL/T 722-2014
# §9.3.2 明文:「总烃起始含量很低(低于 10 μL/L)时,不宜用相对产气速率判断」)。
# 总烃过低时,任一气体的涨幅% 都会被极小分母放大成伪信号(如 C₂H₄ 0.86→18=+2106%),
# 故以总烃为总开关:总烃不达标的当日,所有气体涨幅一律不参与预警判定/不对外展示。
# 另:§10.2.1 规定比值法「一般在每组气体含量超过注意值后使用」,同源精神。
RATE_TOTAL_HC_MIN = 10.0


def _rate_applicable(total_hydrocarbon: float) -> bool:
    """当日产气速率/涨幅判据是否适用——总烃 ≥ 10 μL/L(§9.3.2)。

    低于此,国标明文「不宜用相对产气速率」,且低基数下涨幅% 失真。
    """
    return total_hydrocarbon >= RATE_TOTAL_HC_MIN

# 判定项 → 中文名(组合规则 message 的 {gas} 占位符用)
_ITEM_LABEL: Dict[str, str] = {
    "h2": "H₂", "ch4": "CH₄", "c2h4": "C₂H₄", "c2h6": "C₂H₆",
    "c2h2": "C₂H₂", "co": "CO", "co2": "CO₂",
    "total_hydrocarbon": "总烃",
}


def _fmt(x: float) -> float:
    """message 数值统一保留 1 位小数(避免 8.199999 这类浮点尾巴)。"""
    return round(float(x), 1)


def load_rules(path: Optional[Path] = None) -> dict:
    """加载 rules.yaml。"""
    p = path or RULES_PATH
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _item_value(detect_values: Dict[str, float], item: str) -> float:
    """从 threshold.detect_one 的 values 取某判定项实测值(含总烃合成项)。"""
    return detect_values.get(item, 0.0)


def _effective_thresholds(rules: dict) -> Dict[str, float]:
    """预警有效阈值 = 国标 ATTENTION_VALUES 叠加 rules.yaml 的 warning_thresholds 覆盖。

    国标值是通用注意值;rules.yaml 可选 warning_thresholds 节按设备历史校准覆盖。
    D-044 删 CO/CO₂ 绝对阈值后该节已空(CO/CO₂ 改走 §10.2.3.1 比值法,见 C-02),
    此处恒等于国标口径;保留 update 兜底以便将来按设备校准。不改检测模块的国标口径。
    """
    eff = dict(ATTENTION_VALUES)
    eff.update(rules.get("warning_thresholds", {}))
    return eff


def _exceeds(values: Dict[str, float], item: str, thresholds: Dict[str, float]) -> bool:
    """判定项是否超(预警有效)注意值。"""
    return _item_value(values, item) > thresholds[item]


def evaluate(
    current_gases: Dict[str, float],
    oil_temp: Optional[float] = None,
    forecast_df: Optional[pd.DataFrame] = None,
    rules: Optional[dict] = None,
) -> dict:
    """对单台变压器当前状态 + 预测做预警评估。

    Args:
        current_gases: 当前 7 气体 dict(h2/ch4/c2h4/c2h6/c2h2/co/co2)。
        oil_temp: 当前油温(组合规则用),可缺省。
        forecast_df: ARIMA 未来 N 天预测(arima.forecast_arima 输出,
                     行=天、列=7 气体);None 则跳过软规则/趋势/组合。
        rules: 规则字典;None 则从 rules.yaml 加载。

    Returns:
        dict:{
            "level": 综合等级(red/orange/yellow/blue)或 None(无触发),
            "triggered": [{rule_id, rule_type, level, message}, ...],
            "is_abnormal": bool,   # 是否有任何触发(对外二分类口径)
        }
    """
    if rules is None:
        rules = load_rules()

    thresholds = _effective_thresholds(rules)
    triggered: List[dict] = []

    # 当前值判定(复用 threshold,拿 values 含总烃)
    cur = threshold.detect_one(
        current_gases.get("h2"), current_gases.get("ch4"),
        current_gases.get("c2h4"), current_gases.get("c2h6"),
        current_gases.get("c2h2"), current_gases.get("co"),
        current_gases.get("co2"),
    )

    # ---------- 硬规则:当前已超标 ----------
    for r in rules.get("hard_rules", []):
        item = r["item"]
        if _exceeds(cur.values, item, thresholds):
            triggered.append({
                "rule_id": r["id"], "rule_type": "hard",
                "level": r["level"],
                "message": r["message"].format(
                    value=_fmt(_item_value(cur.values, item)),
                    limit=_fmt(thresholds[item]),
                ),
            })

    # ---------- 组合规则(当前态,不依赖预测):CO₂/CO 比值判固体绝缘 ----------
    # DL/T 722-2014 §10.2.3.1+§10.2.4:故障涉及固体绝缘时一般 CO₂/CO<3,
    # 且比值仅在「已疑似故障」(已有气体超注意值)时才有意义 → 联立判定。
    # 守边界 D-008:message 只提示关注固体绝缘,不输出故障类型。
    co = current_gases.get("co") or 0.0
    co2 = current_gases.get("co2") or 0.0
    for r in rules.get("combo_rules", []):
        if r.get("type") != "co2_co_ratio":
            continue
        c = r["conditions"]
        gas_exceeded = bool(cur.exceeded)         # 当前已有任一气体超注意值(§10.2.4 前提)
        ratio_ok = co > 0 and (co2 / co) < c["co2_co_ratio_max"]
        if (not c.get("require_gas_exceed", True) or gas_exceeded) and ratio_ok:
            triggered.append({
                "rule_id": r["id"], "rule_type": "combo",
                "level": r["level"],
                "message": r["message"].format(ratio=_fmt(co2 / co)),
            })

    # 预测相关规则需要 forecast_df
    if forecast_df is not None and len(forecast_df) > 0:
        # 每天的判定项值(复用 threshold,统一总烃口径)
        daily_values = [
            threshold.detect_one(
                row.get("h2"), row.get("ch4"), row.get("c2h4"),
                row.get("c2h6"), row.get("c2h2"), row.get("co"), row.get("co2"),
            ).values
            for row in forecast_df.to_dict("records")
        ]

        # ---------- 软规则:预测未来 N 天内超标 ----------
        for r in rules.get("soft_rules", []):
            item = r["item"]
            horizon = min(r.get("horizon_days", len(daily_values)), len(daily_values))
            first_day = None
            for d in range(horizon):
                if _exceeds(daily_values[d], item, thresholds):
                    first_day = d + 1        # 第几天(1-based)
                    break
            if first_day is not None:
                # 第 1 天(24h 内)超 → red;第 2-3 天 → orange
                level = "red" if first_day == 1 else "orange"
                pred_v = _item_value(daily_values[first_day - 1], item)
                triggered.append({
                    "rule_id": r["id"], "rule_type": "soft", "level": level,
                    "message": r["message"].format(
                        day=first_day,
                        pred=_fmt(pred_v),
                        limit=_fmt(thresholds[item]),
                    ),
                })

        # ---------- 趋势规则:涨幅明显但未超标 ----------
        last_values = daily_values[-1]
        # 产气速率判据适用前提:当日总烃 ≥ 10 μL/L(§9.3.2);否则涨幅%失真,整体不判
        rate_ok = _rate_applicable(_item_value(cur.values, "total_hydrocarbon"))
        for r in rules.get("trend_rules", []):
            item = r["item"]
            cur_v = _item_value(cur.values, item)
            fut_v = _item_value(last_values, item)
            # 已超标的交给硬/软规则,这里只管「未超标但涨势明显」
            if rate_ok and cur_v > 0 and not _exceeds(last_values, item, thresholds):
                rise = (fut_v - cur_v) / cur_v
                # 半开区间 [rise_ratio, rise_ratio_max):同一气体只命中其所在档
                # (blue 20~50% / yellow ≥50%),避免一个气体既报 blue 又报 yellow
                rise_max = r.get("rise_ratio_max")
                if rise >= r["rise_ratio"] and (rise_max is None or rise < rise_max):
                    triggered.append({
                        "rule_id": r["id"], "rule_type": "soft",
                        "level": r["level"],
                        "message": r["message"].format(
                            rise_pct=round(rise * 100),
                            cur=_fmt(cur_v), fut=_fmt(fut_v),
                        ),
                    })

        # ---------- 组合规则:产气速率快 + 油温高(依赖预测涨幅)----------
        # 带 type 的组合规则(如 co2_co_ratio)已在上方当前态处理,这里跳过。
        for r in rules.get("combo_rules", []):
            if r.get("type"):
                continue
            c = r["conditions"]
            # 任一关键判定项预测涨幅 ≥ 阈值,记下命中的气体名 + 涨幅(填 message)
            hit_item = None
            hit_rise = 0.0
            # CO 不在阈值法判定项内(D-044:cur.values 只含 h2/c2h2/总烃),故不遍历
            for item in ("c2h2", "total_hydrocarbon", "h2"):
                cur_v = _item_value(cur.values, item)
                fut_v = _item_value(last_values, item)
                # 同趋势规则:总烃达标(rate_ok)且当前值>0 才判涨幅(§9.3.2)
                if rate_ok and cur_v > 0 and (fut_v - cur_v) / cur_v >= c["gas_rise_ratio"]:
                    hit_item = item
                    hit_rise = (fut_v - cur_v) / cur_v
                    break
            temp_hit = oil_temp is not None and oil_temp >= c["oil_temp_min"]
            if hit_item is not None and temp_hit:
                triggered.append({
                    "rule_id": r["id"], "rule_type": "combo",
                    "level": r["level"],
                    "message": r["message"].format(
                        gas=_ITEM_LABEL.get(hit_item, hit_item),
                        rise_pct=round(hit_rise * 100),
                        oil_temp=_fmt(oil_temp),
                    ),
                })

    # ---------- 综合等级:取最高 ----------
    level = None
    if triggered:
        level = max((t["level"] for t in triggered), key=lambda lv: LEVEL_ORDER[lv])

    return {
        "level": level,
        "triggered": triggered,
        "is_abnormal": len(triggered) > 0,
    }
