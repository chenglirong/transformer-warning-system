"""API 层测试 —— 锁系统边界契约。

核心:业务接口只输出 is_abnormal 二分类,绝不暴露 fault_state / IEC 故障类型。
这是论文红线(D-008 边界),最该有回归保护。

用内存 SQLite + dependency_overrides 注入可控数据(T1),塞 1 正常 + 1 异常样本。
运行:cd BE && python -m pytest tests/test_api.py -v
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.db.models import Monitoring


@pytest.fixture
def client():
    """内存库 + 2 条样本(1 正常 / 1 C2H2 超标异常),注入 get_db。"""
    # StaticPool:内存 SQLite 所有连接共享同一底层 connection,
    # 否则 create_all 建表的连接与 Session 查询的连接是不同的空库(no such table)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSession()
    # 正常样本
    db.add(Monitoring(
        transformer_id=1, date=date(2024, 4, 1),
        h2=40, ch4=2, c2h4=1, c2h6=1, c2h2=0.5, co=100, co2=1000,
        oil_temp=35, load_current=180, ambient_temp=10,
        fault_state="Normal",
    ))
    # 异常样本(C2H2=10 > 注意值 5,且日期更新 → 最新一条)
    db.add(Monitoring(
        transformer_id=1, date=date(2024, 4, 2),
        h2=40, ch4=2, c2h4=1, c2h6=1, c2h2=10, co=100, co2=1000,
        oil_temp=36, load_current=185, ambient_temp=11,
        fault_state="Discharge of Low Energy",
    ))
    db.commit()
    db.close()

    def _override():
        d = TestingSession()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _data(resp):
    """取信封里的业务数据。"""
    assert resp.status_code == 200
    return resp.json()["data"]


# ============== 系统边界:不暴露 fault_state / 故障类型 ==============

class TestBoundary:
    def test_transformers_no_fault_state(self, client):
        data = _data(client.get("/api/data/transformers"))
        assert isinstance(data, list) and data
        for row in data:
            assert "is_abnormal" in row
            assert "fault_state" not in row
            assert "fault" not in row

    def test_latest_no_fault_state(self, client):
        data = _data(client.get("/api/data/latest/1"))
        assert "is_abnormal" in data
        assert "fault_state" not in data
        assert "fault" not in data

    def test_timeseries_no_fault_state(self, client):
        data = _data(client.get("/api/data/timeseries/1"))
        for pt in data["series"]:
            assert "is_abnormal" in pt
            assert "fault_state" not in pt

    def test_detect_methods_no_fault_type(self, client):
        data = _data(client.get("/api/detect/methods/1"))
        # IEC 块只回 is_abnormal,不含 fault / code
        assert "is_abnormal" in data["methods"]["iec"]
        assert "fault" not in data["methods"]["iec"]
        assert "code" not in data["methods"]["iec"]


# ============== 功能正确性 ==============

class TestFunctional:
    def test_overview_counts(self, client):
        data = _data(client.get("/api/data/overview"))
        assert data["total_transformers"] == 1
        assert data["total_records"] == 2

    def test_detect_latest_is_abnormal(self, client):
        """最新一条 c2h2=10 超标 → 阈值法判异常,投票异常。"""
        data = _data(client.get("/api/detect/methods/1"))
        assert data["methods"]["threshold"]["is_abnormal"] is True
        assert "c2h2" in data["methods"]["threshold"]["exceeded_gases"]
        assert data["vote"]["is_abnormal"] is True

    def test_detect_404_for_unknown(self, client):
        resp = client.get("/api/detect/methods/999")
        assert resp.status_code == 404


# ============== 内部接口标记 ==============

class TestInternal:
    def test_compare_has_warning_flag(self, client):
        data = _data(client.get("/api/detect/_internal/compare"))
        assert "_warning" in data
        assert "metrics" in data
