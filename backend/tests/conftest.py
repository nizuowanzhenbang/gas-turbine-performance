import os
import tempfile
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---- 必须在 import app 之前禁用 scheduler 并配置临时 DB --------------------
os.environ["SCHEDULER_ENABLED"] = "false"

_tmp_dir = tempfile.mkdtemp(prefix="gtp_test_")
_db_path = os.path.join(_tmp_dir, "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.equipment import (  # noqa: E402
    CombinedCycleUnit,
    EquipmentStatus,
    GasTurbine,
    HRSGUnit,
    SteamTurbine,
)
from app.models.performance import PerformanceBaseline  # noqa: E402
from app.models.reading import OperationReading  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def app():
    Base.metadata.create_all(bind=engine)
    a = create_app()
    a.dependency_overrides[get_db] = _override_get_db
    return a


@pytest.fixture(autouse=True)
def _reset_db(app):
    """每个测试隔离 DB 内容"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_users()
    _seed_equipment()
    yield


def _seed_users():
    db = TestingSessionLocal()
    try:
        users = [
            User(username="admin", full_name="管理员", password_hash=hash_password("demo123"), role=UserRole.ADMIN),
            User(username="operator", full_name="运行员", password_hash=hash_password("demo123"), role=UserRole.OPERATOR),
            User(username="perfeng", full_name="性能工程师", password_hash=hash_password("demo123"), role=UserRole.PERFORMANCE_ENG),
            User(username="maintenance", full_name="检修员", password_hash=hash_password("demo123"), role=UserRole.MAINTENANCE),
            User(username="viewer", full_name="访客", password_hash=hash_password("demo123"), role=UserRole.VIEWER),
        ]
        db.add_all(users)
        db.commit()
    finally:
        db.close()


def _seed_equipment():
    db = TestingSessionLocal()
    try:
        gt = GasTurbine(
            code="GT-01",
            name="燃机 1 号",
            manufacturer="GE",
            model="9F.04",
            rated_power_mw=298.0,
            rated_heat_rate_kj_kwh=9100.0,
            rated_efficiency=0.395,
            status=EquipmentStatus.RUNNING,
        )
        hrsg = HRSGUnit(
            code="HRSG-01",
            name="余热锅炉 1 号",
            rated_hp_steam_t_h=350.0,
            rated_hp_pressure_mpa=12.5,
            rated_hp_temp_c=565.0,
        )
        st = SteamTurbine(
            code="ST-01",
            name="汽轮机 1 号",
            rated_power_mw=130.0,
        )
        db.add_all([gt, hrsg, st])
        db.flush()
        cc = CombinedCycleUnit(
            code="CC-01",
            name="联合循环 1 号",
            gas_turbine_id=gt.id,
            hrsg_id=hrsg.id,
            steam_turbine_id=st.id,
            rated_total_power_mw=428.0,
            rated_cc_efficiency=0.58,
            status=EquipmentStatus.RUNNING,
        )
        baseline = PerformanceBaseline(
            gas_turbine_id=gt.id,
            baseline_date=date.today() - timedelta(days=180),
            baseline_type="COMMISSIONING",
            load_pct=100.0,
            iso_corrected_power_mw=298.0,
            iso_corrected_heat_rate_kj_kwh=9100.0,
            iso_corrected_efficiency=0.395,
            iso_corrected_egt_c=605.0,
        )
        db.add_all([cc, baseline])
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str, password: str = "demo123") -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def admin_token(client) -> str:
    return _login(client, "admin")


@pytest.fixture
def operator_token(client) -> str:
    return _login(client, "operator")


@pytest.fixture
def perfeng_token(client) -> str:
    return _login(client, "perfeng")


@pytest.fixture
def viewer_token(client) -> str:
    return _login(client, "viewer")


@pytest.fixture
def auth(admin_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def db_session() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_one_window_of_readings(gas_turbine_id: int, db_session, *, minutes: int = 15) -> None:
    """注入连续 N 分钟的运行读数 — 用于 perf 计算测试"""
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    rows = []
    for i in range(minutes):
        rows.append(OperationReading(
            gas_turbine_id=gas_turbine_id,
            timestamp=now - timedelta(minutes=minutes - 1 - i),
            ambient_temp_c=15.0,
            ambient_pressure_kpa=101.325,
            relative_humidity=0.60,
            fuel_flow_nm3_h=63000.0,
            fuel_lhv_kj_nm3=35880.0,
            gross_power_mw=295.0,
            exhaust_temp_c=608.0,
            egt_t1_c=608.0, egt_t2_c=606.0, egt_t3_c=609.0,
            egt_t4_c=607.0, egt_t5_c=608.5, egt_t6_c=607.5,
            vibration_mm_s=2.5,
            st_power_mw=130.0,
            source="SIMULATED",
        ))
    db_session.add_all(rows)
    db_session.commit()


@pytest.fixture
def seed_window_readings(db_session):
    """fixture 函数：caller 传 gt_id → 注入 15 分钟数据"""
    def _do(gas_turbine_id: int, minutes: int = 15):
        _seed_one_window_of_readings(gas_turbine_id, db_session, minutes=minutes)
    return _do
