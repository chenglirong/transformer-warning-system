"""Agent B —— 自然语言分析报告。

红线:LLM 只组织人话,不下判定、不发明档位/类型/试验/处置指令。
无密钥或调用失败 → 规则模板降级。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from app.algorithms.agent.llm_client import chat_completion, llm_enabled

_SYSTEM = """你是变压器油中溶解气体(DGA)分析报告写手。
硬规则:
1. 只能复述「事实包」里已给出的结论,禁止改判档位、故障类型、可信度、试验清单。
2. 禁止发明未给出的数值、国标条款或运维处置指令(如立即停电/检修)。
3. 输出一段中文「分析意见」,建议按【告警级别】【超标/趋势】【故障类型】【监测与试验建议】组织。
4. 语气专业克制;可说明合成数据局限,但不要编造铭牌/油温等字段。
5. 不要使用 Markdown 标题或项目符号列表,用连贯段落(可用【】分区标签)。"""


def build_facts_pack(
    *,
    grade: str,
    gases: dict,
    thc: float,
    triggers: list,
    is_pre: bool,
    thc_rel: Optional[float],
    urgency: Optional[dict],
    diagnosis: dict,
    fusion: Optional[dict],
    decision: dict,
    scope_note: Optional[str] = None,
    non_fault_tip: Optional[str] = None,
) -> dict[str, Any]:
    """确定性事实包——LLM 唯一允许写的信息来源。"""
    return {
        "grade": grade,
        "gases_uL_L": gases,
        "total_hydrocarbon": thc,
        "triggers": triggers[:8],
        "is_pre": is_pre,
        "thc_rel_rate_pct_per_month": thc_rel,
        "urgency": urgency,
        "diagnosis_triggered": bool(diagnosis.get("triggered")),
        "trigger_note": diagnosis.get("trigger_note") or diagnosis.get("reason"),
        "fault_primary": (fusion or {}).get("primary"),
        "fault_code": (fusion or {}).get("primary_code"),
        "confidence": (fusion or {}).get("confidence"),
        "confidence_reason": (fusion or {}).get("confidence_reason"),
        "provisional": bool((fusion or {}).get("provisional"))
        or (fusion or {}).get("confidence") == "低",
        "nature_label": (fusion or {}).get("nature_label"),
        "summary_rule": (fusion or {}).get("summary"),
        "reasoning": (fusion or {}).get("reasoning") or [],
        "measures": (fusion or {}).get("measures") or decision.get("trials") or [],
        "measures_purpose": (fusion or {}).get("measures_purpose")
        or ("verify" if (fusion or {}).get("confidence") == "低" else "recommend"),
        "measures_basis": (fusion or {}).get("measures_basis")
        or decision.get("trials_basis")
        or [],
        "period": decision.get("period"),
        "resample": decision.get("resample"),
        "scope_note": scope_note,
        "non_fault_source_tip": non_fault_tip,
        "boundary": "不下成因/部位;不给停电检修运维指令;只到监测动作+附录D试验(低可信度为核实非确诊)",
    }


def build_template_opinion(*, facts: dict[str, Any]) -> str:
    """规则模板(降级路径)。"""
    parts = [f"【告警级别】{facts['grade']}。"]
    triggers = facts.get("triggers") or []
    if triggers:
        hit_txt = "、".join(
            f"{_gas_zh(t.get('gas'))}({t.get('basis')})→{t.get('grade')}"
            for t in triggers[:6]
        )
        parts.append(f"超标判据：{hit_txt}。")
    else:
        parts.append("表 A.3 七项均在正常范围。")

    rate = facts.get("thc_rel_rate_pct_per_month")
    rate_txt = f"{rate}%/月" if rate is not None else "—"
    if facts.get("is_pre"):
        parts.append(f"【趋势】总烃月环比 {rate_txt} 连续超阈，触发「预」提前预警。")
    elif facts.get("urgency"):
        u = facts["urgency"]
        advice = (u.get("advice") or "").rstrip("。.;；")
        parts.append(
            f"【趋势】总烃月环比 {rate_txt}；处置紧急度 {u.get('level')}。"
            + (f"{advice}。" if advice else "")
        )
    else:
        parts.append(f"【趋势】总烃月环比 {rate_txt}。")

    if facts.get("diagnosis_triggered") and facts.get("fault_primary"):
        code = facts.get("fault_code") or ""
        provisional = facts.get("provisional") or facts.get("confidence") == "低"
        tag = "暂定故障类型" if provisional else "故障类型"
        parts.append(
            f"【{tag}】{facts['fault_primary']}"
            + (f"（{code}）" if code else "")
            + f"；可信度{facts.get('confidence')}（{facts.get('confidence_reason', '')}）"
            + ("；不作确诊。" if provisional else "。")
        )
    else:
        parts.append(f"【故障类型】{facts.get('trigger_note') or '未进入判型'}。")

    parts.append(
        f"【处置建议】采集周期：{facts.get('period')}；二次采样：{facts.get('resample')}。"
    )
    measures = facts.get("measures") or []
    if measures:
        purpose = facts.get("measures_purpose") or (
            "verify" if facts.get("provisional") else "recommend"
        )
        head = "核实试验" if purpose == "verify" else "进一步试验"
        basis = facts.get("measures_basis") or []
        if basis:
            parts.append(head + "：" + "；".join(b.get("text") for b in basis[:5] if b.get("text")) + "。")
        else:
            parts.append(f"{head}：" + "、".join(measures[:8]) + "。")
    if facts.get("scope_note"):
        parts.append(facts["scope_note"] + "。")
    if facts.get("non_fault_source_tip"):
        parts.append(facts["non_fault_source_tip"] + "。")
    parts.append("（本意见仅复述国标规则判定结果；合成环境无铭牌/油温等字段未编造。）")
    return "".join(parts)


def _gas_zh(gas: str | None) -> str:
    return {
        "c2h2": "乙炔",
        "h2": "氢气",
        "total_hydrocarbon": "总烃",
        "thc": "总烃",
        "ch4": "甲烷",
        "c2h4": "乙烯",
        "c2h6": "乙烷",
        "co": "CO",
        "co2": "CO₂",
    }.get((gas or "").lower(), gas or "—")



def _validate_opinion(text: str, facts: dict[str, Any]) -> Optional[str]:
    """粗校验:过短/缺档位 → 视为失败。"""
    t = (text or "").strip()
    if len(t) < 40:
        return "过短"
    if facts["grade"] not in t and "告警级别" not in t:
        # 允许同义复述缺字面档位时仍过——但两者都没有则拒
        return "未覆盖告警级别"
    banned = ("立即停电", "退出运行", "责令检修", "保证一定", "100%确诊")
    for b in banned:
        if b in t:
            return f"越界措辞:{b}"
    return None


def generate_opinion(
    *,
    facts: dict[str, Any],
    force_template: bool = False,
) -> dict[str, Any]:
    """生成分析意见。返回 {text, mode, error?}。"""
    template = build_template_opinion(facts=facts)
    if force_template or not llm_enabled():
        return {
            "text": template,
            "mode": "rule_template",
            "error": None if force_template or not llm_enabled() else None,
            "note": "未配置 LLM_API_KEY,使用规则模板" if not llm_enabled() and not force_template else None,
        }

    user = (
        "请根据下列 JSON 事实包撰写分析意见(只复述,不改判):\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )
    try:
        raw = chat_completion([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
        ])
        err = _validate_opinion(raw, facts)
        if err:
            return {
                "text": template,
                "mode": "rule_template",
                "error": f"LLM 未通过校验({err}),已降级",
            }
        return {"text": raw, "mode": "llm", "error": None}
    except Exception as e:  # noqa: BLE001
        return {
            "text": template,
            "mode": "rule_template",
            "error": f"LLM 失败已降级: {e}",
        }
