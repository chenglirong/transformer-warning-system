"""预警规则引擎历史回测(论文模块 5 验证产物)。

在 360 天合成时序上逐日跑预警引擎,以**合成真值 fault_state 为 ground truth**
(与检测模块 D-020 同一基准,避免两模块两套真值;论文阶段五原写 IEC 标签,
本轮按 D-020 口径统一改为 fault_state,见 D-033),评估预警的 TP/FP/FN/TN。

命中口径(当日对齐):第 t 天预警是否触发(engine.is_abnormal)vs 第 t 天
fault_state 是否 ≠ Normal。简单可解释;「提前量对齐」(预测未来 N 天 vs 后续
真异常)留未来工作。

软规则预测源 = ARIMA(D-032):每个目标日用截至当日的全量历史跑 ARIMA 预测
未来 3 天,喂给 engine 的软/趋势/组合规则。每日重拟合,360 天稍慢(数分钟)。

输出:
    - 控制台:TP/FP/FN/TN + 准确率/精确率/召回率/F1/误报率 + 四级预警分布
    - data/warning_backtest.json:前端 AlertsView / 论文回测报告数据源
    - notebooks/figures/warning_backtest.png:混淆矩阵 + 等级分布

🚧 系统边界(D-008):只统计二分类命中 + 等级分布,不涉故障类型。

跑法:python -m scripts.backtest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from app.algorithms.predict.arima import forecast_arima  # noqa: E402
from app.algorithms.predict.dataset import DEFAULT_LOOKBACK, FEATURE_COLS  # noqa: E402
from app.algorithms.warning import dedup, engine  # noqa: E402

DATA_CSV = ROOT.parent / "data" / "synthetic_timeseries.csv"
REPORT_JSON = ROOT.parent / "data" / "warning_backtest.json"
FIG_DIR = ROOT.parent / "notebooks" / "figures"

FORECAST_STEPS = 3      # 软规则看未来 3 天

# 等级 → 响应级别(分级响应,非诊断运维建议;守边界 D-008)
LEVEL_RESPONSE = {
    "red": "立即响应", "orange": "24 小时内处理",
    "yellow": "加强监测", "blue": "日常关注",
}


def main() -> None:
    print(f"[1/4] 读数据 {DATA_CSV.name}")
    df = pd.read_csv(DATA_CSV).sort_values("date").reset_index(drop=True)
    rules = engine.load_rules()
    n = len(df)
    # 目标日:前面够 lookback 天(给 ARIMA 足够历史)
    target_idx = list(range(DEFAULT_LOOKBACK, n))
    print(f"      {n} 天,回测目标日 {len(target_idx)} 个(第 {target_idx[0]}~{target_idx[-1]} 天)")

    # dedup 持续性:异常需连续 N 次触发才算有效预警(滤噪声尖峰,D-033)
    consecutive_n = rules.get("dedup", {}).get("consecutive_n", 2)
    rule_hit_history: Dict[str, list] = {}     # rule_id → 历次是否命中(升序)

    print("[2/4] 逐日跑预警引擎(每日 ARIMA 重拟合,稍慢)")
    tp = tn = fp = fn = 0
    level_dist = {"red": 0, "orange": 0, "yellow": 0, "blue": 0}
    records = []
    # 逐日「当前→预测第3天」7 气体涨幅%(预警引擎吃的口径,见 engine 趋势/组合规则),
    # 供 AnalysisView 第2层据实展示「预警输入」而非历史环比。当前已在算 fc,顺手落盘。
    daily_forecast_rate: Dict[str, dict] = {}
    for k, t in enumerate(target_idx):
        row = df.iloc[t]
        current = {c: float(row[c]) for c in FEATURE_COLS}
        oil_temp = float(row["oil_temp"]) if "oil_temp" in df.columns else None
        hist = df.iloc[:t]                                 # 截至 t-1 全量真值
        fc = forecast_arima(hist, steps=FORECAST_STEPS)    # ARIMA 未来 3 天
        res = engine.evaluate(current, oil_temp=oil_temp, forecast_df=fc, rules=rules)

        # 「当前→预测第3天」涨幅%(与 engine 趋势规则同口径 (fut-cur)/cur)。
        # 适用门槛:当日总烃 ≥ 10 μL/L(§9.3.2「总烃起始含量低不宜用相对产气速率」,
        # 见 engine._rate_applicable);不达标则整天所有气体涨幅记 None(低基数下
        # 百分比爆表失真,如 C₂H₄ 0.86→18=+2106%),与引擎判定口径一致。
        fut = fc.iloc[-1]
        total_hc = current["ch4"] + current["c2h4"] + current["c2h6"] + current["c2h2"]
        rate_ok = engine._rate_applicable(total_hc)
        daily_forecast_rate[str(row["date"])] = {
            c: (round((float(fut[c]) - current[c]) / current[c] * 100, 1)
                if rate_ok and current[c] > 0 else None)
            for c in FEATURE_COLS
        }

        # 持续性过滤:更新每条规则命中历史,只保留「连续 N 次」通过的规则
        hit_ids = {x["rule_id"] for x in res["triggered"]}
        persisted = []
        for x in res["triggered"]:
            rid = x["rule_id"]
            hist_list = rule_hit_history.setdefault(rid, [])
            hist_list.append(True)
            if dedup.passes_persistence(hist_list, consecutive_n):
                persisted.append(x)
        # 本次未触发的规则,历史补 False(打断连续性)
        for rid in list(rule_hit_history.keys()):
            if rid not in hit_ids:
                rule_hit_history[rid].append(False)

        # 有效预警 = 经持续性过滤后仍有触发
        eff_level = None
        if persisted:
            eff_level = max((x["level"] for x in persisted),
                            key=lambda lv: engine.LEVEL_ORDER[lv])
        pred_abn = len(persisted) > 0
        true_abn = row["fault_state"] != "Normal"
        if pred_abn and true_abn:
            tp += 1
        elif pred_abn and not true_abn:
            fp += 1
        elif not pred_abn and true_abn:
            fn += 1
        else:
            tn += 1
        if eff_level:
            level_dist[eff_level] += 1
            rule_ids = [x["rule_id"] for x in persisted]
            rule_types = sorted({x["rule_type"] for x in persisted})
            # 触发明细(已填好确切数值的 message),供前端工单详情逐条展示
            messages = [{"rule_id": x["rule_id"], "level": x["level"],
                         "message": x["message"]} for x in persisted]
            records.append({
                "date": str(row["date"]), "level": eff_level,
                "rule_ids": rule_ids,
                "rule_types": rule_types,
                "messages": messages,
                "response": LEVEL_RESPONSE[eff_level],
                "true_abnormal": bool(true_abn),
            })
        if (k + 1) % 30 == 0 or k == len(target_idx) - 1:
            print(f"      {k + 1}/{len(target_idx)}")

    print("[3/4] 算指标")
    total = tp + tn + fp + fn
    acc = (tp + tn) / total if total else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    print("\n=== 预警回测结果(基准=fault_state,当日对齐)===")
    print(f"  混淆矩阵:TP={tp} TN={tn} FP={fp} FN={fn}(n={total})")
    print(f"  准确率={acc:.4f} 精确率={prec:.4f} 召回率={rec:.4f} "
          f"F1={f1:.4f} 误报率={fpr:.4f}")
    print(f"  四级分布(触发日):{level_dist}")

    report = {
        "baseline": "synthetic fault_state(D-020/D-033 当日对齐)",
        "n_days": total,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "metrics": {
            "accuracy": round(acc, 4), "precision": round(prec, 4),
            "recall": round(rec, 4), "f1": round(f1, 4), "fpr": round(fpr, 4),
        },
        "level_distribution": level_dist,
        "n_alerts": len(records),
        "alerts": records,                  # 全量触发记录(前端分页),时间升序
        # 逐日「当前→预测第3天」7气体涨幅%(AnalysisView 第2层预警输入口径)
        "daily_forecast_rate": daily_forecast_rate,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"      落盘 → data/warning_backtest.json")

    print("[4/4] 出图")
    try:
        _plot(report)
        print("      图见 notebooks/figures/warning_backtest.png")
    except ModuleNotFoundError:
        print("\n  ⚠️  matplotlib 未安装,跳过图(指标已打印 + 落盘)")


def _plot(report: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scripts._plot_style import apply_chinese_font
    apply_chinese_font()

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # 左:混淆矩阵
    c = report["confusion"]
    mat = [[c["tp"], c["fn"]], [c["fp"], c["tn"]]]
    ax1.imshow(mat, cmap="Blues")
    ax1.set_xticks([0, 1]); ax1.set_xticklabels(["pred abnormal", "pred normal"])
    ax1.set_yticks([0, 1]); ax1.set_yticklabels(["true abnormal", "true normal"])
    for i in range(2):
        for j in range(2):
            ax1.text(j, i, mat[i][j], ha="center", va="center", fontsize=16)
    ax1.set_title(f"Warning confusion (F1={report['metrics']['f1']:.3f})")

    # 右:四级分布
    ld = report["level_distribution"]
    colors = {"red": "#dc2626", "orange": "#f97316", "yellow": "#eab308", "blue": "#3b82f6"}
    keys = ["red", "orange", "yellow", "blue"]
    ax2.bar(keys, [ld[k] for k in keys], color=[colors[k] for k in keys])
    ax2.set_title("Alert level distribution (triggered days)")
    for i, k in enumerate(keys):
        ax2.text(i, ld[k], str(ld[k]), ha="center", va="bottom")

    fig.tight_layout()
    plt.savefig(FIG_DIR / "warning_backtest.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
