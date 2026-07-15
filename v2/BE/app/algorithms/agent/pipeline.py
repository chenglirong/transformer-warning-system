"""Agent 编排 —— 工作流引擎串工具,产出步骤日志+时间线+决策轨迹+表G.1。

红线:分级/判型/告警全由国标规则;LLM 写分析意见与 G.2 试验成稿,失败则模板降级。
纯算法:输入 DataFrame + 目标日,输出编排结果 dict。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.algorithms.agent.cites import place_cites_in_opinion
from app.algorithms.agent.decide import decide_c
from app.algorithms.agent.report_b import build_facts_pack, generate_opinion
from app.algorithms.agent.report_card import build_g1_card, build_g2_card
from app.algorithms.agent.tools import make_observation
from app.algorithms.agent.workflow import (
    append_timeline,
    build_plan,
    eligible_for_diagnose,
    plan_event,
)
from app.algorithms.detect.grade import detect
from app.algorithms.diagnose.pipeline import diagnose_sample
from app.algorithms.knowledge.refs import (
    cites_for_decision,
    cites_for_detect,
    cites_for_diagnosis,
    expand,
)

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


def run_agent(df: pd.DataFrame, day: str, *, force_template: bool = False) -> dict[str, Any]:
    """对指定监测日跑工作流编排。

    force_template=True 时强制 Agent B 走规则模板(答辩演示降级/无网环境)。
    """
    if df.empty:
        raise ValueError("无监测数据")
    df = df.reset_index(drop=True)
    if day not in set(df["date"].astype(str)):
        raise ValueError(f"日期不存在:{day}")

    results = detect(df)
    idx = int(df.index[df["date"].astype(str) == day][0])
    hit = results[idx]
    row = df.iloc[idx]
    day_num = idx + 1

    gases = {g: round(float(row[g]), 2) for g in GAS_COLS}
    co = float(row["co"]) if row.get("co") is not None and pd.notna(row.get("co")) else None
    co2 = float(row["co2"]) if row.get("co2") is not None and pd.notna(row.get("co2")) else None
    if co is not None:
        gases["co"] = round(co, 2)
    if co2 is not None:
        gases["co2"] = round(co2, 2)

    thc = hit["total_hydrocarbon"]
    grade = hit["grade"]
    is_pre = bool(hit.get("is_pre"))
    urgency = hit.get("urgency")
    thc_rel = hit.get("thc_rel_rate")
    rate_rising = bool(hit.get("rate_rising"))
    triggers = hit.get("triggers") or []
    indicators = hit.get("indicators") or []

    can_diag = eligible_for_diagnose(grade, rate_rising=rate_rising, is_pre=is_pre)
    plan = build_plan(eligible_diagnose=can_diag)
    timeline: list[dict[str, Any]] = [plan_event(plan)]

    # —— 工具调用链(状态机顺序,非自由 ReAct) ——
    # 当日气体:每项数值后跟单位,日期另附
    def _g(label: str, val: float | int) -> str:
        return f"{label} {val}µL/L"

    gas_parts = [
        _g("H₂", gases["h2"]),
        _g("CH₄", gases["ch4"]),
        _g("C₂H₄", gases["c2h4"]),
        _g("C₂H₆", gases["c2h6"]),
        _g("C₂H₂", gases["c2h2"]),
        _g("总烃", thc),
    ]
    if "co" in gases:
        gas_parts.append(_g("CO", gases["co"]))
    if "co2" in gases:
        gas_parts.append(_g("CO₂", gases["co2"]))
    gas_log = " · ".join(gas_parts) + f" · {day}"
    obs_ingest = make_observation(
        tool="ingest.load",
        status="ok",
        summary=gas_log,
        data={"day": day_num, "date": day, "gases": gases, "total_hydrocarbon": thc},
        cite_ids=[],  # 数据装载,不挂判据条文
    )
    append_timeline(timeline, phase="call", observation=obs_ingest)

    detect_cites = cites_for_detect(is_pre=is_pre, urgency=urgency)
    obs_grade = make_observation(
        tool="detect.grade",
        status="ok",
        summary=_grade_log(grade, triggers),
        data={"grade": grade, "triggers": triggers, "indicators": indicators},
        cite_ids=["1498-表A3"],
    )
    append_timeline(timeline, phase="call", observation=obs_grade)

    # 先产气趋势(月环比),再处置紧急度(涨势快→高)——因果顺序
    obs_trend = make_observation(
        tool="trend.rate",
        status="ok",
        summary=_trend_log(is_pre, thc_rel, urgency),
        data={"is_pre": is_pre, "thc_rel_rate": thc_rel},
        cite_ids=["722-9.3.2"],
    )
    append_timeline(timeline, phase="call", observation=obs_trend)

    obs_urgency = make_observation(
        tool="detect.urgency",
        # 处置紧急度仅注意值2+ 启动;涨势预警(is_pre)归「产气趋势」,不塞本步
        status="ok" if urgency else "skip",
        skipped=not bool(urgency),
        summary=_urgency_log(grade, urgency, thc_rel, is_pre),
        data={"urgency": urgency, "thc_rel_rate": thc_rel, "is_pre": is_pre},
        cite_ids=["722-9.3.3", "722-9.3.2"] if urgency else ["722-9.3.3"],
    )
    append_timeline(timeline, phase="call", observation=obs_urgency)

    diagnosis = diagnose_sample(
        grade=grade,
        h2=gases["h2"], ch4=gases["ch4"], c2h4=gases["c2h4"],
        c2h6=gases["c2h6"], c2h2=gases["c2h2"],
        co=co, co2=co2,
        rate_rising=rate_rising,
        is_pre=is_pre,
    )
    fusion = diagnosis.get("fusion") if diagnosis.get("triggered") else None
    diag_cites = cites_for_diagnosis(
        triggered=bool(diagnosis.get("triggered")),
        trigger_by=diagnosis.get("trigger_by"),
        fusion=fusion,
    )
    # 运行日志故障类型只挂判断流程 §10.3；细则角标留给报告/知识区
    diag_log_cites = ["722-10.3"]
    obs_diag = make_observation(
        tool="diagnose.fusion",
        status="ok" if diagnosis.get("triggered") else "skip",
        skipped=not bool(diagnosis.get("triggered")),
        summary=_diag_log(diagnosis, fusion),
        data={"diagnosis": diagnosis},
        cite_ids=diag_log_cites,
    )
    append_timeline(timeline, phase="call", observation=obs_diag)

    decision = decide_c(
        grade=grade, is_pre=is_pre, urgency=urgency, fusion=fusion,
        rate_rising=rate_rising,
    )
    decide_cites = cites_for_decision(is_pre=is_pre, grade=grade)
    obs_decide = make_observation(
        tool="agent.decide",
        status="ok",
        summary=decision["log"],
        data={
            "period": decision["period"],
            "resample": decision["resample"],
            "trajectory": decision.get("trajectory") or [],
        },
        cite_ids=decide_cites,
    )
    append_timeline(timeline, phase="decide", observation=obs_decide)

    facts = build_facts_pack(
        grade=grade, gases=gases, thc=thc, triggers=triggers,
        is_pre=is_pre, thc_rel=thc_rel, urgency=urgency,
        diagnosis=diagnosis, fusion=fusion, decision=decision,
    )
    opinion_pack = generate_opinion(facts=facts, force_template=force_template)
    report_mode = opinion_pack["mode"]

    report_cites = ["722-附录G"]
    cite_ids = list(dict.fromkeys(
        detect_cites + ["722-9.3.2", "722-9.3.3"] + diag_cites + decide_cites + report_cites
    ))
    opinion, cite_map = place_cites_in_opinion(
        opinion_pack["text"],
        section_ids={
            "grade": ["1498-表A3"],
            "trend": ["722-9.3.2"],
            "urgency": ["722-9.3.3"],
            "diagnose": diag_cites,
            "decide": decide_cites,
            "report": report_cites,
        },
        all_ids=cite_ids,
    )

    report_no = f"RPT-{day.replace('-', '')}-{day_num:03d}"
    if report_mode == "llm":
        report_log = f"大模型撰写 · {report_no}"
    else:
        report_log = f"固定模板 · {report_no}"
    if opinion_pack.get("error"):
        report_log += f" · {opinion_pack['error']}"
    elif opinion_pack.get("note"):
        report_log += f" · {opinion_pack['note']}"
    obs_report = make_observation(
        tool="agent.report",
        status="ok",
        summary=report_log,
        data={"report_no": report_no, "mode": report_mode},
        cite_ids=report_cites,
    )
    append_timeline(timeline, phase="report", observation=obs_report)

    sample_dates = _sample_dates(df, idx)

    # 前端七步竖条:分级 → 紧急度 → 产气趋势 → 故障类型 → …
    steps = [
        _step(
            id="input",
            label="当日气体",
            sub="七气浓度（μL/L）",
            tag="detect",
            cite=None,
            cite_ids=[],
            log=obs_ingest["summary"],
            detail=obs_ingest["data"],
            tool="ingest.load",
        ),
        _step(
            id="grade",
            label="四档分级",
            sub="DL/T 1498.2 表 A.3",
            tag="detect",
            cite={"id": "1498-表A3", "label": "表A.3"},
            cite_ids=obs_grade.get("cite_ids") or ["1498-表A3"],
            log=obs_grade["summary"],
            detail={**obs_grade["data"], "cite_ids": obs_grade.get("cite_ids") or ["1498-表A3"]},
            tool="detect.grade",
        ),
        _step(
            id="trend",
            label="产气趋势",
            sub="722 §9.3.2 总烃月环比",
            tag="trend",
            cite={"id": "722-9.3.2", "label": "§9.3.2"},
            cite_ids=obs_trend.get("cite_ids") or ["722-9.3.2"],
            log=obs_trend["summary"],
            detail=obs_trend["data"],
            tool="trend.rate",
        ),
        _step(
            id="urgency",
            label="处置紧急度",
            sub="注意值2+/告警 · §9.3.3",
            tag="detect",
            cite={"id": "722-9.3.3", "label": "§9.3.3"},
            cite_ids=obs_urgency.get("cite_ids") or ["722-9.3.3"],
            log=obs_urgency["summary"],
            detail=obs_urgency["data"],
            tool="detect.urgency",
            skipped=bool(obs_urgency.get("skipped")),
        ),
        _step(
            id="diagnose",
            label="故障类型",
            sub="三比值法 · Duval · 特征气体",
            tag="diag",
            cite={"id": "722-10.3", "label": "§10.3"},
            cite_ids=diag_log_cites,
            log=obs_diag["summary"],
            detail={"diagnosis": diagnosis, "cite_ids": diag_log_cites},
            tool="diagnose.fusion",
            skipped=bool(obs_diag.get("skipped")),
        ),
        _step(
            id="decide",
            label="监测决策",
            sub="检测周期 · 二次采样 · 试验建议",
            tag="agent",
            cite={"id": "1498-5.4.5", "label": "§5.4.5 / A.3.1"},
            cite_ids=decide_cites,
            log=decision["log"],
            detail={**decision, "cite_ids": decide_cites, "report_mode": report_mode},
            tool="agent.decide",
        ),
        _step(
            id="report",
            label="生成报告",
            sub="附录 G 档案卡片 · 分析意见",
            tag="report",
            cite={"id": "722-附录G", "label": "附录G"},
            cite_ids=report_cites,
            log=report_log,
            detail={"report_no": report_no, "mode": report_mode, "cite_ids": report_cites},
            tool="agent.report",
        ),
    ]

    g1 = build_g1_card(
        df=df,
        idx=idx,
        day=day,
        day_num=day_num,
        sample_dates=sample_dates,
        opinion=opinion,
        report_no=report_no,
        cite_ids=cite_ids,
        cite_map=cite_map,
    )
    g2 = build_g2_card(
        other_tests=opinion_pack.get("other_tests") or "",
        trials=decision.get("trials") or [],
        trials_appendix_d=decision.get("trials_appendix_d") or [],
        trials_1685_items=decision.get("trials_1685_items") or [],
        trials_basis=decision.get("trials_basis") or [],
        trials_purpose=decision.get("trials_purpose"),
        trials_nature=decision.get("trials_nature_label"),
        grade=grade,
        confidence=(fusion or {}).get("confidence") if fusion else None,
        provisional=bool((fusion or {}).get("provisional")) if fusion else False,
    )

    note = opinion_pack.get("note") or opinion_pack.get("error")

    return {
        "date": day,
        "grade": grade,
        "steps": steps,
        "decision": decision,
        "g1": g1,
        "g2": g2,
        "mode": report_mode,
        "note": note,
    }


def _step(
    *,
    id: str,
    label: str,
    sub: str,
    tag: str,
    cite: dict | None,
    log: str,
    detail: Any,
    tool: str | None = None,
    cite_ids: list[str] | None = None,
    skipped: bool = False,
) -> dict:
    ids = list(cite_ids or [])
    if not ids and cite and cite.get("id"):
        ids = [cite["id"]]
    return {
        "id": id, "label": label, "sub": sub, "tag": tag,
        "cite": cite, "cite_ids": ids, "log": log, "detail": detail,
        "tool": tool, "skipped": bool(skipped),
    }


def _grade_log(grade: str, triggers: list) -> str:
    if not triggers:
        return f"{grade} · 七项均在正常范围"
    parts = [f"{_gas_zh(t.get('gas'))}→{t.get('grade')}" for t in triggers[:5]]
    return f"{grade} · " + " · ".join(parts)


def _urgency_log(grade: str, urgency: dict | None, thc_rel: float | None, is_pre: bool) -> str:
    """注意值2+/告警才给高/中/低;更低档「不适用」。

    口径:涨势快→高;暂稳→中;仅 H₂ 特殊协调→低。
    """
    _ = (grade, is_pre)
    rate = f"{thc_rel}%/月" if thc_rel is not None else "—"
    if not urgency:
        return "不适用"
    level = urgency.get("level") or "—"
    if level == "高":
        return f"高 · 涨势快（总烃月环比 {rate} 超注意值）"
    if level == "中":
        return f"中 · 暂稳（总烃月环比 {rate} 未超注意值）"
    if level == "低":
        return f"低 · 仅 H₂ 特殊协调（总烃月环比 {rate}）"
    return f"{level} · 总烃月环比 {rate}"


def _diag_log(diagnosis: dict, fusion: dict | None) -> str:
    """只陈述判型结论;未触发则为未启动(不写触发原因长句)。"""
    if not diagnosis.get("triggered"):
        return "未启动"
    if not fusion:
        return "已触发但融合无结论"
    primary = fusion.get("primary") or ""
    code = fusion.get("primary_code") or ""
    conf = fusion.get("confidence") or "—"
    provisional = fusion.get("provisional") or conf == "低"
    stance = "暂定" if provisional else ""
    conf_r = fusion.get("confidence_reason") or ""
    code_bit = f" · {code}" if code and code not in str(primary) else ""
    return (
        f"{stance}{primary}{code_bit} · 可信度{conf}"
        + (f" · {conf_r}" if conf_r else "")
        + (f" · {fusion.get('paper_note')}" if fusion.get("paper_note") else "")
        + (" · 不作确诊" if provisional else "")
    )


def _trend_log(is_pre: bool, thc_rel: float | None, urgency: dict | None) -> str:
    """统一用词:涨势预警(档未到注意值2)|涨势快(已达注意值2+且速率超)|未超注意值。"""
    rate = f"{thc_rel}%/月" if thc_rel is not None else "—"
    if is_pre:
        return f"总烃月环比 {rate} · 涨势预警（档未达注意值2）"
    if urgency and urgency.get("rising"):
        return f"总烃月环比 {rate} · 涨势快"
    if thc_rel is not None and thc_rel >= 10:
        return f"总烃月环比 {rate} · 涨势快"
    return f"总烃月环比 {rate} · 未超注意值"


def _sample_dates(df: pd.DataFrame, idx: int) -> list[str | None]:
    """表G.1 取样条件四列:当日、约一周前、约两周前、约三周前。

    合成时序为逐日,取固定回望填满四列(早期日不足则该列 None→前端「—」)。
    """
    dates = df["date"].astype(str).tolist()
    out: list[str | None] = []
    for back in (0, 7, 14, 21):
        j = idx - back
        out.append(dates[j] if j >= 0 else None)
    return out


def _gas_zh(gas: str | None) -> str:
    return {
        "c2h2": "乙炔", "h2": "氢气", "total_hydrocarbon": "总烃",
        "ch4": "甲烷", "c2h4": "乙烯", "c2h6": "乙烷",
    }.get(gas or "", gas or "—")
