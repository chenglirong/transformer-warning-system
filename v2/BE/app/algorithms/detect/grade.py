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
        每日一 dict:date, grade, total_hydrocarbon, triggers(命中判据列表),
        urgency(注意值2+ 时的产气速率处置研判,否则 None)。
    """
    df = df.reset_index(drop=True)
    total_hc = df[HYDROCARBONS].sum(axis=1)
    thc_seq = total_hc.tolist()
    # 各判据量的完整序列(供参比窗口取值)
    seq = {"c2h2": df["c2h2"].astype(float).tolist(),
           "h2": df["h2"].astype(float).tolist(),
           "total_hydrocarbon": thc_seq}

    results: list[dict] = []
    for i in range(len(df)):
        row = df.iloc[i]
        c2h2, h2, thc = float(row["c2h2"]), float(row["h2"]), float(total_hc.iloc[i])
        metrics = {"c2h2": c2h2, "h2": h2, "total_hydrocarbon": thc}

        triggers: list[dict] = []

        # ① 绝对浓度(当日实测值)
        for gas, bounds in ABS_CONCENTRATION.items():
            g = _grade_by_thresholds(metrics[gas], bounds)
            if g != NORMAL:
                triggers.append({"gas": gas, "basis": "绝对浓度", "grade": g,
                                 "value": round(metrics[gas], 2)})

        # ② 绝对增量 ③ 相对增长速率:当前值 − 参比值(A.3.3 参比=前14~前7天窗口均值)
        # 窗口 = [i-14, i-7)。不足前14天(序列开头)则跳过增量/增长率判据。
        lo, hi = i - BASELINE_WINDOW_START, i - BASELINE_WINDOW_END
        if lo >= 0:
            base_metrics = {k: _baseline(seq[k][lo:hi]) for k in seq}
            base_thc = base_metrics["total_hydrocarbon"]
            for gas, bounds in ABS_INCREMENT.items():
                inc = metrics[gas] - base_metrics[gas]  # γₐ = 当前值 − 参比值(A.1)
                g = _grade_by_thresholds(inc, bounds)
                # C₂H₂「从无到有」:参比≈0 且现值≥1 → 注意值1
                if gas == "c2h2" and base_metrics[gas] < 1.0 and metrics[gas] >= 1.0:
                    g = _max_grade(g, ATTENTION_1)
                if g != NORMAL:
                    triggers.append({"gas": gas, "basis": "绝对增量", "grade": g,
                                     "value": round(inc, 2)})
            # ③ 相对增长速率(仅总烃,参比≥30 才算;γᵣ=(当前−参比)/参比×100%,A.2)
            if base_thc >= REL_GROWTH_MIN_BASE:
                rate = (thc - base_thc) / base_thc * 100.0
                g = _grade_by_thresholds(rate, REL_GROWTH["total_hydrocarbon"])
                if g != NORMAL:
                    triggers.append({"gas": "total_hydrocarbon", "basis": "相对增长速率",
                                     "grade": g, "value": round(rate, 1)})

        # 最终档 = 所有命中判据的最高档(无命中即正常)。落档只认表A.3(1498.2 %/周),
        # 722 相对速率不参与落档(D-004)。
        grade = _max_grade(NORMAL, *[t["grade"] for t in triggers]) if triggers else NORMAL

        # DL/T 722 §9.3.2 相对产气速率(月环比,%/月);供②处置研判 + ④「预」。
        thc_rel_rate = _rel_rate_monthly(thc_seq, i)
        conc_over = any(t["basis"] == "绝对浓度" for t in triggers)

        results.append({
            "date": row["date"] if isinstance(row["date"], str) else row["date"].isoformat(),
            "grade": grade,
            "total_hydrocarbon": round(thc, 2),
            "triggers": triggers,
            "thc_rel_rate": None if thc_rel_rate is None else round(thc_rel_rate, 1),
            "_conc_over": conc_over,
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
        # ④「预」= 浓度未超注意值,但相对速率连续超 10%/月(§9.3.3 a)→ 缩周期
        r["is_pre"] = rising and not r.pop("_conc_over")
        r["urgency"] = _assess_urgency(r["grade"], r["thc_rel_rate"], rising)
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


def _assess_urgency(grade: str, thc_rel_rate: float | None, rising: bool) -> dict | None:
    """处置紧急度研判(§9.3.3),仅注意值2及以上启动;不改档位。

    用 **DL/T 722 §9.3.2 相对产气速率(%/月)** 判涨势急不急(§9.3.3 a「结合
    产气速率进行判断」——配套的是 722 §9.3.2 那套速率,不是表A.3 %/周)。落档
    已由表A.3 定死(1498.2),本函数不改档位,只出处置紧急度。`rising` 由调用方
    传入(相对速率连续 N 天超注意值才为真,滤噪)。

    - 涨势确认(连续超 10%/月)→ 「涨势快,建议缩短检测周期」(急)
    - 超注意值但涨势未确认 → 「超标但暂稳,加强监视」(不急,§9.3.3 a 可继续运行)
    """
    if GRADES.index(grade) < GRADES.index(URGENCY_TRIGGER_GRADE):
        return None

    if rising:
        level = "高"
        rate_txt = f"{thc_rel_rate:.0f}%/月" if thc_rel_rate is not None else "—"
        advice = f"总烃相对产气速率 {rate_txt} 连续超注意值(10%/月),涨势快,建议缩短检测周期"
    else:
        level = "中"
        advice = "超注意值但相对产气速率涨势平稳(未连续超注意值),加强监视"
    return {"level": level, "advice": advice, "rising": bool(rising)}
