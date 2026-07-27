"""Agent 运行日志 —— 从 steps 展开为终端流式 log_lines。

口径与 Agent 页运行日志一致;前端只负责渲染与流式动画。
"""
from __future__ import annotations

import re
from typing import Any

_GAS_LABEL = {
    "c2h2": "C₂H₂",
    "h2": "H₂",
    "ch4": "CH₄",
    "c2h4": "C₂H₄",
    "c2h6": "C₂H₆",
    "total_hydrocarbon": "总烃",
    "co": "CO",
    "co2": "CO₂",
}

_BASIS_SHORT = {
    "绝对浓度": "绝对浓度",
    "绝对增量": "绝对增量",
    "相对增长速率": "相对增速",
}


def build_log_lines(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将七步 steps 展开为扁平 log_lines 列表。"""
    out: list[dict[str, Any]] = []
    for step in steps:
        out.extend(_expand_step_logs(step))
    return out


def _log_result(msg: str | None) -> str:
    return re.sub(r"^(→|->)\s*", "", str(msg or "")).strip()


def _gas_symbol(ind: dict[str, Any]) -> str:
    gas = ind.get("gas")
    return _GAS_LABEL.get(gas, gas or "—")


def _grade_basis(ind: dict[str, Any]) -> str:
    basis = ind.get("basis") or ""
    return _BASIS_SHORT.get(basis, basis)


def _grade_tone(g: str | None) -> str:
    return {
        "正常": "normal",
        "注意值1": "w1",
        "注意值2": "w2",
        "告警值": "alarm",
    }.get(g or "", "muted")


def _fusion_tone(fusion: dict[str, Any] | None) -> str:
    if not fusion:
        return "diag"
    if fusion.get("confidence") == "低":
        return "w1"
    return "diag"


def _urgency_tone(d: dict[str, Any]) -> str:
    lv = (d.get("urgency") or {}).get("level")
    if lv == "高":
        return "alarm"
    if lv == "中":
        return "w2"
    if lv == "低":
        return "w1"
    return "detect"


def _step_cite_ids(step: dict[str, Any]) -> list[str]:
    if step.get("skipped"):
        return []
    ids = step.get("cite_ids") or []
    if ids:
        return list(dict.fromkeys(ids))
    cite = step.get("cite") or {}
    cid = cite.get("id")
    return [cid] if cid else []


def _infer_severity(step: dict[str, Any]) -> str:
    if step.get("skipped"):
        return "muted"
    sid = step.get("id") or ""
    d = step.get("detail") or {}
    if sid == "input":
        return "detect"
    if sid == "grade":
        return _grade_tone(d.get("grade"))
    if sid == "urgency":
        lv = (d.get("urgency") or {}).get("level")
        if lv == "高":
            return "alarm"
        if lv == "中":
            return "w2"
        if lv == "低":
            return "w1"
        return "detect"
    if sid == "diagnose":
        diag = d.get("diagnosis") or {}
        if not diag.get("triggered"):
            return "muted"
        conf = (diag.get("fusion") or {}).get("confidence")
        if conf == "低":
            return "w1"
        if conf == "高":
            return "w2"
        return "diag"
    if sid == "trend":
        return "trend"
    if sid == "decide":
        return "agent"
    if sid == "report":
        return "report"
    return "detect"


def _log_base(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": step["id"],
        "tag": step["tag"],
        "severity": _infer_severity(step),
        "cite": None if step.get("skipped") else step.get("cite"),
        "cite_ids": _step_cite_ids(step),
    }


def _threshold_for_grade(grade: str | None, bounds: dict[str, Any] | None) -> float | None:
    if not bounds or not grade:
        return None
    val = bounds.get(grade)
    return float(val) if val is not None else None


def _format_grade_rule(ind: dict[str, Any]) -> str:
    item = _gas_symbol(ind)
    basis = _grade_basis(ind)
    thr = _threshold_for_grade(ind.get("grade"), ind.get("bounds"))
    unit = f" {ind['unit']}" if ind.get("unit") else ""
    if thr is not None:
        core = f"{item} {ind['value']} ≥ {thr}"
    else:
        core = f"{item}={ind['value']}{unit}"
    note = f" ({ind['note']})" if ind.get("note") else ""
    prefix = f"({basis}) " if basis else ""
    return f"{prefix}{core} → {ind['grade']}{note}"


def _format_ratio_line(ratios: dict[str, Any] | None) -> str:
    if not ratios:
        return "三比值 → —"
    if not ratios.get("ok"):
        return f"三比值 → {ratios.get('fault') or ratios.get('reason') or '未给出有效判型'}"
    code_arr = ratios.get("code") or []
    enc = "·".join(str(c) for c in code_arr) if len(code_arr) == 3 else ""
    parts = [ratios.get("fault"), f"编码 {enc}" if enc else ""]
    body = " · ".join(p for p in parts if p)
    return f"三比值 → {body or '—'}"


def _format_duval_line(duval: dict[str, Any] | None) -> str:
    if not duval:
        return "大卫三角 → —"
    if not duval.get("ok"):
        return f"大卫三角 → {duval.get('fault') or duval.get('reason') or '未给出有效判型'}"
    zone = duval.get("zone") or "—"
    fault = str(duval.get("fault") or "—")
    if zone != "—":
        fault = re.sub(rf"\s*{re.escape(zone)}\s*$", "", fault).strip() or fault
    return f"大卫三角 → {fault} · {zone}"


def _format_key_gas_line(key_gas: dict[str, Any] | None) -> str:
    if not key_gas:
        return "特征气体 → —"
    if not key_gas.get("ok"):
        return f"特征气体 → {key_gas.get('fault') or key_gas.get('reason') or '未给出有效判型'}"
    return f"特征气体 → {key_gas.get('fault')}"


def _format_fusion_line(fusion: dict[str, Any] | None) -> str:
    if not fusion:
        return "—"
    text = re.sub(r"。$", "", str(fusion.get("summary") or "")).strip()
    if text:
        return text
    primary = fusion.get("primary") or "—"
    code = f" {fusion['primary_code']}" if fusion.get("primary_code") else ""
    conf = fusion.get("confidence") or "—"
    provisional = fusion.get("provisional") or conf == "低"
    prefix = "暂定" if provisional else ""
    return f"{prefix}{primary}{code} · 可信度 {conf}"


def _format_decision_msg(t: dict[str, Any], d: dict[str, Any]) -> str:
    action = t.get("action") or "—"
    field = t.get("field")
    if field == "period":
        return f"检测周期 → {action}"
    if field == "resample":
        return f"二次采样 → {action}"
    if field == "trials":
        nature = d.get("trials_nature_label") or "—"
        count = len(d.get("trials") or [])
        return f"试验建议 → 性质={nature} · 其他检查性试验 {count} 项"
    cond = t.get("condition") or ""
    if (
        cond.startswith("已进入判型")
        or cond.startswith("附录D · 故障性质=")
        or cond.startswith("试验建议")
    ):
        nature = d.get("trials_nature_label")
        if not nature and cond.startswith("附录D · 故障性质="):
            nature = cond.replace("附录D · 故障性质=", "").split("·")[0].strip()
        elif not nature and cond.startswith("试验建议"):
            nature = cond.replace("试验建议 · 性质=", "").split("·")[0].strip()
        nature = nature or "—"
        count = len(d.get("trials") or [])
        return f"试验建议 → 性质={nature} · 其他检查性试验 {count} 项"
    return f"{cond} → {action}"


def _expand_input_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    d = step.get("detail") or {}
    gases = d.get("gases") or {}
    keys = ["c2h2", "total_hydrocarbon", "h2", "ch4", "c2h4", "c2h6"]
    parts: list[str] = []
    for k in keys:
        if k == "total_hydrocarbon":
            v = d.get("total_hydrocarbon", gases.get(k))
        else:
            v = gases.get(k)
        if v is not None:
            parts.append(f"{_GAS_LABEL[k]}={v}μL/L")
    if gases.get("co") is not None:
        parts.append(f"{_GAS_LABEL['co']}={gases['co']}μL/L")
    if gases.get("co2") is not None:
        parts.append(f"{_GAS_LABEL['co2']}={gases['co2']}μL/L")
    date = d.get("date") or ""
    body = ", ".join(parts)
    msg = f"{date} 当日气体 → {body}" if date else f"当日气体 → {body}"
    return [{"cat": "气体", "msg": msg, "conclusion_tone": "detect"}]


def _expand_grade_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    d = step.get("detail") or {}
    lines: list[dict[str, Any]] = []
    for ind in d.get("indicators") or []:
        if ind.get("value") is not None:
            lines.append({
                "cat": "分级",
                "msg": _format_grade_rule(ind),
                "conclusion_tone": _grade_tone(ind.get("grade")),
                "cite_ids": ["1498-表A3"],
                "show_cite": True,
            })
        elif ind.get("note"):
            basis = _grade_basis(ind)
            prefix = f"({basis}) " if basis else ""
            note = ind.get("note") or ""
            tone = _grade_tone(note) if note in ("正常", "注意值1", "注意值2", "告警值") else "normal"
            lines.append({
                "cat": "分级",
                "msg": f"{prefix}{_gas_symbol(ind)} → {note}",
                "conclusion_tone": tone,
                "cite_ids": ["1498-表A3"],
                "show_cite": True,
            })
    grade = d.get("grade") or (_log_result(step.get("log")).split("·")[0] or "").strip()
    lines.append({
        "cat": "分级",
        "msg": f"单日最高档 → {grade or '正常'}",
        "highlight": True,
        "conclusion_tone": _grade_tone(grade),
        "cite_ids": ["1498-表A3"],
        "show_cite": True,
    })
    return lines


def _expand_trend_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    d = step.get("detail") or {}
    rate = f"{d['thc_rel_rate']}%/月" if d.get("thc_rel_rate") is not None else "—"
    is_pre = bool(d.get("is_pre"))
    rising = bool((d.get("urgency") or {}).get("rising")) or (
        d.get("thc_rel_rate") is not None and d["thc_rel_rate"] >= 10
    )
    verdict = "未超注意值"
    tone = "normal"
    if is_pre:
        verdict = "涨势预警（档未达注意值2）"
        tone = "pre"
    elif rising:
        verdict = "涨势快"
        tone = "w2"
    return [{
        "cat": "趋势",
        "msg": f"产气趋势 · 总烃月环比 {rate} → {verdict}",
        "conclusion_tone": tone,
        "cite_ids": ["722-9.3.2"],
        "show_cite": True,
    }]


def _expand_urgency_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    if step.get("skipped"):
        return [{
            "cat": "处置",
            "msg": "档未达注意值2/告警 → 紧急度不适用",
            "conclusion_tone": "muted",
            "cite_ids": ["722-9.3.3"],
            "show_cite": True,
        }]
    d = step.get("detail") or {}
    lv = (d.get("urgency") or {}).get("level") or "—"
    rate = f"{d['thc_rel_rate']}%/月" if d.get("thc_rel_rate") is not None else "—"
    detail = f"总烃月环比 {rate}"
    if lv == "高":
        detail = f"涨势快 · 总烃月环比 {rate} 超注意值"
    elif lv == "中":
        detail = f"暂稳 · 总烃月环比 {rate} 未超注意值"
    elif lv == "低":
        detail = f"仅 H₂ 超标且速率未超 · 总烃月环比 {rate}"
    return [{
        "cat": "处置",
        "msg": f"处置紧急度 → {lv}（{detail}）",
        "conclusion_tone": _urgency_tone(d),
        "cite_ids": ["722-9.3.3"],
        "show_cite": True,
    }]


def _expand_diagnose_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    diag = (step.get("detail") or {}).get("diagnosis") or {}
    if not diag.get("triggered"):
        return [{
            "cat": "判型",
            "msg": "判型门槛 → 未达，三比值 / Duval / 特征气体未启动",
            "conclusion_tone": "muted",
        }]
    fusion = diag.get("fusion")
    fusion_cites = _step_cite_ids(step)
    return [
        {
            "cat": "判型",
            "msg": _format_ratio_line(diag.get("ratios")),
            "conclusion_tone": "diag",
            "cite_ids": ["722-表6-7"],
            "show_cite": True,
        },
        {
            "cat": "判型",
            "msg": _format_duval_line(diag.get("duval")),
            "conclusion_tone": "diag",
            "cite_ids": ["722-附录C"],
            "show_cite": True,
        },
        {
            "cat": "判型",
            "msg": _format_key_gas_line(diag.get("key_gas")),
            "conclusion_tone": "diag",
            "cite_ids": ["722-表5"],
            "show_cite": True,
        },
        {
            "cat": "判型",
            "msg": f"三方交叉融合 → {_format_fusion_line(fusion)}",
            "highlight": True,
            "conclusion_tone": _fusion_tone(fusion),
            "cite_ids": fusion_cites or ["722-10.3"],
            "show_cite": True,
        },
    ]


def _expand_decide_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    d = step.get("detail") or {}
    traj = d.get("trajectory") or []
    if traj:
        return [
            {
                "cat": "决策",
                "msg": _format_decision_msg(t, d),
                "conclusion_tone": "agent",
                "cite_ids": [t["cite"]] if t.get("cite") else [],
                "show_cite": bool(t.get("cite")),
            }
            for t in traj
        ]
    return [{"cat": "决策", "msg": _log_result(step.get("log"))}]


def _expand_report_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    raw = _log_result(step.get("log"))
    if "→" in raw:
        return [{"cat": "报告", "msg": raw, "conclusion_tone": "report"}]
    return [{"cat": "报告", "msg": f"分析报告 → {raw}", "conclusion_tone": "report"}]


_EXPANDERS = {
    "input": _expand_input_logs,
    "grade": _expand_grade_logs,
    "trend": _expand_trend_logs,
    "urgency": _expand_urgency_logs,
    "diagnose": _expand_diagnose_logs,
    "decide": _expand_decide_logs,
    "report": _expand_report_logs,
}


def _expand_step_logs(step: dict[str, Any]) -> list[dict[str, Any]]:
    base = _log_base(step)
    expand = _EXPANDERS.get(step.get("id", ""))
    if expand:
        payloads = expand(step)
    else:
        payloads = [{"cat": step.get("label"), "msg": _log_result(step.get("log"))}]
    out: list[dict[str, Any]] = []
    for i, p in enumerate(payloads):
        line = {**base, **p}
        if p.get("cite_ids") is None:
            line["cite_ids"] = base["cite_ids"]
        if "show_cite" not in p:
            line["show_cite"] = i == len(payloads) - 1
        # 行级着色：优先 conclusion_tone（与前端 sev-* / tone-* 一致）
        if p.get("conclusion_tone"):
            line["severity"] = p["conclusion_tone"]
        out.append(line)
    return out
