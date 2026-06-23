"""异常检测三方法对比实验(模块 3 核心产物)。

以**合成真值 fault_state 为 ground truth**(D-020),横向评估三种异常检测方法:
    1. 阈值法(国标 DL/T 722)        detect/threshold.py
    2. IEC 三比值法(国际标准)        detect/iec.py
    3. Isolation Forest(无监督 ML)   detect/iforest.py

输出:
    - 控制台:各方法 准确率/精确率/召回率/F1/误报率 对比表
    - notebooks/figures/detection_confusion.png:三方法混淆矩阵

系统边界(D-008):仅做 is_abnormal 二分类评估,不呈现具体故障类型。

跑法:python -m scripts.compare_detection
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from app.algorithms.detect import threshold, iec, iforest  # noqa: E402

DATA_CSV = ROOT.parent / "data" / "featured_timeseries.csv"
FIG_DIR = ROOT.parent / "notebooks" / "figures"


def _metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    """二分类指标(1=异常为正类)。手算,不引入额外依赖。"""
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    n = tp + tn + fp + fn
    acc = (tp + tn) / n if n else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    # 误报率 FPR = FP / (FP + TN):正常样本被误判为异常的比例
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        "accuracy": acc, "precision": prec, "recall": rec,
        "f1": f1, "fpr": fpr,
    }


def main() -> None:
    print("=" * 70)
    print("  异常检测三方法对比实验(基准:合成真值 fault_state,D-020)")
    print("=" * 70)

    df = pd.read_csv(DATA_CSV)
    # ground truth:fault_state != Normal 即异常
    y_true = (df["fault_state"] != "Normal").astype(int)
    print(f"  样本数: {len(df)}  真值异常: {y_true.sum()} ({y_true.mean()*100:.1f}%)\n")

    methods = {
        "Threshold": threshold.detect_df,
        "IEC": iec.detect_df,
        "IsolationForest": iforest.detect_df,
    }

    results = {}
    preds = {}
    for name, fn in methods.items():
        y_pred = fn(df)
        preds[name] = y_pred
        results[name] = _metrics(y_true, y_pred)

    # 对比表
    hdr = f"  {'方法':<16}{'准确率':>8}{'精确率':>8}{'召回率':>8}{'F1':>8}{'误报率':>8}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for name, m in results.items():
        print(f"  {name:<16}{m['accuracy']:>8.3f}{m['precision']:>8.3f}"
              f"{m['recall']:>8.3f}{m['f1']:>8.3f}{m['fpr']:>8.3f}")
    print()
    for name, m in results.items():
        print(f"  {name:<16} TP={m['TP']:3d} TN={m['TN']:3d} "
              f"FP={m['FP']:3d} FN={m['FN']:3d}")

    _plot_confusion(y_true, preds, results)

    print("\n" + "=" * 70)
    print("  完成。图表见 notebooks/figures/detection_confusion.png")
    print("=" * 70)


def _plot_confusion(y_true: pd.Series, preds: dict, results: dict) -> None:
    """画三方法混淆矩阵。标签用英文,避免中文字体依赖。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scripts._plot_style import apply_chinese_font
        apply_chinese_font()
    except ImportError:
        print("\n  ⚠️  matplotlib 未安装,跳过混淆矩阵图")
        return

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, (name, m) in zip(axes, results.items()):
        mat = [[m["TN"], m["FP"]], [m["FN"], m["TP"]]]
        ax.imshow(mat, cmap="Blues")
        ax.set_title(f"{name}\nF1={m['f1']:.3f}  FPR={m['fpr']:.3f}")
        ax.set_xticks([0, 1]); ax.set_xticklabels(["Pred Normal", "Pred Abnormal"])
        ax.set_yticks([0, 1]); ax.set_yticklabels(["True Normal", "True Abnormal"])
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(mat[i][j]), ha="center", va="center",
                        color="black", fontsize=14)
    plt.suptitle("Anomaly Detection: Confusion Matrices (GT = synthetic fault_state)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "detection_confusion.png", dpi=120)
    plt.close()
    print(f"\n  ✅ {FIG_DIR / 'detection_confusion.png'}")


if __name__ == "__main__":
    main()
