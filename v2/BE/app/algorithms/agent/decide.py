"""Agent 监测决策 —— 规则决策表 + 可解释轨迹。

输入:档位/涨势预警/紧急度/交叉研判可信度;输出:周期/二次采样/试验 + trajectory。
依据用标准条目 id(前端 StdCite),why 用人话一句说清「为何这么做」。

§5.4.5 二次采样验证为装置级动作(由在线监测装置或运维人员执行),
本系统输出建议指令,不模拟自动采样流程。
"""
from __future__ import annotations

from typing import Any, Optional

# decide_c 输出档位（监测决策页 KPI / 筛选用）
PERIOD_KINDS: dict[str, str] = {
    "baseline": "按在线基线周期(≤12h)",
    "fast": "缩短至快速采样周期(下限≤2h)",
    "baseline_watch": "保持基线并加强监视(≤12h)",
    "approach_fast": "缩短采集周期并加强监视(建议逼近≤2h)",
}

RESAMPLE_KINDS: dict[str, str] = {
    "none": "不需要",
    "suggest": "建议二次采样验证",
    "defer": "暂不建议二次采样",
}


def classify_period_kind(period: str) -> str:
    for kind, text in PERIOD_KINDS.items():
        if period == text:
            return kind
    if period.startswith("缩短至快速"):
        return "fast"
    if "保持基线" in period:
        return "baseline_watch"
    if "逼近" in period or period.startswith("缩短采集"):
        return "approach_fast"
    return "baseline"


def classify_resample_kind(resample: str) -> str:
    for kind, text in RESAMPLE_KINDS.items():
        if resample == text:
            return kind
    if resample == "不需要":
        return "none"
    if "暂不建议" in resample:
        return "defer"
    if "建议" in resample:
        return "suggest"
    return "defer"


def decide_c(
    *,
    grade: str,
    is_pre: bool,
    urgency: Optional[dict],
    fusion: Optional[dict],
    rate_rising: bool = False,
) -> dict[str, Any]:
    """返回决策结果,含 rules_fired / trajectory(条件→动作→依据)。"""
    conf = (fusion or {}).get("confidence")
    measures = list((fusion or {}).get("measures") or [])
    cite_period = "1498-A.3.1"
    cite_resample = "1498-5.4.5"
    trajectory: list[dict[str, str]] = []

    def fire(condition: str, action: str, cite: str, field: str) -> None:
        trajectory.append({
            "condition": condition,
            "action": action,
            "cite": cite,
            "field": field,
        })

    # 正常基线 ≤12h;预警确认后快速周期,下限多组分 ≤2h
    if grade in ("正常", "注意值1") and not is_pre and not rate_rising:
        period = "按在线基线周期(≤12h)"
        period_why = "档位正常，维持基线采集周期即可"
        resample = "不需要"
        resample_why = "未达预警，无需二次采样验证"
        fire(
            "档位正常且速率未超注意值",
            period,
            cite_period,
            "period",
        )
        fire("未达预警触发条件", resample, cite_resample, "resample")
        log = f"采集周期 {period} · 二次采样：{resample}"
    elif is_pre or (grade == "注意值1" and rate_rising):
        period = "缩短至快速采样周期(下限≤2h)"
        period_why = "已触发提前预警或速率超注意值，宜缩至最小检测周期"
        cite_period = "1498-5.5.5"
        resample = "建议二次采样验证"
        resample_why = "建议由装置或运维执行二次采样验证，确认后缩短周期"
        cond = "触发涨势预警" if is_pre else "注意值1 且速率超注意值"
        fire(cond, period, cite_period, "period")
        fire(cond, resample, cite_resample, "resample")
        log = f"采集周期 {period} · 二次采样：{resample}"
    else:
        # 注意值2 / 告警值
        if urgency and urgency.get("level") == "低":
            period = "保持基线并加强监视(≤12h)"
            period_why = "紧急度低：仅 H₂ 超标且产气速率未超，档位如实，加强监视"
            cite_period = "722-9.3.3"
            fire(
                f"档位={grade} 且紧急度低",
                period,
                cite_period,
                "period",
            )
        elif urgency and urgency.get("rising"):
            period = "缩短至快速采样周期(下限≤2h)"
            period_why = "产气速率已确认上涨，缩短至最小检测周期加强监视"
            cite_period = "1498-5.5.5"
            fire(
                f"档位={grade} 且产气速率确认上涨",
                period,
                cite_period,
                "period",
            )
        else:
            period = "缩短采集周期并加强监视(建议逼近≤2h)"
            period_why = "已进入注意值2/告警，宜尽快逼近最小检测周期"
            cite_period = "1498-A.3.1"
            fire(
                f"档位={grade}",
                period,
                cite_period,
                "period",
            )

        if conf == "低":
            resample = "建议二次采样验证"
            resample_why = "判型可信度低（分歧或暂定），建议由装置或运维执行二次采样核实"
            fire(
                "判型可信度低（分歧/暂定）",
                resample,
                cite_resample,
                "resample",
            )
        else:
            resample = "暂不建议二次采样"
            resample_why = f"判型可信度{conf or '—'}，可先按当前结论调整监视"
            fire(
                f"判型可信度={conf or '—'}",
                resample,
                cite_resample,
                "resample",
            )

        trials_note = ""
        log = f"采集周期 {period} · 二次采样：{resample}"

    if measures:
        action = f"其他检查性试验 {len(measures)} 项"
        if not any(t.get("field") == "trials" for t in trajectory):
            fire(
                f"试验建议",
                action,
                "722-附录D",
                "trials",
            )
        trials_note = f" · 检查性试验 {len(measures)} 项"
        if trials_note not in log:
            log += trials_note

    measures_purpose = (fusion or {}).get("measures_purpose") or (
        "verify" if conf == "低" else "recommend"
    )

    return {
        "period": period,
        "period_why": period_why,
        # 兼容旧字段名
        "period_sub": period_why,
        "resample": resample,
        "resample_why": resample_why,
        "resample_sub": resample_why,
        "trials": measures,
        "trials_purpose": measures_purpose,
        "trials_basis": list((fusion or {}).get("measures_basis") or []),
        "trials_appendix_d": list((fusion or {}).get("measures_appendix_d") or []),
        "trials_1685_items": list((fusion or {}).get("measures_1685_items") or []),
        "trials_nature_label": (fusion or {}).get("measures_nature_label"),
        "cite_period": cite_period,
        "cite_resample": cite_resample,
        "log": log,
        "offline_note": "722 §5.3 表1 / §5.4 b(月/周/天)为离线例行对照,不写入在线主规则",
        "resample_note": "二次采样验证由在线监测装置或运维人员执行，本系统输出建议指令",
        "trajectory": trajectory,
        "rules_fired": [t["condition"] + " → " + t["action"] for t in trajectory],
    }
