"""演示数据种子。

幂等：若 admin 用户已存在，直接退出。

运行方式：
    python -m app.seed_data
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.alert import Alert, AlertLevel, AlertStatus
from app.models.equipment import (
    CombinedCycleUnit,
    EquipmentStatus,
    GasTurbine,
    HRSGUnit,
    SteamTurbine,
)
from app.models.performance import PerformanceBaseline
from app.models.reading import OperationReading
from app.models.user import User, UserRole

random.seed(20260526)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.username == "admin")):
            print("[seed] admin 已存在，跳过")
            return

        _seed_users(db)
        gts = _seed_gas_turbines(db)
        hrsgs = _seed_hrsgs(db)
        sts = _seed_steam_turbines(db)
        _seed_cc_units(db, gts, hrsgs, sts)
        _seed_baselines(db, gts)
        _seed_readings(db, gts)
        _seed_alerts(db, gts)
        print("[seed] OK：" + ", ".join([
            f"{db.query(User).count()} users",
            f"{db.query(GasTurbine).count()} gas turbines",
            f"{db.query(HRSGUnit).count()} HRSGs",
            f"{db.query(SteamTurbine).count()} STs",
            f"{db.query(CombinedCycleUnit).count()} CC units",
            f"{db.query(PerformanceBaseline).count()} baselines",
            f"{db.query(OperationReading).count()} readings",
            f"{db.query(Alert).count()} alerts",
        ]))
    finally:
        db.close()


def _seed_users(db) -> None:
    db.add_all([
        User(username="admin", full_name="系统管理员",
             password_hash=hash_password("demo123"), role=UserRole.ADMIN),
        User(username="operator", full_name="集控运行员·张磊",
             password_hash=hash_password("demo123"), role=UserRole.OPERATOR),
        User(username="perfeng", full_name="性能工程师·李娜",
             password_hash=hash_password("demo123"), role=UserRole.PERFORMANCE_ENG),
        User(username="maintenance", full_name="检修工程师·王伟",
             password_hash=hash_password("demo123"), role=UserRole.MAINTENANCE),
        User(username="viewer", full_name="厂长·访问者",
             password_hash=hash_password("demo123"), role=UserRole.VIEWER),
    ])
    db.commit()


def _seed_gas_turbines(db) -> list[GasTurbine]:
    items = [
        GasTurbine(
            code="GT-01", name="燃机 1 号", manufacturer="GE", model="9F.04",
            serial_no="9F04-2019-021",
            commissioning_date=date(2019, 6, 15),
            rated_power_mw=298.0, rated_heat_rate_kj_kwh=9100.0, rated_efficiency=0.395,
            rated_egt_c=605.0, rated_speed_rpm=3000.0,
            status=EquipmentStatus.RUNNING, location="1 号燃机房",
            remarks="9F.04 改型，2024 年完成 C 检",
        ),
        GasTurbine(
            code="GT-02", name="燃机 2 号", manufacturer="Mitsubishi", model="M701F4",
            serial_no="M701F4-2020-007",
            commissioning_date=date(2020, 9, 22),
            rated_power_mw=312.0, rated_heat_rate_kj_kwh=8950.0, rated_efficiency=0.402,
            rated_egt_c=610.0, rated_speed_rpm=3000.0,
            status=EquipmentStatus.RUNNING, location="2 号燃机房",
        ),
    ]
    db.add_all(items)
    db.commit()
    for it in items:
        db.refresh(it)
    return items


def _seed_hrsgs(db) -> list[HRSGUnit]:
    items = [
        HRSGUnit(code="HRSG-01", name="余热锅炉 1 号", manufacturer="哈锅",
                 model="三压再热", rated_hp_steam_t_h=350.0, rated_hp_pressure_mpa=12.5,
                 rated_hp_temp_c=565.0, rated_ip_steam_t_h=90.0, rated_lp_steam_t_h=45.0,
                 rated_efficiency=0.86, status=EquipmentStatus.RUNNING),
        HRSGUnit(code="HRSG-02", name="余热锅炉 2 号", manufacturer="东锅",
                 model="三压再热", rated_hp_steam_t_h=360.0, rated_hp_pressure_mpa=12.5,
                 rated_hp_temp_c=565.0, rated_ip_steam_t_h=92.0, rated_lp_steam_t_h=46.0,
                 rated_efficiency=0.87, status=EquipmentStatus.RUNNING),
    ]
    db.add_all(items)
    db.commit()
    for it in items:
        db.refresh(it)
    return items


def _seed_steam_turbines(db) -> list[SteamTurbine]:
    items = [
        SteamTurbine(code="ST-01", name="汽轮机 1 号", manufacturer="上汽",
                     model="LZN130-12.5/3.4/0.45/565/565",
                     rated_power_mw=130.0, rated_efficiency=0.42, status=EquipmentStatus.RUNNING),
        SteamTurbine(code="ST-02", name="汽轮机 2 号", manufacturer="东汽",
                     model="LZN140-12.5/3.4/0.45/565/565",
                     rated_power_mw=140.0, rated_efficiency=0.43, status=EquipmentStatus.RUNNING),
    ]
    db.add_all(items)
    db.commit()
    for it in items:
        db.refresh(it)
    return items


def _seed_cc_units(db, gts, hrsgs, sts) -> None:
    items = [
        CombinedCycleUnit(code="CC-01", name="联合循环 1 号", configuration="1-1-1",
                          gas_turbine_id=gts[0].id, hrsg_id=hrsgs[0].id, steam_turbine_id=sts[0].id,
                          rated_total_power_mw=428.0, rated_cc_efficiency=0.58,
                          commissioning_date=date(2019, 12, 5), status=EquipmentStatus.RUNNING),
        CombinedCycleUnit(code="CC-02", name="联合循环 2 号", configuration="1-1-1",
                          gas_turbine_id=gts[1].id, hrsg_id=hrsgs[1].id, steam_turbine_id=sts[1].id,
                          rated_total_power_mw=452.0, rated_cc_efficiency=0.60,
                          commissioning_date=date(2021, 3, 18), status=EquipmentStatus.RUNNING),
    ]
    db.add_all(items)
    db.commit()


def _seed_baselines(db, gts) -> None:
    base_date = date.today() - timedelta(days=180)
    rows: list[PerformanceBaseline] = []
    for gt in gts:
        for load_pct in (50.0, 75.0, 100.0):
            # 简化：低负荷效率打折
            eff_factor = {50.0: 0.88, 75.0: 0.96, 100.0: 1.0}[load_pct]
            iso_eff = gt.rated_efficiency * eff_factor
            iso_hr = 3600.0 / iso_eff
            rows.append(PerformanceBaseline(
                gas_turbine_id=gt.id,
                baseline_date=base_date,
                baseline_type="COMMISSIONING",
                load_pct=load_pct,
                iso_corrected_power_mw=gt.rated_power_mw * load_pct / 100.0,
                iso_corrected_heat_rate_kj_kwh=iso_hr,
                iso_corrected_efficiency=iso_eff,
                iso_corrected_egt_c=580.0 + load_pct * 0.25,
                remarks=f"商运后基线 ({int(load_pct)}% 负荷)",
            ))
    db.add_all(rows)
    db.commit()


def _seed_readings(db, gts) -> None:
    """注入过去 24 小时、每 5 分钟一条的运行数据，模拟带负荷+少量退化。"""
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    rows: list[OperationReading] = []
    for gt in gts:
        for i in range(24 * 12):  # 288 条
            ts = now - timedelta(minutes=5 * i)
            hour = ts.hour
            load_pct = 100.0 if 7 <= hour <= 22 else random.uniform(60.0, 80.0)
            power = gt.rated_power_mw * load_pct / 100.0 * random.uniform(0.985, 1.005)
            ambient = 20.0 + 6.0 * math.sin(2 * math.pi * hour / 24)
            fuel_flow = power * 215.0  # 粗略：每 MW 约 215 Nm3/h
            egt_base = 580.0 + load_pct * 0.25 + random.uniform(-3, 3)
            tcs = [egt_base + random.uniform(-2.5, 2.5) for _ in range(6)]

            # GT-01 模拟轻度退化 + 偶发振动 C 区
            vib = 2.3 + random.uniform(0, 0.3)
            if gt.code == "GT-01":
                power *= 0.978
                if i < 6:  # 最近 30 分钟
                    vib = 5.2 + random.uniform(0, 0.5)
                    tcs[2] = egt_base + 55  # 模拟 TC#3 异常

            rows.append(OperationReading(
                gas_turbine_id=gt.id,
                timestamp=ts,
                ambient_temp_c=round(ambient, 2),
                ambient_pressure_kpa=101.0 + random.uniform(-0.4, 0.4),
                relative_humidity=round(random.uniform(0.45, 0.75), 3),
                fuel_flow_nm3_h=round(fuel_flow, 1),
                fuel_lhv_kj_nm3=35880.0,
                compressor_inlet_temp_c=round(ambient + 1.0, 2),
                compressor_inlet_pressure_kpa=101.0,
                compressor_outlet_temp_c=400.0 + load_pct * 0.6,
                compressor_outlet_pressure_kpa=1700.0,
                pressure_ratio=17.0,
                exhaust_temp_c=round(egt_base, 2),
                egt_t1_c=round(tcs[0], 2), egt_t2_c=round(tcs[1], 2), egt_t3_c=round(tcs[2], 2),
                egt_t4_c=round(tcs[3], 2), egt_t5_c=round(tcs[4], 2), egt_t6_c=round(tcs[5], 2),
                exhaust_flow_kg_s=600.0 + load_pct * 0.5,
                gross_power_mw=round(power, 2),
                speed_rpm=3000.0,
                igv_angle_deg=round(load_pct * 0.6, 1),
                bearing_temp_max_c=80.0 + load_pct * 0.05,
                vibration_mm_s=round(vib, 2),
                axial_displacement_mm=round(random.uniform(-0.3, 0.3), 2),
                hp_steam_flow_t_h=load_pct * 3.4,
                hp_steam_pressure_mpa=12.0,
                hp_steam_temp_c=560.0,
                st_power_mw=round(power * 0.43, 2),
                source="SIMULATED",
            ))
    db.bulk_save_objects(rows)
    db.commit()


def _seed_alerts(db, gts) -> None:
    now = datetime.now(timezone.utc)
    db.add_all([
        Alert(
            alert_no="AL-20260526-0001",
            gas_turbine_id=gts[0].id,
            category="DEGRADATION",
            level=AlertLevel.WARNING, status=AlertStatus.OPEN,
            title=f"{gts[0].code} 性能退化 3.42%",
            description="出力较基准下降超过 3%，建议安排在线水洗",
            measured_value=3.42, threshold=3.0, unit="%",
            triggered_at=now - timedelta(hours=2),
        ),
        Alert(
            alert_no="AL-20260526-0002",
            gas_turbine_id=gts[0].id,
            category="VIBRATION",
            level=AlertLevel.WARNING, status=AlertStatus.OPEN,
            title=f"{gts[0].code} 振动 5.40 mm/s 进入 C 区",
            description="ISO 10816 振动等级超阈，加密监测",
            measured_value=5.40, threshold=4.5, unit="mm/s",
            triggered_at=now - timedelta(minutes=15),
        ),
        Alert(
            alert_no="AL-20260526-0003",
            gas_turbine_id=gts[0].id,
            category="EGT_SPREAD",
            level=AlertLevel.WARNING, status=AlertStatus.ACKNOWLEDGED,
            title=f"{gts[0].code} EGT 散布 55.2°C（疑似热电偶 #3）",
            description="排气温度热电偶分散度超阈",
            measured_value=55.2, threshold=50.0, unit="°C",
            triggered_at=now - timedelta(hours=6),
            acknowledged_at=now - timedelta(hours=5),
            acknowledged_by="operator",
        ),
    ])
    db.commit()


if __name__ == "__main__":
    main()
