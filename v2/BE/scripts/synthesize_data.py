"""合成 DGA 时序 → data/synthetic_timeseries.csv(阶段0 数据地基)。

跑法(在 v2/BE 下,模块方式):
    .venv/bin/python -m scripts.synthesize_data

读 data/raw/FinalDataSet_DGA.xlsx → 算真实锚点 → 合成单台×360天 → 落 CSV,
并打印摘要供人工核验(健康/异常比、各气体量级、异常事件时段)。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.algorithms.synthesis import (
    GAS_KEYS,
    HYDROCARBONS,
    NORMAL,
    SynthConfig,
    synthesize,
)

# v2/BE/scripts/ → v2/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_XLSX = PROJECT_ROOT / "data" / "raw" / "FinalDataSet_DGA.xlsx"
OUT_CSV = PROJECT_ROOT / "data" / "synthetic_timeseries.csv"


def main() -> None:
    if not RAW_XLSX.exists():
        raise FileNotFoundError(f"原始数据不存在:{RAW_XLSX}")

    raw = pd.read_excel(RAW_XLSX)
    df = synthesize(raw, SynthConfig())

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)

    # ---- 摘要(人工核验) ----
    n = len(df)
    n_normal = int((df["fault_state"] == NORMAL).sum())
    print(f"[OK] 合成 {n} 天 → {OUT_CSV}")
    print(f"     日期:{df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"     健康 {n_normal} 天 ({n_normal/n:.1%}) / 异常 {n-n_normal} 天 ({(n-n_normal)/n:.1%})")
    print("     状态分布:")
    for state, cnt in df["fault_state"].value_counts().items():
        print(f"       {state}: {cnt} 天")
    print("     各气体 mean/max (μL/L):")
    for g in GAS_KEYS:
        print(f"       {g}: mean={df[g].mean():.1f} max={df[g].max():.1f}")

    # 异常事件时段(连续同状态段)
    print("     异常事件时段:")
    seg_state = None
    seg_start = None
    for i, row in df.iterrows():
        st = row["fault_state"]
        if st != seg_state:
            if seg_state is not None and seg_state != NORMAL:
                print(f"       {df['date'].iloc[seg_start]} ~ {df['date'].iloc[i-1]}  {seg_state}")
            seg_state, seg_start = st, i
    if seg_state is not None and seg_state != NORMAL:
        print(f"       {df['date'].iloc[seg_start]} ~ {df['date'].iloc[n-1]}  {seg_state}")


if __name__ == "__main__":
    main()
