"""LSTM 趋势预测离线训练(论文模块 4 核心产物)。

架构(D-027「离线训练 + 在线推理」):训练是重计算 + 落盘,放脚本层;
产物 lstm.h5 + scaler.pkl 落 BE/models/(已 .gitignore,通过本脚本重训,不进 git)。
在线推理走 app/algorithms/predict/lstm.py(load_lstm + predict_step)。

模型结构(论文写死,D-027):Sequential([LSTM(64), Dense(7)]),
过去 30 天 7 气体 → 第 31 天 7 气体(单步多输出回归)。

防数据泄漏:按时间切训练/验证(不 shuffle);scaler 只在训练集 fit,
验证集复用同一 scaler(见 dataset.train_val_split_by_time / make_windows)。

跑法:python -m scripts.train_lstm
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402

import joblib  # noqa: E402
import pandas as pd  # noqa: E402
from keras.layers import LSTM, Dense  # noqa: E402
from keras.models import Sequential  # noqa: E402

from app.algorithms.predict.dataset import (  # noqa: E402
    DEFAULT_LOOKBACK,
    FEATURE_COLS,
    make_windows,
    train_val_split_by_time,
)

DATA_CSV = ROOT.parent / "data" / "synthetic_timeseries.csv"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "lstm.h5"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
HISTORY_PATH = MODEL_DIR / "train_history.json"   # loss 曲线,供 compare_predict 汇入前端

EPOCHS = 50
BATCH_SIZE = 16
RANDOM_SEED = 42


def build_model(lookback: int, n_features: int) -> Sequential:
    """论文写死结构:LSTM(64) → Dense(7)。MSE 回归,Adam 优化。"""
    model = Sequential([
        LSTM(64, input_shape=(lookback, n_features)),
        Dense(n_features),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def main() -> None:
    import numpy as np
    import tensorflow as tf

    np.random.seed(RANDOM_SEED)
    tf.random.set_seed(RANDOM_SEED)

    print(f"[1/5] 读数据 {DATA_CSV.name}")
    df = pd.read_csv(DATA_CSV)
    df = df.sort_values("date").reset_index(drop=True)
    print(f"      {len(df)} 天 × {len(FEATURE_COLS)} 气体")

    print("[2/5] 时序切分(前 80% 训 / 后 20% 验,不 shuffle)")
    train_df, val_df = train_val_split_by_time(df)
    print(f"      train={len(train_df)} 天 / val={len(val_df)} 天")

    print("[3/5] 造滑窗样本(scaler 只在训练集 fit,验证集复用)")
    X_train, y_train, scaler = make_windows(train_df, lookback=DEFAULT_LOOKBACK)
    X_val, y_val, _ = make_windows(val_df, lookback=DEFAULT_LOOKBACK, scaler=scaler)
    print(f"      X_train{X_train.shape} y_train{y_train.shape} | X_val{X_val.shape}")

    print(f"[4/5] 训练 LSTM(64)→Dense(7),epochs={EPOCHS}")
    model = build_model(DEFAULT_LOOKBACK, len(FEATURE_COLS))
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        shuffle=False,            # 时序,不打乱
        verbose=2,
    )
    tl = history.history["loss"]
    vl = history.history["val_loss"]
    print(f"      train_loss {tl[0]:.4f} → {tl[-1]:.4f} | "
          f"val_loss {vl[0]:.4f} → {vl[-1]:.4f}")

    print(f"[5/5] 落盘 → {MODEL_PATH.name} + {SCALER_PATH.name} + {HISTORY_PATH.name}")
    MODEL_DIR.mkdir(exist_ok=True)
    model.save(MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    # loss 曲线落盘(JSON),供 compare_predict 汇入前端 predict_eval.json
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump({"loss": tl, "val_loss": vl, "epochs": EPOCHS}, f)
    print("      完成。在线推理用 predict.lstm.load_lstm(compile=False)。")


if __name__ == "__main__":
    main()
