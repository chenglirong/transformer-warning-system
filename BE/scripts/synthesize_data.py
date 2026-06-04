"""驱动脚本:读 labeled_iec.csv,合成时序数据,输出 synthetic_timeseries.csv。

用法:
    cd BE
    python -m scripts.synthesize_data

可选参数:
    --n-transformers N     虚拟变压器数量(默认 50)
    --n-days N             每台天数(默认 90)
    --seed N               随机种子(默认 42,保证可复现)
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.algorithms.synthesis import (  # noqa: E402
    GAS_KEYS, SynthConfig, synthesize, build_state_pools,
    DEFAULT_N_TRANSFORMERS, DEFAULT_N_DAYS, DEFAULT_START_DATE,
)


INPUT_CSV = ROOT.parent / "data" / "labeled_iec.csv"
OUTPUT_CSV = ROOT.parent / "data" / "synthetic_timeseries.csv"

GAS_NUM_COLS = ["h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2"]


def section(title: str):
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")


def load_labeled() -> list[dict]:
    """读 labeled_iec.csv 为 list[dict],气体列转为 float|None。"""
    rows = []
    with INPUT_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            for col in GAS_NUM_COLS:
                v = r.get(col, "")
                r[col] = float(v) if v not in ("", None) else None
            rows.append(r)
    return rows


def report_pools(pools):
    section("分布池统计(对数空间均值,反映各 IEC 状态的气体水平)")
    print(f"  {'状态':<35s}{'n':>5s}" + "".join(f"{g:>10s}" for g in GAS_KEYS))
    print("  " + "-" * (40 + 10 * len(GAS_KEYS)))
    for state, pool in sorted(pools.items(), key=lambda x: -x[1].n_samples):
        # 反对数显示给人类读
        means = [10 ** pool.log_mu[g] - 1 for g in GAS_KEYS]
        print(f"  {state:<35s}{pool.n_samples:>5d}" +
              "".join(f"{m:>10.1f}" for m in means))


def report_synthesized(rows: list[dict]):
    section("合成结果概览")
    print(f"  总行数: {len(rows)}")
    n_tx = len({r['transformer_id'] for r in rows})
    print(f"  变压器数: {n_tx}")
    days_per = len(rows) // n_tx
    print(f"  每台天数: {days_per}")
    print(f"  日期范围: {rows[0]['date']} → {rows[-1]['date']}")

    section("合成数据中各 fault_state 占比")
    counter = Counter(r["fault_state"] for r in rows)
    for state, count in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"  {state:<35s}: {count:5d} ({count/len(rows)*100:5.1f}%)")

    section("气体浓度统计(合成 vs 真实分布对比)")
    print(f"  {'气体':<8s}{'min':>10s}{'max':>12s}{'mean':>10s}{'median':>10s}")
    for gas in GAS_KEYS:
        vals = sorted(r[gas] for r in rows)
        med = vals[len(vals) // 2]
        print(f"  {gas:<8s}{min(vals):>10.2f}{max(vals):>12.2f}"
              f"{mean(vals):>10.2f}{med:>10.2f}")
    print("  💡 与 EDA 真实分布对照(论文素材):")
    print("     真实 H2 mean=348 max=23349,合成应在该量级范围内")

    section("工况统计")
    print(f"  {'指标':<14s}{'min':>10s}{'max':>10s}{'mean':>10s}")
    for col in ["oil_temp", "load_current", "ambient_temp"]:
        vals = [r[col] for r in rows]
        print(f"  {col:<14s}{min(vals):>10.2f}{max(vals):>10.2f}{mean(vals):>10.2f}")

    # 健康/异常天数比例
    section("健康天数 vs 异常天数")
    healthy = sum(1 for r in rows if r["fault_state"] == "Normal")
    abnormal = len(rows) - healthy
    print(f"  健康: {healthy} ({healthy/len(rows)*100:.1f}%)")
    print(f"  异常: {abnormal} ({abnormal/len(rows)*100:.1f}%)")
    print("  💡 设计目标:健康天数占 70-85%,体现真实运维场景")


def save(rows: list[dict]):
    section("保存合成数据集")
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "transformer_id", "date",
        "h2", "ch4", "c2h4", "c2h6", "c2h2", "co", "co2",
        "oil_temp", "load_current", "ambient_temp",
        "fault_state",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})
    print(f"  ✅ {OUTPUT_CSV}")
    print(f"     {len(rows)} 行 × {len(cols)} 列")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-transformers", type=int, default=DEFAULT_N_TRANSFORMERS)
    p.add_argument("--n-days", type=int, default=DEFAULT_N_DAYS)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    section(f"读取 labeled_iec.csv")
    labeled = load_labeled()
    print(f"  读入 {len(labeled)} 行")

    pools = build_state_pools(labeled)
    report_pools(pools)

    cfg = SynthConfig(
        n_transformers=args.n_transformers,
        n_days=args.n_days,
        start_date=DEFAULT_START_DATE,
        seed=args.seed,
    )
    section(f"开始合成({cfg.n_transformers} 台 × {cfg.n_days} 天, seed={cfg.seed})")
    rows = synthesize(labeled, cfg)
    print(f"  ✅ 已生成 {len(rows)} 行")

    report_synthesized(rows)
    save(rows)

    section("合成完成")
    print("  → 后续:scripts.import_data 把 CSV 入库 SQLite")


if __name__ == "__main__":
    main()
