"""故障类型判断模块。

对外入口:diagnose_sample / can_diagnose(见 pipeline)。
"""
from app.algorithms.diagnose.pipeline import can_diagnose, diagnose_sample

__all__ = ["can_diagnose", "diagnose_sample"]
