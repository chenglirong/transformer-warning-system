"""预警决策算法层单元测试(模块 5)。

覆盖规则引擎 + 误报控制的契约与边界:
    - engine.evaluate —— 硬/软/趋势/组合规则触发 + 四级分级取最高
    - dedup.passes_persistence / is_duplicate / should_push —— 误报控制

阈值口径(与 detect/threshold.ATTENTION_VALUES 一致):
    h2>150 / c2h2>5 / 总烃>150 / co>300 / co2>10000。

运行:cd BE && python -m pytest tests/test_warning.py -v
"""
from datetime import datetime, timedelta

import pandas as pd
import pytest

from app.algorithms.warning import dedup, engine
from app.algorithms.predict.dataset import FEATURE_COLS


def _gases(h2=10, ch4=5, c2h4=5, c2h6=5, c2h2=0.5, co=100, co2=1000):
    """造一组气体 dict,默认全部低于注意值(正常)。"""
    return {"h2": h2, "ch4": ch4, "c2h4": c2h4, "c2h6": c2h6,
            "c2h2": c2h2, "co": co, "co2": co2}


def _forecast(rows):
    """造 ARIMA 预测 DataFrame(行=天,列=7 气体)。rows 为 dict 列表。"""
    full = [_gases(**r) for r in rows]
    return pd.DataFrame(full, columns=FEATURE_COLS)


# ============== 规则引擎 ==============

class TestEngine:
    def test_normal_no_trigger(self):
        """全部正常 + 无预测 → 不触发,level=None,is_abnormal=False。"""
        res = engine.evaluate(_gases())
        assert res["triggered"] == []
        assert res["level"] is None
        assert res["is_abnormal"] is False

    def test_hard_rule_c2h2_red(self):
        """C₂H₂=10 > 5 当前已超标 → 硬规则 H-01,红色。"""
        res = engine.evaluate(_gases(c2h2=10))
        assert res["level"] == "red"
        assert res["is_abnormal"] is True
        ids = [t["rule_id"] for t in res["triggered"]]
        assert "H-01" in ids
        assert all(t["rule_type"] == "hard" for t in res["triggered"] if t["rule_id"] == "H-01")

    def test_hard_rule_total_hydrocarbon(self):
        """总烃 = 60+60+39+1 = 160 > 150 → 硬规则 H-03 红色。"""
        res = engine.evaluate(_gases(ch4=60, c2h4=60, c2h6=39, c2h2=1))
        ids = [t["rule_id"] for t in res["triggered"]]
        assert "H-03" in ids
        assert res["level"] == "red"

    def test_soft_rule_day1_red(self):
        """当前正常,预测第 1 天 C₂H₂ 超标(24h 内)→ 软规则 red。"""
        fc = _forecast([{"c2h2": 8}, {"c2h2": 9}, {"c2h2": 10}])
        res = engine.evaluate(_gases(c2h2=0.5), forecast_df=fc)
        soft = [t for t in res["triggered"] if t["rule_id"] == "S-01"]
        assert len(soft) == 1
        assert soft[0]["level"] == "red"      # 第 1 天超 → red
        assert soft[0]["rule_type"] == "soft"

    def test_soft_rule_day3_orange(self):
        """当前正常,预测第 3 天才 C₂H₂ 超标 → 软规则 orange。"""
        fc = _forecast([{"c2h2": 2}, {"c2h2": 4}, {"c2h2": 8}])
        res = engine.evaluate(_gases(c2h2=0.5), forecast_df=fc)
        soft = [t for t in res["triggered"] if t["rule_id"] == "S-01"]
        assert len(soft) == 1
        assert soft[0]["level"] == "orange"   # 第 3 天超 → orange

    def test_trend_rule_yellow(self):
        """C₂H₂ 0.5→2(涨 3 倍 ≥ 50%)但未超标 5 → 趋势规则 T-01 黄色。"""
        fc = _forecast([{"c2h2": 1}, {"c2h2": 1.5}, {"c2h2": 2}])
        res = engine.evaluate(_gases(c2h2=0.5), forecast_df=fc)
        ids = [t["rule_id"] for t in res["triggered"]]
        assert "T-01" in ids
        t01 = next(t for t in res["triggered"] if t["rule_id"] == "T-01")
        assert t01["level"] == "yellow"

    def test_combo_rule_gas_rise_and_hot_oil(self):
        """C₂H₂ 涨 ≥30% + 油温 85 ≥ 80 → 组合规则 C-01 橙色。"""
        fc = _forecast([{"c2h2": 0.6}, {"c2h2": 0.7}, {"c2h2": 0.8}])
        res = engine.evaluate(_gases(c2h2=0.5), oil_temp=85, forecast_df=fc)
        ids = [t["rule_id"] for t in res["triggered"]]
        assert "C-01" in ids
        c01 = next(t for t in res["triggered"] if t["rule_id"] == "C-01")
        assert c01["rule_type"] == "combo"

    def test_combo_not_triggered_when_oil_temp_low(self):
        """气体涨但油温低(< 80)→ 组合规则不触发。"""
        fc = _forecast([{"c2h2": 0.6}, {"c2h2": 0.7}, {"c2h2": 0.8}])
        res = engine.evaluate(_gases(c2h2=0.5), oil_temp=50, forecast_df=fc)
        ids = [t["rule_id"] for t in res["triggered"]]
        assert "C-01" not in ids

    def test_level_takes_highest(self):
        """同时触发 yellow(趋势)+ red(硬)→ 综合等级取最高 red。"""
        fc = _forecast([{"c2h2": 1}, {"c2h2": 1.5}, {"c2h2": 2}])
        res = engine.evaluate(_gases(h2=200), forecast_df=fc)   # h2 超标 red
        assert res["level"] == "red"
        levels = {t["level"] for t in res["triggered"]}
        assert "red" in levels and "yellow" in levels

    def test_no_forecast_skips_predictive_rules(self):
        """不传 forecast → 只跑硬规则,软/趋势/组合跳过不报错。"""
        res = engine.evaluate(_gases(c2h2=10))    # 硬规则 red
        assert res["level"] == "red"
        assert all(t["rule_type"] == "hard" for t in res["triggered"])


# ============== 误报控制 ==============

class TestDedup:
    def test_persistence_needs_consecutive(self):
        """连续 2 次才报:[True] 不够,[True,True] 通过。"""
        assert dedup.passes_persistence([True], 2) is False
        assert dedup.passes_persistence([True, True], 2) is True

    def test_persistence_breaks_on_gap(self):
        """中间断开 [True, False, True] → 最近 2 次非全 True → 不通过。"""
        assert dedup.passes_persistence([True, False, True], 2) is False

    def test_persistence_n1_single_hit(self):
        """N=1 时本次命中即可。"""
        assert dedup.passes_persistence([True], 1) is True
        assert dedup.passes_persistence([False], 1) is False

    def test_duplicate_within_cooldown(self):
        """距上次 1 小时 < 冷却 24h → 算重复,抑制。"""
        now = datetime(2025, 1, 2, 12, 0)
        last = now - timedelta(hours=1)
        assert dedup.is_duplicate(last, now, 24) is True

    def test_not_duplicate_after_cooldown(self):
        """距上次 25 小时 > 冷却 24h → 非重复,可推送。"""
        now = datetime(2025, 1, 2, 12, 0)
        last = now - timedelta(hours=25)
        assert dedup.is_duplicate(last, now, 24) is False

    def test_never_triggered_not_duplicate(self):
        """从未推送(None)→ 非重复。"""
        assert dedup.is_duplicate(None, datetime(2025, 1, 1), 24) is False

    def test_should_push_combines_both(self):
        """综合:连续 2 次 + 不在冷却期 → 推送;缺任一 → 不推送。"""
        now = datetime(2025, 1, 2, 12, 0)
        # 连续够 + 从未推送 → 推送
        assert dedup.should_push([True, True], None, now, 2, 24) is True
        # 连续不够 → 不推送
        assert dedup.should_push([True], None, now, 2, 24) is False
        # 连续够但在冷却期 → 不推送
        assert dedup.should_push([True, True], now - timedelta(hours=1), now, 2, 24) is False
