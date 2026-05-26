from datetime import datetime, timezone

from app.models.alert import Alert, AlertLevel, AlertStatus
from app.utils.numbering import next_alert_no


def _make_alert(db, gt_id, level=AlertLevel.WARNING):
    a = Alert(
        alert_no=next_alert_no(db),
        gas_turbine_id=gt_id,
        category="VIBRATION",
        level=level,
        title="测试告警",
        description="集成测试用",
        measured_value=5.5,
        threshold=4.5,
        unit="mm/s",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_alerts_list_empty(client, auth):
    r = client.get("/api/v1/alerts/", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


def test_alerts_list_with_data(client, auth, db_session):
    gt_id = client.get("/api/v1/gas-turbines/", headers=auth).json()[0]["id"]
    _make_alert(db_session, gt_id)
    _make_alert(db_session, gt_id, AlertLevel.CRITICAL)
    r = client.get("/api/v1/alerts/", headers=auth)
    assert r.status_code == 200
    assert len(r.json()) == 2

    r2 = client.get("/api/v1/alerts/?level=CRITICAL", headers=auth)
    assert len(r2.json()) == 1


def test_alert_ack_and_resolve_flow(client, auth, db_session):
    gt_id = client.get("/api/v1/gas-turbines/", headers=auth).json()[0]["id"]
    a = _make_alert(db_session, gt_id)
    r = client.post(f"/api/v1/alerts/{a.id}/ack", headers=auth, json={"remarks": "已确认"})
    assert r.status_code == 200
    assert r.json()["status"] == "ACKNOWLEDGED"
    assert r.json()["acknowledged_by"] == "admin"

    # 再次 ack 应失败
    r2 = client.post(f"/api/v1/alerts/{a.id}/ack", headers=auth, json={"remarks": ""})
    assert r2.status_code == 400

    r3 = client.post(f"/api/v1/alerts/{a.id}/resolve", headers=auth, json={"remarks": "更换轴承"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "RESOLVED"


def test_alert_resolve_not_found(client, auth):
    r = client.post("/api/v1/alerts/9999/resolve", headers=auth, json={"remarks": ""})
    assert r.status_code == 404


def test_dashboard_summary(client, auth):
    r = client.get("/api/v1/dashboard/summary", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["gas_turbines"]["total"] == 1
    assert body["gas_turbines"]["running"] == 1
    assert body["combined_cycle_units"] == 1
    assert "generation_24h_mwh" in body


def test_dashboard_summary_with_alerts(client, auth, db_session):
    gt_id = client.get("/api/v1/gas-turbines/", headers=auth).json()[0]["id"]
    _make_alert(db_session, gt_id, AlertLevel.CRITICAL)
    r = client.get("/api/v1/dashboard/summary", headers=auth)
    body = r.json()
    assert body["alerts"]["open"] == 1
    assert body["alerts"]["critical"] == 1


def test_dashboard_perf_trend(client, auth, seed_window_readings):
    gt_id = client.get("/api/v1/gas-turbines/", headers=auth).json()[0]["id"]
    seed_window_readings(gt_id, minutes=15)
    client.post("/api/v1/performance/calculate", headers=auth, json={
        "gas_turbine_id": gt_id, "window_minutes": 15,
    })
    r = client.get(f"/api/v1/dashboard/performance-trend?gas_turbine_id={gt_id}&days=30", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "series" in body
    assert len(body["series"]) >= 1
    assert "corrected_power_mw" in body["series"][0]
