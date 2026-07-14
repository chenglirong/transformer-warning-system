"""Agent 编排 —— 串检测/判型/趋势,产出步骤日志+依据+表G.1+监测决策。

红线:分级/判型/告警全由国标规则;LLM 只写分析意见人话(Agent B),失败则规则模板降级。
纯算法:输入 DataFrame + 目标日,输出编排结果 dict。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.algorithms.agent.report_b import build_facts_pack, generate_opinion
from app.algorithms.agent.report_card import build_g1_card, build_g2_card
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
    """对指定监测日跑七步编排。

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
    triggers = hit.get("triggers") or []
    indicators = hit.get("indicators") or []
    scope_note = hit.get("scope_note")
    non_fault_tip = hit.get("non_fault_source_tip")

    diagnosis = diagnose_sample(
        grade=grade,
        h2=gases["h2"], ch4=gases["ch4"], c2h4=gases["c2h4"],
        c2h6=gases["c2h6"], c2h2=gases["c2h2"],
        co=co, co2=co2,
        rate_rising=bool(hit.get("rate_rising")),
        is_pre=is_pre,
    )
    fusion = diagnosis.get("fusion") if diagnosis.get("triggered") else None

    sample_dates = _sample_dates(df, idx)

    decision = _decide_c(
        grade=grade, is_pre=is_pre, urgency=urgency, fusion=fusion,
        rate_rising=bool(hit.get("rate_rising")),
    )

    facts = build_facts_pack(
        grade=grade, gases=gases, thc=thc, triggers=triggers,
        is_pre=is_pre, thc_rel=thc_rel, urgency=urgency,
        diagnosis=diagnosis, fusion=fusion, decision=decision,
        scope_note=scope_note, non_fault_tip=non_fault_tip,
    )
    opinion_pack = generate_opinion(facts=facts, force_template=force_template)
    opinion = opinion_pack["text"]
    report_mode = opinion_pack["mode"]

    # 模块5:结论↔依据 id
    detect_cites = cites_for_detect(
        is_pre=is_pre, urgency=urgency,
        scope_exceeded=bool(hit.get("scope_exceeded")),
    )
    diag_cites = cites_for_diagnosis(
        triggered=bool(diagnosis.get("triggered")),
        trigger_by=diagnosis.get("trigger_by"),
        fusion=fusion,
    )
    decide_cites = cites_for_decision(is_pre=is_pre, grade=grade)
    knowledge = {
        "detect": expand(detect_cites),
        "diagnose": expand(diag_cites),
        "decision": expand(decide_cites),
        "report": expand(["722-附录G"]),
    }

    report_no = f"RPT-{day.replace('-', '')}-{day_num:03d}"
    report_log = (
        f"生成 DL/T 722 表 G.1/G.2 · 分析意见已写入({report_mode}) · {report_no}"
        + (f" · {opinion_pack['error']}" if opinion_pack.get("error") else "")
    )

    steps = [
        _step(
            id="input",
            label="时序输入",
            sub="360 天合成时序 · SYN-001",
            tag="detect",
            cite={"id": "722-10.3", "label": "§10.3"},
            log=f"加载虚拟设备 #SYN-001 · 第 {day_num} 采样日 {day} · 7 种特征气体",
            detail={"day": day_num, "date": day, "gases": gases, "total_hydrocarbon": thc},
        ),
        _step(
            id="grade",
            label="四档分级",
            sub="DL/T 1498.2 表 A.3",
            tag="detect",
            cite={"id": "1498-表A3", "label": "表A.3"},
            log=_grade_log(grade, triggers),
            detail={"grade": grade, "indicators": indicators, "triggers": triggers,
                    "cite_ids": detect_cites},
        ),
        _step(
            id="urgency",
            label="处置紧急度",
            sub="产气速率 · §9.3.3",
            tag="detect",
            cite={"id": "722-9.3.3", "label": "§9.3.3"},
            log=_urgency_log(grade, urgency, thc_rel, is_pre),
            detail={"urgency": urgency, "thc_rel_rate": thc_rel, "is_pre": is_pre},
        ),
        _step(
            id="diagnose",
            label="故障类型",
            sub="三比值法 · Duval · 特征气体",
            tag="diag",
            cite={"id": "722-10.3", "label": "§10.3"},
            log=_diag_log(diagnosis, fusion),
            detail={"diagnosis": diagnosis, "cite_ids": diag_cites},
        ),
        _step(
            id="trend",
            label="产气趋势",
            sub="「预」提前预警 · 产气涨势",
            tag="trend",
            cite={"id": "722-9.3.2", "label": "§9.3.2"},
            log=_trend_log(is_pre, thc_rel, urgency),
            detail={"is_pre": is_pre, "thc_rel_rate": thc_rel},
        ),
        _step(
            id="decide",
            label="Agent 决策",
            sub="模块 B 报告 + 模块 C 监测",
            tag="agent",
            cite={"id": "1498-5.4.5", "label": "§5.4.5 / A.3.1"},
            log=decision["log"],
            detail={**decision, "cite_ids": decide_cites, "report_mode": report_mode},
        ),
        _step(
            id="report",
            label="表 G.1/G.2 报告",
            sub="附录 G 档案卡片 · 分析意见",
            tag="report",
            cite={"id": "722-附录G", "label": "附录G"},
            log=report_log,
            detail={"report_no": report_no, "mode": report_mode},
        ),
    ]

    cite_ids = list(dict.fromkeys(
        detect_cites + diag_cites + decide_cites + ["722-附录G"]
    ))
    g1 = build_g1_card(
        df=df,
        idx=idx,
        day=day,
        day_num=day_num,
        sample_dates=sample_dates,
        opinion=opinion,
        report_no=report_no,
        cite_ids=cite_ids,
    )
    g2 = build_g2_card()

    note = (
        "判定全由国标规则完成;Agent B 分析意见="
        + ("LLM 组织人话" if report_mode == "llm" else "规则模板")
        + ";Agent C 监测决策为规则。"
    )
    if opinion_pack.get("error"):
        note += f" ({opinion_pack['error']})"
    if opinion_pack.get("note"):
        note += f" ({opinion_pack['note']})"

    return {
        "date": day,
        "day": day_num,
        "grade": grade,
        "is_pre": is_pre,
        "rate_rising": bool(hit.get("rate_rising")),
        "steps": steps,
        "decision": decision,
        "g1": g1,
        "g2": g2,
        "knowledge": knowledge,
        "mode": report_mode,
        "note": note,
    }


def _step(*, id: str, label: str, sub: str, tag: str, cite: dict, log: str, detail: Any) -> dict:
    return {
        "id": id, "label": label, "sub": sub, "tag": tag,
        "cite": cite, "log": log, "detail": detail,
    }


def _grade_log(grade: str, triggers: list) -> str:
    if not triggers:
        return f"表 A.3 分级 → {grade} · 七项均在正常范围"
    parts = [f"{t.get('basis','')}·{_gas_zh(t.get('gas'))}→{t.get('grade')}" for t in triggers[:5]]
    return f"表 A.3 分级 → {grade} · " + " · ".join(parts)


def _urgency_log(grade: str, urgency: dict | None, thc_rel: float | None, is_pre: bool) -> str:
    rate = f"{thc_rel}%/月" if thc_rel is not None else "—"
    if is_pre:
        return f"档位 {grade} 未达注意值2,但总烃月环比 {rate} 连续超阈 → 「预」· 建议缩短检测周期"
    if urgency:
        return f"处置紧急度 → {urgency['level']} · 总烃月环比 {rate} · {urgency.get('advice','')}"
    return f"档位 {grade} 未达注意值2,暂不启动处置紧急度研判 · 总烃月环比 {rate}"


def _diag_log(diagnosis: dict, fusion: dict | None) -> str:
    if not diagnosis.get("triggered"):
        return diagnosis.get("reason") or "未进判型(档位未达注意值2且速率未连续超注意)"
    if not fusion:
        return "已触发判型但融合无结论"
    code = fusion.get("primary_code") or ""
    conf = fusion.get("confidence") or "—"
    by = diagnosis.get("trigger_note") or ""
    provisional = fusion.get("provisional") or conf == "低"
    stance = "暂定" if provisional else ""
    return (
        f"{stance}{fusion.get('primary')}{' · '+code if code else ''} · 可信度{conf}"
        f" · {fusion.get('confidence_reason','')}"
        + (" · 不作确诊" if provisional else "")
        + (f" · {by}" if by else "")
    )


def _trend_log(is_pre: bool, thc_rel: float | None, urgency: dict | None) -> str:
    rate = f"{thc_rel}%/月" if thc_rel is not None else "—"
    if is_pre:
        return f"总烃相对产气速率 {rate} 连续超 10%/月 → 触发「预」提前预警(§9.3.3 a)"
    if urgency and urgency.get("rising"):
        return f"总烃相对产气速率 {rate} 连续超阈 · 涨势确认"
    return f"总烃相对产气速率 {rate} · 未形成连续超阈涨势"


def _decide_c(
    *,
    grade: str,
    is_pre: bool,
    urgency: dict | None,
    fusion: dict | None,
    rate_rising: bool = False,
) -> dict:
    """Agent C 监测决策 —— 在线口径(1498.2 A.3.1 / §5.4.5 / §5.5.5)。"""
    conf = (fusion or {}).get("confidence")
    measures = list((fusion or {}).get("measures") or [])
    cite_period = "1498-A.3.1"
    cite_resample = "1498-5.4.5"

    # 正常基线 ≤12h;预警确认后快速周期,下限多组分 ≤2h
    if grade in ("正常", "注意值1") and not is_pre and not rate_rising:
        period = "按在线基线周期(≤12h)"
        period_sub = "1498.2 A.3.1 · 220kV 及以下采集周期"
        resample = "不需要"
        resample_sub = "未达预警触发条件"
        log = f"Agent C → {period} · 二次采样：{resample}"
    elif is_pre or (grade == "注意值1" and rate_rising):
        period = "缩短至快速采样周期(下限≤2h)"
        period_sub = "§9.3.3 a「预」+ §5.4.5 / §5.5.5"
        cite_period = "1498-5.5.5"
        resample = "建议二次采样验证"
        resample_sub = "§5.4.5 · 发现预警先验证再缩周期"
        log = f"Agent C → {period} · 二次采样：{resample}"
    else:
        # 注意值2 / 告警值
        if urgency and urgency.get("level") == "低":
            period = "保持基线并加强监视(≤12h)"
            period_sub = "§9.3.3 d 协调 · 仅 H₂ 超且不涨"
            cite_period = "722-9.3.3"
        elif urgency and urgency.get("rising"):
            period = "缩短至快速采样周期(下限≤2h)"
            period_sub = "§5.4.5 确认后快速周期 · §5.5.5 下限"
            cite_period = "1498-5.5.5"
        else:
            period = "缩短采集周期并加强监视(建议逼近≤2h)"
            period_sub = "A.3.1 异常宜缩至最小检测周期"
            cite_period = "1498-A.3.1"

        if conf == "低":
            resample = "建议二次采样验证"
            resample_sub = "§5.4.5 · 可信度低/有分歧先验证"
        else:
            resample = "暂不建议二次采样"
            resample_sub = f"可信度{conf or '—'} · 确认后再调周期"

        trials_note = (
            f" · 核实试验 {len(measures)} 项"
            if measures and conf == "低"
            else (f" · 试验建议 {len(measures)} 项" if measures else "")
        )
        log = f"Agent C → 采集周期 {period} · 二次采样：{resample}{trials_note}"

    measures_purpose = (fusion or {}).get("measures_purpose") or (
        "verify" if conf == "低" else "recommend"
    )

    return {
        "period": period,
        "period_sub": period_sub,
        "resample": resample,
        "resample_sub": resample_sub,
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
    }


def _sample_dates(df: pd.DataFrame, idx: int) -> list[str | None]:
    """表G.1 取样条件四列:当日、约一周前、约两周前、空。"""
    dates = df["date"].astype(str).tolist()
    out: list[str | None] = [dates[idx]]
    for back in (6, 14):
        j = idx - back
        out.append(dates[j] if j >= 0 else None)
    out.append(None)
    return out


def _gas_zh(gas: str | None) -> str:
    return {
        "c2h2": "乙炔", "h2": "氢气", "total_hydrocarbon": "总烃",
        "ch4": "甲烷", "c2h4": "乙烯", "c2h6": "乙烷",
    }.get(gas or "", gas or "—")
