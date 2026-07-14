"""表A.3 四档分级 + 产气速率处置研判(检测模块第①步)。

纯算法层:输入 DataFrame(日期升序,含 h2/ch4/c2h4/c2h6/c2h2 列),
输出每日检测结果 list[dict]。不碰 DB/HTTP。

档位是**事实陈述**(表A.3 三组判据取最高档,四档全报,正常也报);§9.3.3
应用原则只调「处置紧急度」不改档位。产气速率研判仅注意值2及以上启动。
"""
from __future__ import annotations

import pandas as pd

from app.algorithms.detect.thresholds import (
    ABS_CONCENTRATION,
    ABS_INCREMENT,
    ATTENTION_1,
    BASELINE_OUTLIER_K,
    BASELINE_WINDOW_END,
    BASELINE_WINDOW_START,
    GRADES,
    NORMAL,
    REL_GROWTH,
    REL_GROWTH_MIN_BASE,
    REL_RATE_CONSECUTIVE_DAYS,
    REL_RATE_LOOKBACK_DAYS,
    THC_REL_RATE_ATTENTION,
    THC_REL_RATE_MIN_BASE,
    URGENCY_TRIGGER_GRADE,
)

HYDROCARBONS = ["ch4", "c2h4", "c2h6", "c2h2"]  # 总烃 = 四烃类之和


def _grade_by_thresholds(value: float, bounds: list[float | None]) -> str:
    """给定值与 [注意1,注意2,告警] 下限,返回所在档(达下限即升档)。"""
    grade = NORMAL
    for i, lo in enumerate(bounds):
        if lo is not None and value >= lo:
            grade = GRADES[i + 1]
    return grade


def _max_grade(*grades: str) -> str:
    """取最高档(任一判据升档即升)。"""
    return max(grades, key=GRADES.index)


def _baseline(vals: list[float]) -> float | None:
    """参比值(DL/T 1498.2-2025 A.3.3 a):窗口内算术平均,先剔奇异值。

    `vals` = 前14天~前7天窗口内的测量值。剔除超出 [μ±kσ] 的奇异值后再平均。
    窗口不足(序列开头)时返回 None,该日不算增量/增长率判据。
    """
    if not vals:
        return None
    arr = pd.Series(vals, dtype=float)
    mu, sigma = arr.mean(), arr.std()
    if sigma > 0:
        kept = arr[(arr - mu).abs() <= BASELINE_OUTLIER_K * sigma]
        if len(kept):
            arr = kept
    return float(arr.mean())


def detect(df: pd.DataFrame) -> list[dict]:
    """对整段时序逐日分级 + 研判。

    Args:
        df: 日期升序,含 date + 5 主烃类列。

    Returns:
        每日一 dict:
          date, grade(综合最高档), total_hydrocarbon,
          indicators(表A.3 全部指标,含正常),
          triggers(indicators 中非正常子集,兼容旧调用),
          urgency / is_pre / thc_rel_rate(§9.3.2 处置与「预」)。
    """
    df = df.reset_index(drop=True)
    total_hc = df[HYDROCARBONS].sum(axis=1)
    thc_seq = total_hc.tolist()
    # 各判据量的完整序列(供参比窗口取值)
    seq = {"c2h2": df["c2h2"].astype(float).tolist(),
           "h2": df["h2"].astype(float).tolist(),
           "total_hydrocarbon": thc_seq}

    gas_label = {
        "c2h2": "乙炔",
        "h2": "氢气",
        "total_hydrocarbon": "总烃",
    }

    results: list[dict] = []
    for i in range(len(df)):
        row = df.iloc[i]
        c2h2, h2, thc = float(row["c2h2"]), float(row["h2"]), float(total_hc.iloc[i])
        metrics = {"c2h2": c2h2, "h2": h2, "total_hydrocarbon": thc}

        indicators: list[dict] = []

        # ① 绝对浓度(当日实测值)——三项全报,含正常
        for gas, bounds in ABS_CONCENTRATION.items():
            g = _grade_by_thresholds(metrics[gas], bounds)
            indicators.append({
                "basis": "绝对浓度",
                "gas": gas,
                "item": f"{gas_label[gas]}值",
                "unit": "μL/L",
                "value": round(metrics[gas], 2),
                "grade": g,
                "note": None,
            })

        # ② 绝对增量 ③ 相对增长速率:当前值 − 参比值(A.3.3)
        lo, hi = i - BASELINE_WINDOW_START, i - BASELINE_WINDOW_END
        if lo >= 0:
            base_metrics = {k: _baseline(seq[k][lo:hi]) for k in seq}
            base_thc = base_metrics["total_hydrocarbon"]
            for gas, bounds in ABS_INCREMENT.items():
                base = base_metrics[gas]
                inc = metrics[gas] - base  # γₐ = 当前值 − 参比值(A.1)
                g = _grade_by_thresholds(inc, bounds)
                note = None
                # C₂H₂「从无到有」:参比≈0 且现值≥1 → 注意值1
                if gas == "c2h2" and base < 1.0 and metrics[gas] >= 1.0:
                    g = _max_grade(g, ATTENTION_1)
                    if g == ATTENTION_1 and _grade_by_thresholds(inc, bounds) == NORMAL:
                        note = "从无到有"
                indicators.append({
                    "basis": "绝对增量",
                    "gas": gas,
                    "item": gas_label[gas],
                    "unit": "μL/L·周",
                    "value": round(inc, 2),
                    "grade": g,
                    "baseline": round(base, 2),
                    "note": note,
                })
            # ③ 相对增长速率(仅总烃)
            if base_thc is None or base_thc < REL_GROWTH_MIN_BASE:
                indicators.append({
                    "basis": "相对增长速率",
                    "gas": "total_hydrocarbon",
                    "item": "总烃",
                    "unit": "%/周",
                    "value": None,
                    "grade": NORMAL,
                    "note": "总烃参比 <30 μL/L，不计算相对增长速率",
                })
            else:
                rate = (thc - base_thc) / base_thc * 100.0
                g = _grade_by_thresholds(rate, REL_GROWTH["total_hydrocarbon"])
                indicators.append({
                    "basis": "相对增长速率",
                    "gas": "total_hydrocarbon",
                    "item": "总烃",
                    "unit": "%/周",
                    "value": round(rate, 1),
                    "grade": g,
                    "baseline": round(base_thc, 2),
                    "note": None,
                })
        else:
            # 序列开头不足参比窗:增量/增长率仍报「正常」并注明未计算
            for gas in ABS_INCREMENT:
                indicators.append({
                    "basis": "绝对增量",
                    "gas": gas,
                    "item": gas_label[gas],
                    "unit": "μL/L·周",
                    "value": None,
                    "grade": NORMAL,
                    "note": "参比窗不足（前14天），暂不计算",
                })
            indicators.append({
                "basis": "相对增长速率",
                "gas": "total_hydrocarbon",
                "item": "总烃",
                "unit": "%/周",
                "value": None,
                "grade": NORMAL,
                "note": "参比窗不足（前14天），暂不计算",
            })

        # 综合档 = 全部指标最高档(含正常则仍为正常)
        grade = _max_grade(*[ind["grade"] for ind in indicators])
        # 兼容旧字段:仅非正常项
        triggers = [
            {"gas": ind["gas"], "basis": ind["basis"], "grade": ind["grade"],
             "value": ind["value"]}
            for ind in indicators if ind["grade"] != NORMAL and ind["value"] is not None
        ]

        # DL/T 722 §9.3.2 相对产气速率(月环比,%/月);供②处置研判 + ④「预」。
        thc_rel_rate = _rel_rate_monthly(thc_seq, i)

        results.append({
            "date": row["date"] if isinstance(row["date"], str) else row["date"].isoformat(),
            "grade": grade,
            "total_hydrocarbon": round(thc, 2),
            "indicators": indicators,
            "triggers": triggers,
            "thc_rel_rate": None if thc_rel_rate is None else round(thc_rel_rate, 1),
            "_rate_over": (thc_rel_rate is not None and thc >= THC_REL_RATE_MIN_BASE
                           and thc_rel_rate >= THC_REL_RATE_ATTENTION),
        })

    # 第二遍:连续确认 + 落 is_pre / urgency。相对速率须**连续 N 天**都超注意值才
    # 认定涨势(§9.3.2 连续判据),滤掉健康段孤立随机超标。
    _confirm_rate_over = [
        all(results[k]["_rate_over"] for k in range(i - REL_RATE_CONSECUTIVE_DAYS + 1, i + 1))
        if i >= REL_RATE_CONSECUTIVE_DAYS - 1 else False
        for i in range(len(results))
    ]
    for i, r in enumerate(results):
        rising = _confirm_rate_over[i]
        # rate_rising:722 相对速率连续超注意(供判型 OR 门槛 + 「预」/研判共用)
        r["rate_rising"] = rising
        # ④「预」= 档位仅正常/注意值1,但相对速率连续超 10%/月(§9.3.3 a)→ 缩周期 + 可进判型
        r["is_pre"] = rising and r["grade"] in (NORMAL, ATTENTION_1)
        r["urgency"] = _assess_urgency(
            r["grade"], r["thc_rel_rate"], rising, indicators=r.get("indicators"),
        )
        r.update(_scope_flags(r.get("indicators") or [], r["total_hydrocarbon"]))
        del r["_rate_over"]
    return results


def _rel_rate_monthly(thc_seq: list[float], i: int) -> float | None:
    """DL/T 722 §9.3.2 相对产气速率(总烃,%/月)。

    式2:γᵣ = (C₂ − C₁)/C₁ × 1/Δt × 100%。合成为逐日,取**月环比**(今 vs 30天前,
    Δt=1月)直接得 %/月,不做短窗折月放大(周环比×4.3 会把健康段日抖虚放成假超标)。
    前 30 天不足(序列开头)或参比≈0 返回 None。
    """
    j = i - REL_RATE_LOOKBACK_DAYS
    if j < 0:
        return None
    base = thc_seq[j]
    if base <= 0:
        return None
    return (thc_seq[i] - base) / base * 100.0  # Δt=1月,直接 %/月


def _assess_urgency(
    grade: str,
    thc_rel_rate: float | None,
    rising: bool,
    *,
    indicators: list[dict] | None = None,
) -> dict | None:
    """处置紧急度研判(§9.3.3),仅注意值2及以上启动;不改档位。

    - 涨势确认 → 急
    - 超注意值但暂稳 → 不急
    - §9.3.3 d 协调:仅 H₂ 顶档且涨势未确认 → 档位如实,紧急度降为「低」
    """
    if GRADES.index(grade) < GRADES.index(URGENCY_TRIGGER_GRADE):
        return None

    h2_only = _is_h2_only_attention(indicators or [])

    if rising:
        level = "高"
        rate_txt = f"{thc_rel_rate:.0f}%/月" if thc_rel_rate is not None else "—"
        advice = f"总烃相对产气速率 {rate_txt} 连续超注意值(10%/月),涨势快,建议缩短检测周期"
    elif h2_only:
        # 722 原文「也可判断为正常」;对接表A.3 时档位仍如实,只降紧急度
        level = "低"
        advice = (
            "仅 H₂ 超标且产气速率涨势未确认(§9.3.3 d 协调设计):档位如实,"
            "大概率非故障,加强监视"
        )
    else:
        level = "中"
        advice = "超注意值但相对产气速率涨势平稳(未连续超注意值),加强监视"

    return {
        "level": level,
        "advice": advice,
        "rising": bool(rising),
        "h2_only": h2_only,
    }


def _is_h2_only_attention(indicators: list[dict]) -> bool:
    """是否仅 H₂ 相关判据超标(浓度/增量)、总烃与乙炔均正常。"""
    abnormal = [i for i in indicators if i.get("grade") != NORMAL and i.get("value") is not None]
    if not abnormal:
        return False
    return all(i.get("item") == "氢气" or i.get("gas") == "h2" for i in abnormal)


def _scope_flags(indicators: list[dict], thc: float) -> dict:
    """表A.3 适用范围(A.2.3):乙炔≤10 / H₂≤150 / 总烃≤150。超出仍报最高档并标注。"""
    exceeded = []
    for ind in indicators:
        if ind.get("basis") != "绝对浓度" or ind.get("value") is None:
            continue
        gas = ind.get("gas")
        val = float(ind["value"])
        if gas == "c2h2" and val > 10:
            exceeded.append(f"乙炔 {val:.1f}>10")
        elif gas == "h2" and val > 150:
            exceeded.append(f"氢气 {val:.1f}>150")
    if thc > 150:
        exceeded.append(f"总烃 {thc:.1f}>150")
    tip = None
    if any(i.get("grade") != NORMAL for i in indicators):
        tip = (
            "注意核查非故障气体来源(有载调压油污染、不锈钢催化、近期大修等),"
            "参 DL/T 722 §4.3 / §9.3.3 e"
        )
    return {
        "scope_exceeded": bool(exceeded),
        "scope_note": ("已超表A.3 标定适用范围:" + "、".join(exceeded)) if exceeded else None,
        "non_fault_source_tip": tip,
    }
