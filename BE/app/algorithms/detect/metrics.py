"""二分类评估指标(异常检测对比共用)。

抽出此模块,避免 API 层(api/detect.py)与脚本(scripts/compare_detection.py)
各写一份指标计算——承 CLAUDE.md「算法层与 Web/DB 解耦」约定:纯函数,
输入真值/预测,输出指标 dict,不依赖 DB/HTTP。

约定:1=异常为正类(预警语义下「异常」是我们要抓的目标)。
"""
from __future__ import annotations

from typing import Sequence


def binary_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> dict:
    """算二分类指标。y_true/y_pred 为 0/1 序列(可为 list 或 pandas Series)。

    返回 accuracy/precision/recall/f1/fpr + 混淆矩阵 tp/tn/fp/fn。
    误报率 FPR = FP/(FP+TN):正常样本被误判为异常的比例。
    """
    yt = list(y_true)
    yp = list(y_pred)
    tp = sum(1 for t, p in zip(yt, yp) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(yt, yp) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(yt, yp) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(yt, yp) if t == 1 and p == 0)
    n = tp + tn + fp + fn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {
        "accuracy": round((tp + tn) / n, 4) if n else 0.0,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "fpr": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }
