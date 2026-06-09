"""异常检测算法层单元测试(模块 3)。

覆盖三个检测器 + 指标模块的核心契约与边界:
    - threshold.detect_one / detect_df —— 国标注意值阈值法
    - iec.diagnose / detect_df —— IEC 三比值法
    - iforest.detect_df —— Isolation Forest 无监督
    - metrics.binary_metrics —— 二分类指标

这些算法是整个系统的地基(检测结果喂给后续预测/预警/Agent),
测试锁定其契约,后续阶段重构时防回归。

运行:cd BE && python -m pytest tests/ -v
"""
import pandas as pd
import pytest

from app.algorithms.detect import threshold, iec, iforest
from app.algorithms.detect.metrics import binary_metrics


# ============== 阈值法 ==============

class TestThreshold:
    def test_normal_sample_not_abnormal(self):
        """全部低于注意值 → 正常,无超标项。"""
        res = threshold.detect_one(h2=40, ch4=2, c2h4=1, c2h6=1, c2h2=0.5, co=100, co2=1000)
        assert res.is_abnormal is False
        assert res.exceeded == []

    def test_c2h2_exceeds_attention_value(self):
        """C2H2=10 > 注意值 5 → 异常,exceeded 含 c2h2。"""
        res = threshold.detect_one(h2=40, ch4=2, c2h4=1, c2h6=1, c2h2=10, co=100, co2=1000)
        assert res.is_abnormal is True
        assert "c2h2" in res.exceeded

    def test_total_hydrocarbon_exceeds(self):
        """总烃 = ch4+c2h4+c2h6+c2h2 = 160 > 150 → 异常,exceeded 含 total_hydrocarbon。
        注:单个烃不设阈值,以总烃合并判定(国标口径)。
        """
        res = threshold.detect_one(h2=40, ch4=60, c2h4=60, c2h6=39, c2h2=1, co=100, co2=1000)
        assert res.is_abnormal is True
        assert "total_hydrocarbon" in res.exceeded

    def test_missing_gases_treated_as_zero(self):
        """缺失 co/co2 按 0 计,不误报。"""
        res = threshold.detect_one(h2=40, ch4=2, c2h4=1, c2h6=1, c2h2=0.5)
        assert res.is_abnormal is False
        assert res.values["co"] == 0.0

    def test_detect_df_returns_int_series(self):
        """批量返回 0/1 int Series,长度与 df 一致。"""
        df = pd.DataFrame([
            {"h2": 40, "ch4": 2, "c2h4": 1, "c2h6": 1, "c2h2": 0.5, "co": 100, "co2": 1000},
            {"h2": 40, "ch4": 2, "c2h4": 1, "c2h6": 1, "c2h2": 10, "co": 100, "co2": 1000},
        ])
        s = threshold.detect_df(df)
        assert len(s) == 2
        assert s.tolist() == [0, 1]
        assert str(s.dtype) == "int64"


# ============== IEC 三比值法 ==============

class TestIEC:
    def test_missing_gas_insufficient_data(self):
        """任一气体缺失 → INSUFFICIENT_DATA,is_abnormal=False。"""
        res = iec.diagnose(h2=None, ch4=20, c2h4=20, c2h6=20, c2h2=5)
        assert res.fault == iec.INSUFFICIENT_DATA
        assert res.is_abnormal is False

    def test_all_below_threshold_normal(self):
        """5 种气体都低于浓度阈值 → NORMAL(无故障特征气体)。"""
        res = iec.diagnose(h2=5, ch4=5, c2h4=5, c2h6=5, c2h2=0.5)
        assert res.fault == iec.NORMAL
        assert res.is_abnormal is False

    def test_divisor_too_small_undetermined(self):
        """分母气体过小致比值不可算 → UNDETERMINED,is_abnormal=False。
        c2h4 接近 0 → r1(c2h2/c2h4)、r3(c2h4/c2h6)不可判。
        """
        res = iec.diagnose(h2=50, ch4=20, c2h4=0.0, c2h6=20, c2h2=5)
        assert res.fault == iec.UNDETERMINED
        assert res.is_abnormal is False

    def test_thermal_low_code_001(self):
        """编码 (0,0,1) → 低温过热 THERMAL_LOW,is_abnormal=True。
        构造:r1<0.1(c2h2 极小), 0.1<=r2<1, 1<=r3<3。
        """
        # c2h2/c2h4 < 0.1 → r1=0;ch4/h2 in [0.1,1) → r2=0;c2h4/c2h6 in [1,3) → r3=1
        res = iec.diagnose(h2=100, ch4=50, c2h4=40, c2h6=20, c2h2=1)
        assert res.code == (0, 0, 1)
        assert res.fault == iec.THERMAL_LOW
        assert res.is_abnormal is True

    def test_encode_ratio_2_special_order(self):
        """CH4/H2 编码顺序特殊:<0.1→1, [0.1,1)→0, >=1→2。"""
        assert iec._encode_ratio_2(0.05) == 1
        assert iec._encode_ratio_2(0.5) == 0
        assert iec._encode_ratio_2(1.5) == 2

    def test_encode_ratio_1_boundaries(self):
        """C2H2/C2H4 编码:<0.1→0, [0.1,3)→1, >=3→2。边界值落在区间下界。"""
        assert iec._encode_ratio_1(0.05) == 0
        assert iec._encode_ratio_1(0.1) == 1
        assert iec._encode_ratio_1(3) == 2


# ============== Isolation Forest ==============

class TestIForest:
    def _make_df(self, n=40):
        """造 n 行正常 + 几行明显离群的数据。"""
        rows = [{"h2": 40, "ch4": 2, "c2h4": 1, "c2h6": 1, "c2h2": 0.5, "co": 100, "co2": 1000}
                for _ in range(n)]
        # 几个明显离群点
        for _ in range(5):
            rows.append({"h2": 9000, "ch4": 8000, "c2h4": 7000, "c2h6": 6000,
                         "c2h2": 500, "co": 9000, "co2": 50000})
        return pd.DataFrame(rows)

    def test_missing_feature_column_raises(self):
        """缺气体列 → KeyError。"""
        df = pd.DataFrame([{"h2": 40, "ch4": 2}])
        with pytest.raises(KeyError):
            iforest.detect_df(df)

    def test_returns_binary_series_same_length(self):
        """返回 0/1 Series,长度与输入一致。"""
        df = self._make_df()
        s = iforest.detect_df(df)
        assert len(s) == len(df)
        assert set(s.unique()).issubset({0, 1})

    def test_deterministic_with_fixed_random_state(self):
        """random_state 固定 → 两次结果完全一致(可复现)。"""
        df = self._make_df()
        s1 = iforest.detect_df(df, random_state=42)
        s2 = iforest.detect_df(df, random_state=42)
        assert s1.tolist() == s2.tolist()


# ============== 二分类指标 ==============

class TestMetrics:
    def test_perfect_prediction(self):
        """全对 → accuracy/precision/recall/f1 = 1.0,fpr = 0.0。"""
        yt = [1, 1, 0, 0]
        yp = [1, 1, 0, 0]
        m = binary_metrics(yt, yp)
        assert m["accuracy"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0
        assert m["fpr"] == 0.0

    def test_known_confusion_matrix(self):
        """手算验证:yt=[1,1,1,0,0], yp=[1,1,0,1,0]
        TP=2 FN=1 FP=1 TN=1 → precision=2/3, recall=2/3, fpr=1/2。
        """
        yt = [1, 1, 1, 0, 0]
        yp = [1, 1, 0, 1, 0]
        m = binary_metrics(yt, yp)
        assert m["confusion"] == {"tp": 2, "tn": 1, "fp": 1, "fn": 1}
        assert m["precision"] == round(2 / 3, 4)
        assert m["recall"] == round(2 / 3, 4)
        assert m["fpr"] == 0.5

    def test_no_positive_prediction_no_crash(self):
        """全预测为正类 → tp+fn 等分母仍可算,不除零崩溃。"""
        yt = [0, 0, 0]
        yp = [1, 1, 1]
        m = binary_metrics(yt, yp)
        assert m["recall"] == 0.0   # tp+fn=0 → 兜底 0
        assert m["fpr"] == 1.0      # 全部正常被误判
