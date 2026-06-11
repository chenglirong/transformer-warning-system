"""预测算法层单元测试(模块 4)。

覆盖纯算法层的契约与边界(不依赖训练好的 .h5,测试不绑落盘产物):
    - dataset.make_windows / train_val_split_by_time —— 滑窗造样本 + 时序切分
    - arima.forecast_arima —— ARIMA 基线(含 0 序列兜底)
    - rolling.rolling_forecast —— 滚动预测(用 stub model,验证回灌逻辑)

lstm.load_lstm/predict_step 的真模型推理在 scripts/compare_predict.py 端到端
验证(D-029),此处只用 stub 测 rolling 的迭代/回灌/clip 契约,避免单测依赖 .h5。

运行:cd BE && python -m pytest tests/test_predict.py -v
"""
import numpy as np
import pandas as pd
import pytest

from app.algorithms.predict import arima, dataset, rolling
from app.algorithms.predict.dataset import FEATURE_COLS


def _make_ts(n=60):
    """造 n 天合成时序(7 气体 + date),值随机但可复现。"""
    rng = np.random.default_rng(42)
    data = {"date": pd.date_range("2024-01-01", periods=n).astype(str)}
    for c in FEATURE_COLS:
        data[c] = rng.uniform(1, 100, n)
    return pd.DataFrame(data)


# ============== dataset 滑窗造样本 ==============

class TestMakeWindows:
    def test_window_shapes(self):
        """lookback=30、60 天 → X(30,30,7) y(30,7)(n-lookback 个样本)。"""
        df = _make_ts(60)
        X, y, scaler = dataset.make_windows(df, lookback=30)
        assert X.shape == (30, 30, 7)
        assert y.shape == (30, 7)
        assert scaler is not None

    def test_missing_gas_column_raises(self):
        """缺气体列 → KeyError。"""
        df = pd.DataFrame({"h2": [1, 2, 3], "ch4": [1, 2, 3]})
        with pytest.raises(KeyError):
            dataset.make_windows(df, lookback=2)

    def test_insufficient_rows_raises(self):
        """行数 <= lookback,造不出窗口 → ValueError。"""
        df = _make_ts(10)
        with pytest.raises(ValueError):
            dataset.make_windows(df, lookback=30)

    def test_scaled_into_unit_range(self):
        """新 fit 的 MinMax 把值压进 [0,1](float32 转换有微小浮点误差,留容差)。"""
        df = _make_ts(60)
        X, y, _ = dataset.make_windows(df, lookback=30)
        assert X.min() >= -1e-6 and X.max() <= 1.0 + 1e-6

    def test_reuse_scaler_does_not_refit(self):
        """传入已 fit 的 scaler → 复用同一变换(验证/推理口径一致,防泄漏)。"""
        df = _make_ts(60)
        _, _, scaler = dataset.make_windows(df, lookback=30)
        df2 = _make_ts(50)
        X2a, _, _ = dataset.make_windows(df2, lookback=20, scaler=scaler)
        X2b, _, _ = dataset.make_windows(df2, lookback=20, scaler=scaler)
        assert np.allclose(X2a, X2b)            # 同 scaler 同输入 → 同输出


# ============== dataset 时序切分 ==============

class TestTrainValSplit:
    def test_split_ratio_and_order(self):
        """100 天 val_ratio=0.2 → 训练前 80 / 验证后 20,按时间不打乱。"""
        df = _make_ts(100)
        tr, va = dataset.train_val_split_by_time(df, val_ratio=0.2)
        assert len(tr) == 80
        assert len(va) == 20
        # 训练集末日 < 验证集首日(时序连续,无打乱)
        assert tr["date"].iloc[-1] < va["date"].iloc[0]


# ============== ARIMA 基线 ==============

class TestArima:
    def test_forecast_shape(self):
        """steps=1 → (1,7);steps=3 → (3,7),列为 7 气体。"""
        df = _make_ts(60)
        out1 = arima.forecast_arima(df, steps=1)
        out3 = arima.forecast_arima(df, steps=3)
        assert out1.shape == (1, 7)
        assert out3.shape == (3, 7)
        assert list(out1.columns) == FEATURE_COLS

    def test_missing_gas_column_raises(self):
        """缺气体列 → KeyError。"""
        df = pd.DataFrame({"h2": [1, 2, 3]})
        with pytest.raises(KeyError):
            arima.forecast_arima(df, steps=1)

    def test_output_non_negative(self):
        """预测值 clip 到非负(气体浓度物理约束)。"""
        df = _make_ts(60)
        out = arima.forecast_arima(df, steps=3)
        assert (out.values >= 0).all()

    def test_all_zero_series_naive_fallback(self):
        """全 0 序列 ARIMA 不收敛 → naive 兜底(持平最后值=0),不崩。"""
        df = _make_ts(40)
        df["c2h2"] = 0.0                        # 模拟含大量 0 的气体
        out = arima.forecast_arima(df, steps=2)
        assert out.shape == (2, 7)
        assert (out["c2h2"] == 0.0).all()       # 持平最后观测值 0

    def test_forecast_one_naive_on_constant(self):
        """_forecast_one 对常数序列退化为持平该常数。"""
        series = np.full(30, 5.0)
        fc = arima._forecast_one(series, steps=3, order=(2, 1, 2))
        assert len(fc) == 3
        assert all(v == 5.0 for v in fc)


# ============== 滚动预测(stub model) ==============

class _StubModel:
    """假 LSTM:predict 返回固定缩放值(0.5),验证 rolling 回灌/形状契约。

    形状契约同 Keras:输入 (1, lookback, 7) → 输出 (1, 7)。
    """
    def predict(self, x, verbose=0):
        assert x.ndim == 3 and x.shape[2] == 7
        return np.full((1, 7), 0.5, dtype=np.float32)


class TestRolling:
    def _fitted_scaler(self, df, lookback):
        """在 df 上 fit 一个真 scaler(rolling 内部 transform/inverse 要用)。"""
        _, _, scaler = dataset.make_windows(df, lookback=lookback)
        return scaler

    def test_rolling_shape_and_index(self):
        """steps=3 → (3,7),index 为 step_1..step_3。"""
        df = _make_ts(60)
        scaler = self._fitted_scaler(df, lookback=30)
        out = rolling.rolling_forecast(_StubModel(), scaler, df, steps=3, lookback=30)
        assert out.shape == (3, 7)
        assert list(out.index) == ["step_1", "step_2", "step_3"]
        assert list(out.columns) == FEATURE_COLS

    def test_rolling_no_nan_non_negative(self):
        """滚动结果无 NaN、非负(clip)。"""
        df = _make_ts(60)
        scaler = self._fitted_scaler(df, lookback=30)
        out = rolling.rolling_forecast(_StubModel(), scaler, df, steps=3, lookback=30)
        assert not out.isna().any().any()
        assert (out.values >= 0).all()

    def test_insufficient_history_raises(self):
        """history 行数 < lookback → ValueError。"""
        df = _make_ts(20)
        scaler = self._fitted_scaler(_make_ts(60), lookback=30)
        with pytest.raises(ValueError):
            rolling.rolling_forecast(_StubModel(), scaler, df, steps=3, lookback=30)
