"""Agent 编排 —— 串检测/判型/趋势,产出步骤日志+依据+表G.1+监测决策。

LLM 不下判定(红线);本版分析意见/决策用规则模板(降级路径可跑通)。
纯算法:输入 DataFrame + 目标日,输出编排结果 dict。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.algorithms.detect.grade import detect
from app.algorithms.diagnose.pipeline import can_diagnose, diagnose_sample

GAS_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2"]


def run_agent(df: pd.DataFrame, day: str) -> dict[str, Any]:
    """对指定监测日跑七步编排。"""
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
    thc = hit["total_hydrocarbon"]
    grade = hit["grade"]
    is_pre = bool(hit.get("is_pre"))
    urgency = hit.get("urgency")
    thc_rel = hit.get("thc_rel_rate")
    triggers = hit.get("triggers") or []
    indicators = hit.get("indicators") or []

    diagnosis = diagnose_sample(
        grade=grade,
        h2=gases["h2"], ch4=gases["ch4"], c2h4=gases["c2h4"],
        c2h6=gases["c2h6"], c2h2=gases["c2h2"],
        co=co, co2=co2,
    )
    fusion = diagnosis.get("fusion") if diagnosis.get("triggered") else None

    # 近窗取样日(表G.1 多列):当日 / −6 / −14(有则填)
    sample_dates = _sample_dates(df, idx)

    decision = _decide_c(grade=grade, is_pre=is_pre, urgency=urgency, fusion=fusion)
    opinion = _build_opinion(
        grade=grade, gases=gases, thc=thc, triggers=triggers,
        is_pre=is_pre, thc_rel=thc_rel, urgency=urgency,
        diagnosis=diagnosis, fusion=fusion, decision=decision,
    )
    report_no = f"RPT-{day.replace('-', '')}-{day_num:03d}"

    steps = [
        _step(
            id="input",
            label="时序输入",
            sub="360 天合成时序 · SYN-001",
            tag="detect",
            cite={"id": "722-10.3", "label": "§10.3"},
            log=f"加载虚拟设备 #SYN-001 · 第 {day_num} 采样日 {day} · 5 主烃类完整",
            detail={"day": day_num, "date": day, "gases": gases, "total_hydrocarbon": thc},
        ),
        _step(
            id="grade",
            label="四档分级",
            sub="DL/T 1498.2 表 A.3",
            tag="detect",
            cite={"id": "1498-表A3", "label": "表A.3"},
            log=_grade_log(grade, triggers),
            detail={"grade": grade, "indicators": indicators, "triggers": triggers},
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
            detail={"diagnosis": diagnosis},
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
            cite={"id": "722-5.4", "label": "§5.4 / §5.4.5"},
            log=decision["log"],
            detail=decision,
        ),
        _step(
            id="report",
            label="表 G.1 报告",
            sub="附录 G 档案卡片 · 分析意见",
            tag="report",
            cite={"id": "722-附录G", "label": "附录G 表G.1"},
            log=f"生成 DL/T 722 表 G.1 档案卡片 · 分析意见已写入 · {report_no}",
            detail={"report_no": report_no},
        ),
    ]

    g1 = {
        "report_no": report_no,
        "device_id": "SYN-001",
        "voltage": "220kV 及以下",
        "sample_dates": sample_dates,
        "gases": {
            "h2": _gas_cols(df, idx, "h2", sample_dates),
            "ch4": _gas_cols(df, idx, "ch4", sample_dates),
            "c2h4": _gas_cols(df, idx, "c2h4", sample_dates),
            "c2h6": _gas_cols(df, idx, "c2h6", sample_dates),
            "c2h2": _gas_cols(df, idx, "c2h2", sample_dates),
            "co": _gas_cols(df, idx, "co", sample_dates) if "co" in df.columns else [None] * 4,
            "co2": _gas_cols(df, idx, "co2", sample_dates) if "co2" in df.columns else [None] * 4,
            "thc": [
                _thc_at(df, _date_to_idx(df, d)) if d else None
                for d in sample_dates
            ],
        },
        "opinion": opinion,
        "empty_note": "合成虚拟设备无铭牌/油重/油温等工况字段,如实留空",
    }

    return {
        "date": day,
        "day": day_num,
        "grade": grade,
        "is_pre": is_pre,
        "steps": steps,
        "decision": decision,
        "g1": g1,
        "mode": "rule_template",  # LLM 降级
        "note": "判定全由国标规则完成;分析意见与监测决策为本版规则模板(Agent B/C 降级路径)",
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
        return diagnosis.get("reason") or "未达注意值2,按 §10.3 / §10.2.4 a 不判型"
    if not fusion:
        return "已触发判型但融合无结论"
    code = fusion.get("primary_code") or ""
    conf = fusion.get("confidence") or "—"
    return (
        f"{fusion.get('primary')}{' · '+code if code else ''} · 可信度{conf}"
        f" · {fusion.get('confidence_reason','')}"
    )


def _trend_log(is_pre: bool, thc_rel: float | None, urgency: dict | None) -> str:
    rate = f"{thc_rel}%/月" if thc_rel is not None else "—"
    if is_pre:
        return f"总烃相对产气速率 {rate} 连续超 10%/月 → 触发「预」提前预警(§9.3.3 a)"
    if urgency and urgency.get("rising"):
        return f"总烃相对产气速率 {rate} 连续超阈 · 涨势确认"
    return f"总烃相对产气速率 {rate} · 未形成连续超阈涨势"


def _decide_c(*, grade: str, is_pre: bool, urgency: dict | None, fusion: dict | None) -> dict:
    """Agent C 监测决策(规则模板)。"""
    nature = (fusion or {}).get("nature")
    conf = (fusion or {}).get("confidence")
    measures = list((fusion or {}).get("measures") or [])
    cite_period = "722-5.4"
    cite_resample = "722-5.4.5"

    if grade in ("正常", "注意值1"):
        if is_pre:
            period = "缩短检测周期（建议每周）"
            period_sub = "§9.3.3 a · 「预」缩周期"
            cite_period = "722-9.3.3"
        else:
            period = "按表1正常周期"
            period_sub = "§5.3 表1 · 默认监测周期"
        resample = "不需要"
        resample_sub = "未达注意值2 经典线"
        log = f"Agent C → {period} · 二次采样：{resample}"
    else:
        if nature == "discharge":
            period = "每天一次"
            period_sub = "§5.4 b · 放电类缩短至天"
        elif nature == "thermal":
            period = "每周一次"
            period_sub = "§5.4 b · 过热类缩短至周"
        elif urgency and urgency.get("rising"):
            period = "缩短检测周期（建议每周）"
            period_sub = "§9.3.3 a · 涨势快"
            cite_period = "722-9.3.3"
        else:
            period = "加强监视（可暂不缩周期）"
            period_sub = "§9.3.3 a · 超标但暂稳"

        if conf == "低":
            resample = "建议二次采样验证"
            resample_sub = "§5.4.5 · 可信度低/有分歧先验证"
        else:
            resample = "暂不建议二次采样"
            resample_sub = f"可信度{conf or '—'} · 确认后再调周期"

        log = (
            f"Agent C → 检测周期 {period} · 二次采样：{resample}"
            + (f" · 附录D 试验 {len(measures)} 项" if measures else "")
        )

    return {
        "period": period,
        "period_sub": period_sub,
        "resample": resample,
        "resample_sub": resample_sub,
        "trials": measures,
        "cite_period": cite_period,
        "cite_resample": cite_resample,
        "log": log,
    }


def _build_opinion(*, grade, gases, thc, triggers, is_pre, thc_rel, urgency, diagnosis, fusion, decision) -> str:
    parts = [f"【告警级别】{grade}。"]
    if triggers:
        hit_txt = "、".join(
            f"{_gas_zh(t.get('gas'))}({t.get('basis')})→{t.get('grade')}" for t in triggers[:6]
        )
        parts.append(f"超标判据：{hit_txt}。")
    else:
        parts.append("表 A.3 七项均在正常范围。")

    rate = f"{thc_rel}%/月" if thc_rel is not None else "—"
    if is_pre:
        parts.append(f"【趋势】总烃月环比 {rate} 连续超阈，触发「预」提前预警。")
    elif urgency:
        parts.append(f"【趋势】总烃月环比 {rate}；处置紧急度 {urgency.get('level')}。{urgency.get('advice','')}")
    else:
        parts.append(f"【趋势】总烃月环比 {rate}。")

    if fusion:
        code = fusion.get("primary_code") or ""
        parts.append(
            f"【故障类型】{fusion.get('primary')}"
            + (f"（{code}）" if code else "")
            + f"；可信度{fusion.get('confidence')}（{fusion.get('confidence_reason','')}）。"
        )
    elif not diagnosis.get("triggered"):
        parts.append("【故障类型】未触发（§10.3：未达注意值2不判型）。")

    parts.append(
        f"【处置建议】检测周期：{decision['period']}；二次采样：{decision['resample']}。"
    )
    if decision.get("trials"):
        parts.append("附录 D 建议试验：" + "、".join(decision["trials"]) + "。")
    parts.append("（本意见由规则模板组织；判定本身全部来自国标规则，非 LLM 下判。）")
    return "".join(parts)


def _sample_dates(df: pd.DataFrame, idx: int) -> list[str | None]:
    """表G.1 取样条件四列:当日、约一周前、约两周前、空。"""
    dates = df["date"].astype(str).tolist()
    out: list[str | None] = [dates[idx]]
    for back in (6, 14):
        j = idx - back
        out.append(dates[j] if j >= 0 else None)
    out.append(None)
    return out


def _date_to_idx(df: pd.DataFrame, day: str | None) -> int | None:
    if not day:
        return None
    hits = df.index[df["date"].astype(str) == day].tolist()
    return int(hits[0]) if hits else None


def _gas_cols(df: pd.DataFrame, idx: int, gas: str, sample_dates: list) -> list:
    out = []
    for d in sample_dates:
        if d is None:
            out.append(None)
            continue
        j = _date_to_idx(df, d)
        if j is None or gas not in df.columns or pd.isna(df.iloc[j][gas]):
            out.append(None)
        else:
            out.append(round(float(df.iloc[j][gas]), 2))
    return out


def _thc_at(df: pd.DataFrame, j: int | None) -> float | None:
    if j is None:
        return None
    row = df.iloc[j]
    return round(float(row["ch4"]) + float(row["c2h4"]) + float(row["c2h6"]) + float(row["c2h2"]), 2)


def _gas_zh(gas: str | None) -> str:
    return {
        "c2h2": "乙炔", "h2": "氢气", "total_hydrocarbon": "总烃",
        "ch4": "甲烷", "c2h4": "乙烯", "c2h6": "乙烷",
    }.get(gas or "", gas or "—")
