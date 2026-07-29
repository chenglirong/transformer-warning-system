"""规则解释 — 从 run_agent() 结果生成确定性中文 + cite_ids。"""
from __future__ import annotations

from typing import Any

_GAS_ZH = {
    "h2": "氢气",
    "ch4": "甲烷",
    "c2h4": "乙烯",
    "c2h6": "乙烷",
    "c2h2": "乙炔",
    "co": "CO",
    "co2": "CO₂",
    "total_hydrocarbon": "总烃",
}

def _step(result: dict, step_id: str) -> dict:
    for s in result.get("steps") or []:
        if s.get("id") == step_id:
            return s
    return {}


def _gas_zh(gas: str | None) -> str:
    return _GAS_ZH.get(gas or "", gas or "—")


def analysis_cite_ids(result: dict) -> list[str]:
    cite_ids = ["1498-表A3", "722-9.3.2"]
    diag_step = _step(result, "diagnose")
    diag = (diag_step.get("detail") or {}).get("diagnosis") or {}
    if not diag_step.get("skipped") and diag.get("triggered"):
        cite_ids.append("722-10.3")
    decision = result.get("decision") or {}
    if decision.get("cite_period"):
        cite_ids.append(decision["cite_period"])
    if decision.get("trials"):
        cite_ids.append("722-附录D")
    return list(dict.fromkeys(cite_ids))


def _analysis_facts(result: dict) -> dict[str, str]:
    day = result.get("date") or "—"
    grade = result.get("grade") or "—"
    trend_log = (_step(result, "trend").get("log") or "—")

    diag_step = _step(result, "diagnose")
    diag = (diag_step.get("detail") or {}).get("diagnosis") or {}
    fusion = diag.get("fusion") or {}
    if diag_step.get("skipped") or not diag.get("triggered"):
        diag_bit = "未启动（未达判型门槛）"
    else:
        primary = fusion.get("primary") or diag_step.get("log") or "—"
        conf = fusion.get("confidence")
        diag_bit = f"{primary}" + (f"，可信度{conf}" if conf else "")

    decision = result.get("decision") or {}
    return {
        "day": day,
        "grade": grade,
        "trend": trend_log,
        "diagnosis": diag_bit,
        "period": decision.get("period") or "—",
        "resample": decision.get("resample") or "—",
    }


def analysis_draft_for_llm(result: dict) -> dict[str, Any]:
    """仅作 LLM 输入的事实条目，不直接展示给用户。"""
    f = _analysis_facts(result)
    text = "\n".join([
        f"日期={f['day']}",
        f"最高档={f['grade']}",
        f"产气趋势={f['trend']}",
        f"故障判型={f['diagnosis']}",
        f"检测周期={f['period']}",
        f"二次采样={f['resample']}",
    ])
    return {"text": text, "cite_ids": analysis_cite_ids(result)}


def analysis_summary(result: dict) -> dict[str, Any]:
    """用户可见的规则成稿（润色失败时的回退，不是 key=value）。"""
    f = _analysis_facts(result)
    text = (
        f"{f['day']} 的 DGA 分析已完成。"
        f"当日最高档为「{f['grade']}」，产气趋势为{f['trend']}，"
        f"故障判型为{f['diagnosis']}。"
        f"监测决策：检测周期 → {f['period']}；二次采样 → {f['resample']}。"
    )
    return {"text": text, "cite_ids": analysis_cite_ids(result)}


def analysis_done(result: dict) -> dict[str, Any]:
    """兼容别名。"""
    return analysis_summary(result)


def explain_grade(result: dict) -> dict[str, Any]:
    step = _step(result, "grade")
    if not step:
        return {"text": "未找到分级结果，请先运行分析。", "cite_ids": []}

    grade = result.get("grade") or "—"
    detail = step.get("detail") or {}
    triggers = detail.get("triggers") or []
    log = step.get("log") or ""

    if not triggers:
        return {
            "text": (
                f"当日最高档为「{grade}」。依据 DL/T 1498.2 表A.3，"
                f"七项特征气体均在正常范围内，未触发表A.3 任一注意值或告警值阈值。"
                f"步骤日志：{log}"
            ),
            "cite_ids": ["1498-表A3"],
        }

    parts = []
    for t in triggers[:5]:
        gas = _gas_zh(t.get("gas"))
        basis = t.get("basis") or "—"
        tgrade = t.get("grade") or "—"
        parts.append(f"{gas}的{basis}达到{tgrade}")

    return {
        "text": (
            f"当日最高档为「{grade}」，依据 DL/T 1498.2 表A.3，"
            f"{'、'.join(parts)}，因此取最高档。"
            f"表A.3 按浓度、增量、周增率三维度分别判定，取最高档。"
            f"（{log}）"
        ),
        "cite_ids": ["1498-表A3"],
    }


def explain_trend(result: dict) -> dict[str, Any]:
    step = _step(result, "trend")
    if not step:
        return {"text": "未找到产气趋势结果，请先运行分析。", "cite_ids": []}

    log = step.get("log") or "—"
    detail = step.get("detail") or {}
    is_pre = detail.get("is_pre")
    thc_rel = detail.get("thc_rel_rate")

    extra = ""
    if is_pre:
        extra = (
            "「涨势预警」表示档位尚未达注意值2，但总烃月环比已超过 "
            "DL/T 722 §9.3.2 注意值（约 10%/月），需加强监视。"
        )
    elif "涨势快" in log:
        extra = "「涨势快」表示档位已达注意值2/告警且总烃月环比超注意值。"

    rate_bit = f"{thc_rel}%/月" if thc_rel is not None else "—"
    return {
        "text": (
            f"产气趋势依据 DL/T 722 §9.3.2 总烃相对产气速率（月环比）。"
            f"当前总烃月环比约 {rate_bit}。步骤结论：{log}。{extra}"
        ),
        "cite_ids": ["722-9.3.2", "722-9.3.3"],
    }


def _diagnosis_bundle(result: dict) -> tuple[dict, dict, dict, dict]:
    step = _step(result, "diagnose")
    detail = step.get("detail") or {}
    diagnosis = detail.get("diagnosis") or {}
    fusion = diagnosis.get("fusion") or {}
    return step, diagnosis, fusion, detail


def _skipped_diagnosis_text(step: dict) -> dict[str, Any]:
    return {
        "text": (
            "故障类型步骤已跳过。依据 DL/T 722 §10.2.1、§10.2.4 a，"
            "三比值/Duval/特征气体法一般在注意值2/告警或有增长趋势（含涨势预警）后使用。"
            f"当前日志：{step.get('log') or '未启动'}。"
        ),
        "cite_ids": ["722-10.2.4a", "722-10.3"],
    }


def _reasoning_line(fusion: dict, label: str) -> str | None:
    for r in fusion.get("reasoning") or []:
        if r.get("label") == label:
            return str(r.get("text") or "")
    return None


def explain_key_gas(result: dict) -> dict[str, Any]:
    step, diagnosis, fusion, _ = _diagnosis_bundle(result)
    if not step:
        return {"text": "未找到故障类型研判结果，请先运行分析。", "cite_ids": []}
    if step.get("skipped"):
        return _skipped_diagnosis_text(step)

    kg = diagnosis.get("key_gas") or {}
    fault = kg.get("fault") or "—"
    if not kg.get("ok") and fault in ("数据不足", "未达表3注意值", "无明显特征气体偏高", "无法匹配表5", "—"):
        return {
            "text": f"特征气体法（DL/T 722 表5）当日未得出有效结论：{fault}。",
            "cite_ids": ["722-表5"],
        }

    nature = kg.get("nature") or ""
    chain = _reasoning_line(fusion, "特征气体") or f"表5 →「{fault}」"
    primary = fusion.get("primary") or "—"

    text = f"特征气体法依据 DL/T 722 表5（判型入口已由注意值2/告警或涨势预警统一把关）。当日结论：「{fault}」"
    if nature:
        text += f"（性质：{nature}）"
    text += f"。推理链：{chain}。"
    if primary and primary != fault:
        text += f"交叉研判综合主结论为「{primary}」，与特征气体法表述可能不完全相同，以三法综合为准。"
    return {"text": text, "cite_ids": ["722-表5", "722-10.3"]}


def explain_ratios(result: dict) -> dict[str, Any]:
    step, diagnosis, fusion, _ = _diagnosis_bundle(result)
    if not step:
        return {"text": "未找到故障类型研判结果，请先运行分析。", "cite_ids": []}
    if step.get("skipped"):
        return _skipped_diagnosis_text(step)

    ratios = diagnosis.get("ratios") or {}
    fault = ratios.get("fault") or "—"
    code = ratios.get("code")
    chain = _reasoning_line(fusion, "三比值") or fault
    primary = fusion.get("primary") or "—"
    code_str = "".join(str(c) for c in code) if code else "—"

    text = f"三比值法依据 DL/T 722 §10.2 表6/表7。编码：{code_str}；判型：「{fault}」。推理链：{chain}。"
    if primary and str(primary) != str(fault):
        text += f"交叉研判综合主结论为「{primary}」。"
    return {"text": text, "cite_ids": ["722-表6-7", "722-10.2.4a"]}


def explain_duval(result: dict) -> dict[str, Any]:
    step, diagnosis, fusion, _ = _diagnosis_bundle(result)
    if not step:
        return {"text": "未找到故障类型研判结果，请先运行分析。", "cite_ids": []}
    if step.get("skipped"):
        return _skipped_diagnosis_text(step)

    duval = diagnosis.get("duval") or {}
    fault = duval.get("fault") or "—"
    zone = duval.get("zone") or "—"
    chain = _reasoning_line(fusion, "大卫三角") or fault
    primary = fusion.get("primary") or "—"

    text = f"大卫三角（Duval）依据 DL/T 722 附录C。落区：{zone}；结论：「{fault}」。推理链：{chain}。"
    if primary and str(primary) != str(fault):
        text += f"交叉研判综合主结论为「{primary}」。"
    return {"text": text, "cite_ids": ["722-附录C", "722-10.3"]}


def explain_diagnosis(result: dict) -> dict[str, Any]:
    step, diagnosis, fusion, _ = _diagnosis_bundle(result)
    if not step:
        return {"text": "未找到故障类型研判结果，请先运行分析。", "cite_ids": []}

    if step.get("skipped"):
        return _skipped_diagnosis_text(step)

    log = step.get("log") or "—"
    conf = fusion.get("confidence") or "—"
    primary = fusion.get("primary") or "—"
    code = fusion.get("primary_code") or ""

    # 三法分项摘要
    parts: list[str] = []
    for label, key in (("三比值", "ratios"), ("大卫三角", "duval"), ("特征气体", "key_gas")):
        sub = diagnosis.get(key) or {}
        f = sub.get("fault")
        if f:
            parts.append(f"{label}：{f}")

    methods_bit = "；".join(parts) if parts else "—"

    return {
        "text": (
            f"故障类型依据 DL/T 722 §10 三法交叉研判。"
            f"综合主结论：{primary}"
            + (f"（编码 {code}）" if code else "")
            + f"；可信度：{conf}。分项：{methods_bit}。"
            f"步骤日志：{log}。"
        ),
        "cite_ids": ["722-10.3", "722-10.2.4a"],
    }


def _collect_trial_names(result: dict) -> list[str]:
    """从 decision / g2 块汇总全部建议试验名称（去重保序）。"""
    decision = result.get("decision") or {}
    names: list[str] = []

    for t in decision.get("trials") or []:
        s = str(t).strip()
        if s:
            names.append(s)

    g2 = result.get("g2") or {}
    for block in g2.get("other_tests_blocks") or []:
        for item in block.get("items") or []:
            s = str(item).strip()
            if s:
                names.append(s)
        suggest = block.get("suggest")
        if suggest:
            s = str(suggest).strip()
            if s:
                names.append(s)

    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _format_trial_list(names: list[str]) -> str:
    if not names:
        return "—"
    return "\n".join(f"{i + 1}. {n}" for i, n in enumerate(names))


def explain_trials(result: dict) -> dict[str, Any]:
    """列出当日全部其他检查性试验项目。"""
    decision = result.get("decision") or {}
    names = _collect_trial_names(result)

    if not names:
        return {
            "text": (
                "当日监测决策未映射出其他检查性试验，"
                "可能因故障判型未触发或档位/趋势不满足附录D 映射条件。"
            ),
            "cite_ids": ["722-附录D", "1685-附录B"],
        }

    nature = decision.get("trials_nature_label") or "—"
    purpose = decision.get("trials_purpose")
    purpose_zh = "验证性" if purpose == "verify" else ("查明性" if purpose else "—")

    return {
        "text": (
            f"其他检查性试验共 {len(names)} 项（故障性质：{nature}，试验目的：{purpose_zh}）。"
            f"依据 DL/T 722 附录D 与 DL/T 1685 附录B 映射，建议项目如下：\n"
            f"{_format_trial_list(names)}"
        ),
        "cite_ids": ["722-附录D", "1685-附录B"],
    }


def explain_decision(result: dict) -> dict[str, Any]:
    step = _step(result, "decide")
    decision = result.get("decision") or {}
    if not step and not decision:
        return {"text": "未找到监测决策结果，请先运行分析。", "cite_ids": []}

    period = decision.get("period") or "—"
    resample = decision.get("resample") or "—"
    log = step.get("log") or decision.get("log") or "—"
    names = _collect_trial_names(result)
    trials_block = _format_trial_list(names) if names else "—"

    return {
        "text": (
            f"监测决策综合当日档位、产气趋势与判型结论。"
            f"建议检测周期：{period}；二次采样：{resample}。"
            f"其他检查性试验共 {len(names)} 项：\n{trials_block}\n"
            f"步骤日志：{log}。"
            "试验项目映射依据 DL/T 722 附录D 与 DL/T 1685 附录B。"
        ),
        "cite_ids": ["1498-5.4.5", "722-附录D", "1685-附录B"],
    }


def explain_report(result: dict) -> dict[str, Any]:
    step = _step(result, "report")
    mode = result.get("mode") or "rule_template"
    g1 = result.get("g1") or {}
    g2 = result.get("g2") or {}
    report_no = (step.get("detail") or {}).get("report_no") or "—"
    opinion = (g1.get("opinion") or "")[:200]
    other = (g2.get("other_tests") or "")[:200]

    mode_zh = "大模型撰写" if mode == "llm" else "固定模板"
    text = (
        f"报告编号 {report_no}，成稿模式：{mode_zh}。"
        f"G.1 分析意见（摘要）：{opinion or '—'}。"
    )
    if other:
        text += f" G.2 其他检查性试验（摘要）：{other}。"
    note = result.get("note")
    if note:
        text += f" 备注：{note}。"

    return {
        "text": text,
        "cite_ids": ["722-附录G"],
    }


def explain_confidence(result: dict | None) -> dict[str, Any]:
    """解释可信度含义；有当日结果时结合研判结论。"""
    general = (
        "可信度反映三比值、Duval、特征气体交叉研判的一致程度："
        "高 = 多种方法结论一致；中 = 部分分歧；低 = 分歧明显或数据不充分。"
        "低可信度时标注「暂定结论」，不作确诊，宜二次采样复核。"
    )
    if not result:
        return {"text": general, "cite_ids": ["722-10.3"]}

    step = _step(result, "diagnose")
    if step.get("skipped"):
        return {
            "text": general + " 当日未启动故障类型研判，暂无可信度结论。",
            "cite_ids": ["722-10.3"],
        }

    detail = step.get("detail") or {}
    diagnosis = detail.get("diagnosis") or {}
    fusion = diagnosis.get("fusion") or {}
    conf = fusion.get("confidence") or "—"
    conf_r = fusion.get("confidence_reason") or ""
    provisional = bool(fusion.get("provisional")) or conf == "低"

    text = f"{general} 当日研判可信度为「{conf}」"
    if conf_r:
        text += f"（{conf_r}）"
    if provisional:
        text += "。当前为暂定结论，建议结合产气趋势加密监视并安排二次采样。"
    elif conf == "高":
        text += "。表示三法结论一致，但仍须结合档位与涨势综合判断。"
    return {"text": text, "cite_ids": ["722-10.3"]}


EXPLAIN_HANDLERS = {
    "explain_confidence": explain_confidence,
    "explain_grade": explain_grade,
    "explain_trend": explain_trend,
    "explain_key_gas": explain_key_gas,
    "explain_ratios": explain_ratios,
    "explain_duval": explain_duval,
    "explain_diagnosis": explain_diagnosis,
    "explain_trials": explain_trials,
    "explain_decision": explain_decision,
    "explain_report": explain_report,
}
