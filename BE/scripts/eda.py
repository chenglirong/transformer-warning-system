"""EDA 脚本:数据集探索 + IEC 自动打标。

用法:
    cd BE
    python -m scripts.eda

产出:
    - 控制台报告(各列缺失率、Fault 分布、IEC 自动诊断分布)
    - data/labeled_iec.csv:743 行 + IEC 自动诊断标签
    - notebooks/figures/*.png(若已装 matplotlib)

设计取舍:
    用纯 stdlib + openpyxl 能跑通最关键的部分(扫描 + 自动打标),
    可视化部分仅在 matplotlib 可用时执行。EDA 不依赖 pandas,
    避免被依赖安装阻塞。
"""
from __future__ import annotations

import sys
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev, median

# 让脚本能 import app.*
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.algorithms.detect.iec import diagnose, IECDiagnosis  # noqa: E402


DATA_XLSX = ROOT.parent / "data" / "raw" / "FinalDataSet_DGA.xlsx"
OUT_CSV = ROOT.parent / "data" / "labeled_iec.csv"
FIG_DIR = ROOT.parent / "notebooks" / "figures"

GAS_COLS = [
    "Hydrogen (H2)", "Methane (CH4)", "Ethylene (C2H4)",
    "Ethane (C2H6)", "Acetylene (C2H2)",
    "Carbon Monoxide (CO)", "Carbon Dioxide (CO2)",
]


def section(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def load_rows():
    """读 xlsx,返回 (header, rows)。

    清洗:把原始数据中的 '-'、'na'、'NA'、'' 字符串占位统一视为 None,
    避免下游(合成器、特征工程)在数值列上踩字符串雷。
    Fault 列的 'NA' 是有效字符串(代表"未标注"),保留。
    """
    import openpyxl
    wb = openpyxl.load_workbook(DATA_XLSX, read_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    header = list(all_rows[0])
    fault_idx = header.index("Fault") if "Fault" in header else -1
    missing_tokens = {"-", "", "na", "n/a"}

    cleaned = []
    for raw in all_rows[1:]:
        row = list(raw)
        for i, v in enumerate(row):
            if i == fault_idx:
                continue  # Fault 列保留原字符串
            if isinstance(v, str) and v.strip().lower() in missing_tokens:
                row[i] = None
        cleaned.append(row)
    return header, cleaned


def report_missing(header, rows):
    section("1. 各列缺失值统计")
    print(f"  数据行数: {len(rows)}")
    for i, col in enumerate(header):
        none_count = sum(1 for r in rows if r[i] is None)
        rate = none_count / len(rows) * 100
        marker = " 🔴" if rate >= 50 else (" ⚠️" if rate >= 20 else "")
        print(f"  {col:30s}: None={none_count:4d} ({rate:5.1f}%){marker}")


def report_fault_dist(header, rows):
    section("2. 原始 Fault 标签分布")
    idx = header.index("Fault")
    counter = Counter(r[idx] for r in rows)
    for k, v in counter.most_common():
        print(f"  {k!r:25s}: {v:4d} ({v/len(rows)*100:5.1f}%)")
    print("\n  ⚠️ 'NA' 占比过高 → Fault 列不可作为可靠 ground truth")
    print("     → 改用 IEC 自动打标(见下文第 4 节)")


def report_gas_stats(header, rows):
    section("3. 7 种 DGA 气体数值分布")
    print(f"  {'气体':<28s}{'min':>10s}{'max':>12s}{'mean':>12s}{'median':>12s}{'std':>14s}")
    print("  " + "-" * 78)
    for gas in GAS_COLS:
        idx = header.index(gas)
        vals = [r[idx] for r in rows if r[idx] is not None and isinstance(r[idx], (int, float))]
        if not vals:
            continue
        std = stdev(vals) if len(vals) > 1 else 0
        print(f"  {gas:<28s}{min(vals):>10.2f}{max(vals):>12.2f}"
              f"{mean(vals):>12.2f}{median(vals):>12.2f}{std:>14.2f}")
    print("\n  💡 长尾分布:max 远大于 mean+3*std,合成时序时建议对数空间扰动")


def apply_iec_labeling(header, rows):
    """对每行应用 IEC 三比值法,返回 (rows, diagnoses)。"""
    section("4. IEC 三比值法自动打标")
    idx = {gas: header.index(gas) for gas in [
        "Hydrogen (H2)", "Methane (CH4)", "Ethylene (C2H4)",
        "Ethane (C2H6)", "Acetylene (C2H2)",
    ]}
    diagnoses = []
    for r in rows:
        d = diagnose(
            h2=r[idx["Hydrogen (H2)"]],
            ch4=r[idx["Methane (CH4)"]],
            c2h4=r[idx["Ethylene (C2H4)"]],
            c2h6=r[idx["Ethane (C2H6)"]],
            c2h2=r[idx["Acetylene (C2H2)"]],
        )
        diagnoses.append(d)

    counter = Counter(d.fault for d in diagnoses)
    print(f"  IEC 自动诊断结果分布(n={len(diagnoses)}):")
    for fault, count in sorted(counter.items(), key=lambda x: -x[1]):
        print(f"    {fault:<35s}: {count:4d} ({count/len(diagnoses)*100:5.1f}%)")

    abn = sum(1 for d in diagnoses if d.is_abnormal)
    print(f"\n  异常样本数: {abn} ({abn/len(diagnoses)*100:.1f}%)")
    print(f"  正常样本数: {counter.get('Normal', 0)} ({counter.get('Normal', 0)/len(diagnoses)*100:.1f}%)")
    return diagnoses


def cross_check_with_original(header, rows, diagnoses):
    """对原始 Fault 列有标注的 18 个样本,看 IEC 诊断与之是否一致。"""
    section("5. IEC 自动诊断 vs 原始 Fault 列(交叉验证)")
    fault_idx = header.index("Fault")
    matrix = defaultdict(Counter)
    for r, d in zip(rows, diagnoses):
        original = r[fault_idx]
        if original in ("NA", None):
            continue
        matrix[original][d.fault] += 1

    if not matrix:
        print("  无可交叉验证的样本")
        return

    for original, counter in matrix.items():
        print(f"\n  原始标签 [{original}]:")
        for iec_fault, count in counter.most_common():
            print(f"    → IEC 判为 {iec_fault:<35s}: {count}")
    print("\n  💡 可观察 IEC 法在小样本下与原始标签的一致性")


def gas_means_per_iec_group(header, rows, diagnoses):
    """按 IEC 诊断结果分组,统计气体均值——为合成器提供参数。"""
    section("6. 各 IEC 诊断组的气体特征(用于合成器参数化)")
    groups = defaultdict(list)
    for r, d in zip(rows, diagnoses):
        groups[d.fault].append(r)

    idx = {gas: header.index(gas) for gas in GAS_COLS}
    print(f"  {'诊断组':<35s}{'n':>5s}{'H2':>10s}{'CH4':>10s}{'C2H4':>10s}{'C2H2':>10s}")
    print("  " + "-" * 80)
    for fault, group_rows in sorted(groups.items(), key=lambda x: -len(x[1])):
        n = len(group_rows)
        means = []
        for gas in ["Hydrogen (H2)", "Methane (CH4)", "Ethylene (C2H4)", "Acetylene (C2H2)"]:
            vals = [r[idx[gas]] for r in group_rows
                    if r[idx[gas]] is not None and isinstance(r[idx[gas]], (int, float))]
            means.append(mean(vals) if vals else 0)
        print(f"  {fault:<35s}{n:>5d}" + "".join(f"{m:>10.1f}" for m in means))


def save_labeled_csv(header, rows, diagnoses):
    """保存带 IEC 自动标签的 CSV,作为后续模块的真实数据源。"""
    section("7. 保存带 IEC 标签的数据集")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_header = [
        "transformer_id", "h2", "ch4", "c2h4", "c2h6", "c2h2",
        "co", "co2", "o2", "n2",
        "original_fault", "iec_fault", "iec_code",
        "ratio_c2h2_c2h4", "ratio_ch4_h2", "ratio_c2h4_c2h6",
        "is_abnormal",
    ]
    idx = {gas: header.index(gas) for gas in [
        "Transformer", "Hydrogen (H2)", "Methane (CH4)", "Ethylene (C2H4)",
        "Ethane (C2H6)", "Acetylene (C2H2)", "Carbon Monoxide (CO)",
        "Carbon Dioxide (CO2)", "Oxygen (O2)", "Nitrogen (N2)", "Fault",
    ]}

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(out_header)
        for r, d in zip(rows, diagnoses):
            w.writerow([
                r[idx["Transformer"]],
                r[idx["Hydrogen (H2)"]],
                r[idx["Methane (CH4)"]],
                r[idx["Ethylene (C2H4)"]],
                r[idx["Ethane (C2H6)"]],
                r[idx["Acetylene (C2H2)"]],
                r[idx["Carbon Monoxide (CO)"]],
                r[idx["Carbon Dioxide (CO2)"]],
                r[idx["Oxygen (O2)"]],
                r[idx["Nitrogen (N2)"]],
                r[idx["Fault"]],
                d.fault,
                "-".join(str(c) for c in d.code) if d.code else "",
                round(d.ratios.get("C2H2/C2H4"), 4) if d.ratios.get("C2H2/C2H4") is not None else "",
                round(d.ratios.get("CH4/H2"), 4) if d.ratios.get("CH4/H2") is not None else "",
                round(d.ratios.get("C2H4/C2H6"), 4) if d.ratios.get("C2H4/C2H6") is not None else "",
                int(d.is_abnormal),
            ])
    print(f"  ✅ 已保存: {OUT_CSV}")
    print(f"     行数: {len(diagnoses)}, 列数: {len(out_header)}")


def try_plot(header, rows, diagnoses):
    """画图——若 matplotlib 可用。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n  ⚠️  matplotlib 未安装,跳过可视化(装好后重跑此脚本即可生成图)")
        return

    section("8. 生成可视化")
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # 8.1 IEC 诊断分布饼图
    counter = Counter(d.fault for d in diagnoses)
    labels, sizes = zip(*counter.most_common())
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
    ax.set_title("IEC 60599 三比值法自动诊断分布(n=743)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "iec_distribution.png", dpi=120)
    plt.close()
    print(f"  ✅ {FIG_DIR / 'iec_distribution.png'}")

    # 8.2 7 种气体的对数分布(直方图)
    import math
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    for ax, gas in zip(axes.flatten(), GAS_COLS):
        idx = header.index(gas)
        vals = [r[idx] for r in rows if r[idx] is not None and isinstance(r[idx], (int, float)) and r[idx] > 0]
        log_vals = [math.log10(v) for v in vals]
        ax.hist(log_vals, bins=40)
        ax.set_title(gas)
        ax.set_xlabel("log10(ppm)")
    axes.flatten()[-1].axis("off")
    plt.suptitle("7 种 DGA 气体的对数分布(展示长尾特征)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "gas_log_distribution.png", dpi=120)
    plt.close()
    print(f"  ✅ {FIG_DIR / 'gas_log_distribution.png'}")


def main():
    header, rows = load_rows()
    report_missing(header, rows)
    report_fault_dist(header, rows)
    report_gas_stats(header, rows)
    diagnoses = apply_iec_labeling(header, rows)
    cross_check_with_original(header, rows, diagnoses)
    gas_means_per_iec_group(header, rows, diagnoses)
    save_labeled_csv(header, rows, diagnoses)
    try_plot(header, rows, diagnoses)

    section("EDA 完成")
    print(f"  → 带 IEC 标签的 CSV: {OUT_CSV.relative_to(ROOT.parent)}")
    print(f"  → 后续模块以此 CSV 为真实数据源")


if __name__ == "__main__":
    main()
