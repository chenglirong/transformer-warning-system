"""LSTM vs ARIMA 趋势预测对比实验(论文模块 4 核心产物)。

在验证段(后 20%)做**单步 walk-forward 对比**:对每个目标日 t,
    - LSTM:用前 lookback 天滑窗(predict.lstm.predict_step)预测第 t 天
    - ARIMA:用截至 t-1 的全量真值 fit 后 forecast 1 步
两法在**同一批目标日、同一真值**上算 MAE / RMSE / MAPE(7 气体),横向对比。

口径说明:
    - 两法各用其自然输入(LSTM=近 30 天窗口;ARIMA=全量历史,时序预测惯例),
      对比落在"同目标日预测精度",公平。
    - MAPE 对含 0 气体会除零,故**只在真值非 0 的日子上算**(并报告样本数)。
    - 承 D-028:LSTM 单步精度有数据/建模软肋;本实验据实出数,叙事走向
      (LSTM 胜→讲深度学习;ARIMA 胜→兜底"ARIMA 更稳健")由结果定。

输出:
    - 控制台:两法 7 气体 MAE/RMSE/MAPE 对比表 + 总体均值
    - notebooks/figures/predict_compare.png:7 子图(每气体真值 vs 两法预测)

跑法:python -m scripts.compare_predict
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.algorithms.predict.arima import forecast_arima  # noqa: E402
from app.algorithms.predict.dataset import (  # noqa: E402
    DEFAULT_LOOKBACK,
    DEFAULT_VAL_RATIO,
    FEATURE_COLS,
)
from app.algorithms.predict.lstm import load_lstm, predict_step  # noqa: E402
from app.algorithms.predict.rolling import rolling_forecast  # noqa: E402

DATA_CSV = ROOT.parent / "data" / "synthetic_timeseries.csv"
MODEL_PATH = ROOT / "models" / "lstm.h5"
SCALER_PATH = ROOT / "models" / "scaler.pkl"
HISTORY_PATH = ROOT / "models" / "train_history.json"   # train_lstm 落的 loss 曲线
EVAL_JSON = ROOT.parent / "data" / "predict_eval.json"   # 前端 PredictionView 数据源
FIG_DIR = ROOT.parent / "notebooks" / "figures"


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """MAE / RMSE / MAPE(MAPE 仅在真值非 0 处算,避免除零)。"""
    err = y_pred - y_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    nz = y_true != 0
    if nz.any():
        mape = float(np.mean(np.abs(err[nz] / y_true[nz])) * 100)
        n_mape = int(nz.sum())
    else:
        mape, n_mape = float("nan"), 0
    return {"mae": mae, "rmse": rmse, "mape": mape, "n_mape": n_mape}


def main() -> None:
    print(f"[1/4] 读数据 + 模型")
    df = pd.read_csv(DATA_CSV).sort_values("date").reset_index(drop=True)
    model = load_lstm(str(MODEL_PATH))           # compile=False,见 D-027
    scaler = joblib.load(SCALER_PATH)
    n = len(df)
    split = int(n * (1.0 - DEFAULT_VAL_RATIO))
    # 目标日:验证段中、且前面够 lookback 天的那些天
    target_idx = list(range(max(split + DEFAULT_LOOKBACK, DEFAULT_LOOKBACK), n))
    print(f"      {n} 天,验证段目标日 {len(target_idx)} 个(第 {target_idx[0]}~{target_idx[-1]} 天)")

    print("[2/4] LSTM 单步 walk-forward")
    lstm_pred = {c: [] for c in FEATURE_COLS}
    truth = {c: [] for c in FEATURE_COLS}
    for t in target_idx:
        window = df.iloc[t - DEFAULT_LOOKBACK:t]
        p = predict_step(model, scaler, window)
        for c in FEATURE_COLS:
            lstm_pred[c].append(p[c])
            truth[c].append(df[c].iloc[t])

    print("[3/4] ARIMA 单步 walk-forward(每目标日全量历史重拟合,稍慢)")
    arima_pred = {c: [] for c in FEATURE_COLS}
    for k, t in enumerate(target_idx):
        hist = df.iloc[:t]                         # 截至 t-1 的全量真值
        fc = forecast_arima(hist, steps=1)         # (1, 7)
        for c in FEATURE_COLS:
            arima_pred[c].append(float(fc[c].iloc[0]))
        if (k + 1) % 10 == 0 or k == len(target_idx) - 1:
            print(f"      ARIMA {k + 1}/{len(target_idx)}")

    print("[4/4] 算指标 + 出图")
    rows = []
    lstm_maes, arima_maes = [], []
    for c in FEATURE_COLS:
        yt = np.asarray(truth[c])
        ml = _metrics(yt, np.asarray(lstm_pred[c]))
        ma = _metrics(yt, np.asarray(arima_pred[c]))
        lstm_maes.append(ml["mae"])
        arima_maes.append(ma["mae"])
        rows.append((c, ml, ma))

    # 控制台对比表
    print("\n=== LSTM vs ARIMA 单步预测对比(验证段)===")
    print(f"{'气体':<6} {'LSTM_MAE':>10} {'ARIMA_MAE':>10} {'LSTM_RMSE':>10} "
          f"{'ARIMA_RMSE':>11} {'LSTM_MAPE%':>11} {'ARIMA_MAPE%':>12} {'胜者':>6}")
    for c, ml, ma in rows:
        winner = "LSTM" if ml["mae"] < ma["mae"] else "ARIMA"
        print(f"{c:<6} {ml['mae']:>10.3f} {ma['mae']:>10.3f} {ml['rmse']:>10.3f} "
              f"{ma['rmse']:>11.3f} {ml['mape']:>11.2f} {ma['mape']:>12.2f} {winner:>6}")
    print(f"\n总体平均 MAE:LSTM={np.mean(lstm_maes):.3f}  ARIMA={np.mean(arima_maes):.3f}")
    overall = "LSTM" if np.mean(lstm_maes) < np.mean(arima_maes) else "ARIMA"
    print(f"总体更优(MAE):{overall}")

    # 滚动预测(未来 1-3 天):取最后 lookback 天历史,两模型各出多步
    #   LSTM 迭代回灌(rolling_forecast);ARIMA 原生多步(forecast_arima steps=3)
    print("      滚动预测未来 3 天(LSTM 回灌 / ARIMA 原生多步)")
    roll_steps = 3
    hist_tail = df.iloc[-DEFAULT_LOOKBACK:]
    lstm_roll = rolling_forecast(model, scaler, df, steps=roll_steps)
    arima_roll = forecast_arima(df, steps=roll_steps)
    rolling_data = {
        "history_days": 7,                 # 前端展示最近 7 天真实值作上下文
        "gases": FEATURE_COLS,
        "history": {c: [round(float(v), 3) for v in df[c].iloc[-7:]] for c in FEATURE_COLS},
        "lstm": {c: [round(float(v), 3) for v in lstm_roll[c]] for c in FEATURE_COLS},
        "arima": {c: [round(float(v), 3) for v in arima_roll[c]] for c in FEATURE_COLS},
    }

    _dump_eval_json(rows, target_idx, truth, lstm_pred, arima_pred, overall,
                    float(np.mean(lstm_maes)), float(np.mean(arima_maes)), rolling_data)
    print(f"      指标 + 曲线 + 滚动预测落盘 → data/predict_eval.json(前端 PredictionView 数据源)")

    try:
        _plot(target_idx, truth, lstm_pred, arima_pred)
        print(f"完成。图见 notebooks/figures/predict_compare.png")
    except ModuleNotFoundError:
        print("\n  ⚠️  matplotlib 未安装,跳过对比图(指标表已打印)")


def _dump_eval_json(rows, target_idx, truth, lstm_pred, arima_pred,
                    overall, lstm_mean_mae, arima_mean_mae, rolling_data=None) -> None:
    """把对比指标 + 验证段三序列 + loss 曲线写 data/predict_eval.json。

    前端 PredictionView 读此文件渲染(训练时快照,API 只读文件,毫秒级,
    守 D-027「在线推理轻量」)。守边界:只含 MAE/RMSE/MAPE + 气体浓度曲线,
    不涉 fault_state / 故障类型。
    """
    per_gas = {}
    for c, ml, ma in rows:
        per_gas[c] = {
            "lstm": {"mae": round(ml["mae"], 3), "rmse": round(ml["rmse"], 3),
                     "mape": round(ml["mape"], 2)},
            "arima": {"mae": round(ma["mae"], 3), "rmse": round(ma["rmse"], 3),
                      "mape": round(ma["mape"], 2)},
            "winner": "LSTM" if ml["mae"] < ma["mae"] else "ARIMA",
        }
    # 验证段曲线(真值 vs 两法),x 轴为目标日序号
    series = {
        c: {
            "truth": [round(float(v), 3) for v in truth[c]],
            "lstm": [round(float(v), 3) for v in lstm_pred[c]],
            "arima": [round(float(v), 3) for v in arima_pred[c]],
        }
        for c in FEATURE_COLS
    }
    # loss 曲线(train_lstm 落的,可能不存在 → 容错)
    loss_history = {}
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, encoding="utf-8") as f:
            loss_history = json.load(f)

    payload = {
        "baseline": "synthetic_timeseries 验证段(后 20%)单步 walk-forward",
        "n_target_days": len(target_idx),
        "gases": FEATURE_COLS,
        "overall": {
            "winner": overall,
            "lstm_mean_mae": round(lstm_mean_mae, 3),
            "arima_mean_mae": round(arima_mean_mae, 3),
        },
        "per_gas": per_gas,
        "series": series,
        "loss_history": loss_history,
        "rolling": rolling_data or {},     # 滚动预测(未来 1-3 天,LSTM vs ARIMA)
    }
    EVAL_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _plot(target_idx, truth, lstm_pred, arima_pred) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(4, 2, figsize=(14, 14))
    axes = axes.ravel()
    x = list(range(len(target_idx)))
    for i, c in enumerate(FEATURE_COLS):
        ax = axes[i]
        ax.plot(x, truth[c], label="actual", color="#333", linewidth=1.5)
        ax.plot(x, lstm_pred[c], label="LSTM", color="#d62728", alpha=0.8)
        ax.plot(x, arima_pred[c], label="ARIMA", color="#1f77b4", alpha=0.8)
        ax.set_title(c)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    axes[-1].axis("off")    # 7 gases in 8 cells, last one blank
    fig.suptitle("LSTM vs ARIMA single-step forecast (validation segment)", fontsize=14)
    fig.tight_layout()
    plt.savefig(FIG_DIR / "predict_compare.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
