"""表 G.1 / G.2 报告字段装配(DL/T 722 附录G)。

有值如实填,合成缺字段填 NA 哨兵(前端渲染「—」),不杜撰铭牌/工况/台账。
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

# 前端识别:空字段统一用 None →「—」;带说明用 dict {"value": None, "note": "..."}
NA = None
EMPTY = "—"  # 仅文档约定;API 传 null


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
) -> dict[str, Any]:
    """装配表G.1完整字段。sample_dates 长度=4(当日/约-6/约-14/第四列占位)。"""
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

    return {
        "report_no": report_no,
        "bureau": None,  # 局(厂、所)
        "nameplate": {
            "model": None,
            "voltage_capacity": voltage,
            "oil_weight_t": None,
            "oil_type": None,
            "manufacturer": None,
            "serial_no": device_id,
            "manufacture_date": None,
            "commission_date": None,
            "cooling": None,
            "tap_changer": None,
            "oil_protection": None,
            "nameplate_note": "合成虚拟设备,无铭牌——电压等级为声明前提,出厂序号用合成设备号",
        },
        "sample": {
            "dates": sample_dates,  # 年、月、日、时 → 合成仅有日
            "reason": [None, None, None, None],
            "site": [None, None, None, None],
            "oil_temp_c": [None, None, None, None],
            "load_mva": [None, None, None, None],
            "sample_note": "合成数据无取样原因/部位/油温/负荷",
        },
        "gas_content_pct": [None, None, None, None],  # 含气量%
        "gases": gases,
        "thc_growth": thc_growth,
        "run_days": run_days,
        # 绝对产气率式1需油重/密度 → 不用;相对速率写在分析意见里
        "thc_gassing_rate_ml_d": [None, None, None, None],
        "thc_gassing_rate_note": "绝对产气率(mL/天)需油重/油密度,本系统用 722 式2相对产气率(%/月),见分析意见",
        "test_report_nos": [report_no, None, None, None],
        "opinion": opinion,
        "empty_note": "合成虚拟设备:铭牌/工况/含气量%/O₂/N₂/绝对产气率如实留空,不杜撰",
        "cite_ids": cite_ids or [],
        "device_id": device_id,
        "voltage": voltage,
        "sample_dates": sample_dates,  # 兼容旧前端字段
        "day": day,
        "day_num": day_num,
    }


def build_g2_card() -> dict[str, Any]:
    """表G.2:台账类,合成环境无真实记录 → 三栏均留空并注明。"""
    note = "合成环境无真实台账,本栏留空不杜撰(P1)"
    return {
        "other_tests": None,
        "maintenance": None,
        "fault_records": None,
        "note": note,
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
