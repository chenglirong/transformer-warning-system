"""驱动脚本:对合成时序数据构建特征,输出 featured CSV。

用法:
    cd BE
    python -m scripts.build_features

产出:
    data/featured_timeseries.csv —— 原始列 + 48 个特征列,供 LSTM/检测/决策复用
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from app.algorithms.features import build_features, feature_columns  # noqa: E402


INPUT_CSV = ROOT.parent / "data" / "synthetic_timeseries.csv"
OUTPUT_CSV = ROOT.parent / "data" / "featured_timeseries.csv"


def section(title: str):
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")


def main():
    section("读取合成数据")
    df = pd.read_csv(INPUT_CSV)
    print(f"  {df.shape[0]} 行 × {df.shape[1]} 列")

    section("构建特征")
    feat = build_features(df)
    new_cols = feature_columns()
    print(f"  原始列: {df.shape[1]}")
    print(f"  特征列: {len(new_cols)}")
    print(f"  合计: {feat.shape[1]} 列")
    print("\n  特征分类:")
    print("    基础衍生(总烃+3比值): 4")
    print("    滑窗统计(7气体×4指标): 28")
    print("    变化率(7气体×2 + 油温 + 总烃): 16")

    section("保存")
    feat.to_csv(OUTPUT_CSV, index=False)
    print(f"  ✅ {OUTPUT_CSV}")
    print(f"     {feat.shape[0]} 行 × {feat.shape[1]} 列")

    section("完成")
    print("  → 后续:LSTM(模块4)/异常检测(模块3)直接读此 CSV")


if __name__ == "__main__":
    main()
