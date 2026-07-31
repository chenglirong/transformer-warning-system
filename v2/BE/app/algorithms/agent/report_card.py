"""表 G.1 / G.2 报告字段装配(DL/T 722 附录G)。

有值如实填;演示台账可填铭牌区,合成缺的工况/O₂·N₂/含气量%仍填 None→「—」。
绝对产气速率式1缺油密度,不杜撰 → 仍「—」。变压器台账来自 transformers 表。
"""
from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

# 前端识别:空字段统一用 None →「—」;带说明用 dict {"value": None, "note": "..."}
NA = None
EMPTY = "—"  # 仅文档约定;API 传 null


def _np_field(transformer: dict | None, key: str, default=None):
    """从变压器台账取值;无台账或字段为 None 则返回 default。"""
    if not transformer:
        return default
    return transformer.get(key) or default


def build_g1_card(
    *,
    df: pd.DataFrame,
    idx: int,
    day: str,
    day_num: int,
    sample_dates: list[Optional[str]],
    opinion: str,
    report_no: str,
    device_id: str = "SYN-001",
    voltage: str = "220kV及以下(前提声明)",
    cite_ids: list[str] | None = None,
    cite_map: list[dict] | None = None,
    transformer: dict | None = None,
) -> dict[str, Any]:
    """装配表G.1完整字段。sample_dates 长度=4(当日 / 约−7 / 约−14 / 约−21 天)。

    transformer: transformers 表查询结果(dict),无则铭牌等字段用 None 占位。
    只取 G.1 铭牌区原有字段,不加非 G.1 内容。
    """
    t = transformer  # 缩写

    # 合成电压等级/容量:优先用台账 voltage_capacity,其次用 voltage 参数
    voltage_capacity = _np_field(t, "voltage_capacity") or voltage
    serial_no = _np_field(t, "serial_no") or device_id

    gases = {
        "h2": _cols(df, sample_dates, "h2"),
        "o2": [None] * 4,  # 数据集不含
        "n2": [None] * 4,
        "co": _cols(df, sample_dates, "co"),
        "co2": _cols(df, sample_dates, "co2"),
        "ch4": _cols(df, sample_dates, "ch4"),
        "c2h4": _cols(df, sample_dates, "c2h4"),
        "c2h6": _cols(df, sample_dates, "c2h6"),
        "c2h2": _cols(df, sample_dates, "c2h2"),
        "thc": [_thc(df, d) for d in sample_dates],
    }

    # 总烃增长:相对「更早一次」取样的差值(列0相对列1,列1相对列2…)
    thc_growth: list[Optional[float]] = []
    for i, thc in enumerate(gases["thc"]):
        if i + 1 >= len(gases["thc"]) or thc is None or gases["thc"][i + 1] is None:
            thc_growth.append(None)
        else:
            thc_growth.append(round(thc - gases["thc"][i + 1], 2))

    # 实际运行时间(天):相邻取样间隔
    run_days: list[Optional[int]] = []
    for i, d in enumerate(sample_dates):
        if i + 1 >= len(sample_dates) or not d or not sample_dates[i + 1]:
            run_days.append(None)
        else:
            run_days.append(_day_delta(sample_dates[i + 1], d))

    # 铭牌注:有台账数据时去掉"演示"提示
    has_np = bool(t and any(t.get(k) for k in (
        "model", "manufacturer", "oil_weight_t", "oil_type",
        "manufacture_date", "commission_date", "cooling",
        "tap_changer", "oil_protection",
    )))
    nameplate_note = None if has_np else "演示设备，铭牌字段取可声明项，其余留空"

    return {
        "report_no": report_no,
        "bureau": _np_field(t, "bureau"),
        "nameplate": {
            "model": _np_field(t, "model"),
            "voltage_capacity": voltage_capacity,
            "oil_weight_t": _np_field(t, "oil_weight_t"),
            "oil_type": _np_field(t, "oil_type"),
            "manufacturer": _np_field(t, "manufacturer"),
            "serial_no": serial_no,
            "manufacture_date": _np_field(t, "manufacture_date"),
            "commission_date": _np_field(t, "commission_date"),
            "cooling": _np_field(t, "cooling"),
            "tap_changer": _np_field(t, "tap_changer"),
            "oil_protection": _np_field(t, "oil_protection"),
            "nameplate_note": nameplate_note,
        },
        "sample": {
            "dates": sample_dates,  # 年、月、日、时 → 合成仅有日
            "reason": [None, None, None, None],
            "site": [None, None, None, None],
            "oil_temp_c": [None, None, None, None],
            "load_mva": [None, None, None, None],
            "sample_note": "演示时序无取样原因/部位/油温/负荷",
        },
        "gas_content_pct": [None, None, None, None],  # 含气量%
        "gases": gases,
        "thc_growth": thc_growth,
        "run_days": run_days,
        # 绝对产气速率式1需油重+密度;台账有油重仍缺密度 →「—」,相对速率写分析意见
        "thc_gassing_rate_ml_d": [None, None, None, None],
        "thc_gassing_rate_note": None,
        "test_report_nos": [report_no, None, None, None],
        "opinion": opinion,
        "empty_note": None,
        "cite_ids": cite_ids or [],
        "cite_map": cite_map or [],
        "device_id": serial_no,
        "voltage": voltage_capacity,
        "sample_dates": sample_dates,  # 兼容旧前端字段
        "day": day,
        "day_num": day_num,
    }


def build_other_tests_blocks(
    *,
    trials: list[str] | None = None,
    trials_appendix_d: list[str] | None = None,
    trials_1685_items: list[dict] | None = None,
    trials_basis: list[dict] | None = None,
    trials_nature: str | None = None,
    trials_purpose: str | None = None,
) -> list[dict[str, Any]]:
    """与监测决策同款：当前状态 / 依据 / 建议试验 结构化块。"""
    nature = (trials_nature or "").strip() or "—"
    verify = trials_purpose == "verify"
    basis_d = next(
        (
            b for b in (trials_basis or [])
            if b.get("cite") == "722-附录D" or b.get("label") == "附录D"
        ),
        None,
    )
    status = ""
    if basis_d and basis_d.get("status"):
        status = str(basis_d["status"]).replace("当前状况：", "", 1).strip()
    if not status:
        status = f"故障性质暂定为「{nature}」" if verify else f"故障性质为「{nature}」"

    d_names = [
        str(t).strip()
        for t in (trials_appendix_d or [])
        if t and str(t).strip()
    ]
    if not d_names:
        d_names = [
            str(t).strip()
            for t in (trials or [])
            if t and str(t).strip() and "(B." not in str(t)
        ]

    blocks: list[dict[str, Any]] = []
    if d_names:
        blocks.append({
            "status": status,
            "cite": "722-附录D",
            "cite_label": "722-附录D",
            "table_hint": f"表D.1「{nature}」列",
            "items": d_names,
            "suggest": None,
            "badge": None,
        })

    for it in trials_1685_items or []:
        clause = str(it.get("clause") or "").strip()
        test = str(it.get("test") or "").strip()
        if clause:
            test = test.replace(f"({clause})", "").strip()
        test = re.sub(r"\(B\.[^)]+\)", "", test).strip()
        m = re.match(r"^(B\.\d+)", clause, re.I)
        table_hint = f"表{m.group(1)}" if m else ""
        blocks.append({
            "status": it.get("why") or "当日气体组合贴近附录B状态量描述",
            "cite": "1685-附录B",
            "cite_label": "1685-附录B",
            "table_hint": table_hint,
            "items": None,
            "suggest": test,
            "badge": clause or None,
        })
    return blocks


def _blocks_to_plain(blocks: list[dict[str, Any]]) -> str | None:
    """纯文本兜底(导出/旧前端)。"""
    if not blocks:
        return None
    parts: list[str] = []
    for b in blocks:
        lines = [f"当前状态：{b.get('status') or '—'}"]
        cite = b.get("cite_label") or b.get("cite") or ""
        hint = b.get("table_hint") or ""
        lines.append(f"依据：{cite}" + (f" {hint}" if hint else ""))
        items = b.get("items") or []
        if items:
            lines.append("建议试验：" + "；".join(items))
        elif b.get("suggest"):
            badge = b.get("badge") or ""
            lines.append("建议试验：" + (f"[{badge}] " if badge else "") + str(b["suggest"]))
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def build_g2_card(
    *,
    other_tests: str | None = None,
    trials: list[str] | None = None,
    trials_appendix_d: list[str] | None = None,
    trials_1685_items: list[dict] | None = None,
    trials_basis: list[dict] | None = None,
    trials_purpose: str | None = None,
    trials_nature: str | None = None,
    grade: str | None = None,  # noqa: ARG001
    confidence: str | None = None,  # noqa: ARG001
    provisional: bool = False,  # noqa: ARG001
) -> dict[str, Any]:
    """表G.2:报告栏用文书成稿;结构化块仅供监测决策展示。"""
    blocks = build_other_tests_blocks(
        trials=trials,
        trials_appendix_d=trials_appendix_d,
        trials_1685_items=trials_1685_items,
        trials_basis=trials_basis,
        trials_nature=trials_nature,
        trials_purpose=trials_purpose,
    )
    text = (other_tests or "").strip() or _blocks_to_plain(blocks)
    return {
        "other_tests": text or None,
        "other_tests_blocks": blocks,
        "maintenance": None,
        "fault_records": None,
        "note": None,
    }


def _cols(df: pd.DataFrame, sample_dates: list, gas: str) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    for d in sample_dates:
        if not d or gas not in df.columns:
            out.append(None)
            continue
        hits = df.index[df["date"].astype(str) == d].tolist()
        if not hits:
            out.append(None)
            continue
        v = df.iloc[int(hits[0])][gas]
        out.append(None if pd.isna(v) else round(float(v), 2))
    return out


def _thc(df: pd.DataFrame, day: Optional[str]) -> Optional[float]:
    if not day:
        return None
    hits = df.index[df["date"].astype(str) == day].tolist()
    if not hits:
        return None
    row = df.iloc[int(hits[0])]
    return round(
        float(row["ch4"]) + float(row["c2h4"]) + float(row["c2h6"]) + float(row["c2h2"]),
        2,
    )


def _day_delta(earlier: str, later: str) -> Optional[int]:
    try:
        a = pd.Timestamp(earlier)
        b = pd.Timestamp(later)
        return int((b - a).days)
    except Exception:  # noqa: BLE001
        return None
