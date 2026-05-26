from datetime import datetime, timezone


def _gt_id(client, auth):
    return client.get("/api/v1/gas-turbines/", headers=auth).json()[0]["id"]


def test_create_reading(client, auth):
    gt_id = _gt_id(client, auth)
    r = client.post("/api/v1/readings/", headers=auth, json={
        "gas_turbine_id": gt_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gross_power_mw": 290.0, "fuel_flow_nm3_h": 60000.0,
    })
    assert r.status_code == 201


def test_create_reading_invalid_gt(client, auth):
    r = client.post("/api/v1/readings/", headers=auth, json={
        "gas_turbine_id": 9999,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gross_power_mw": 100,
    })
    assert r.status_code == 404


def test_batch_reading_insert(client, auth):
    gt_id = _gt_id(client, auth)
    rows = [{
        "gas_turbine_id": gt_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gross_power_mw": 290, "fuel_flow_nm3_h": 60000,
    } for _ in range(5)]
    r = client.post("/api/v1/readings/batch", headers=auth, json=rows)
    assert r.status_code == 201
    assert r.json()["inserted"] == 5


def test_list_readings_filter(client, auth, seed_window_readings):
    gt_id = _gt_id(client, auth)
    seed_window_readings(gt_id, minutes=10)
    r = client.get(f"/api/v1/readings/?gas_turbine_id={gt_id}", headers=auth)
    assert r.status_code == 200
    assert len(r.json()) >= 10


def test_performance_calculation_endpoint(client, auth, seed_window_readings):
    gt_id = _gt_id(client, auth)
    seed_window_readings(gt_id, minutes=15)
    r = client.post("/api/v1/performance/calculate", headers=auth, json={
        "gas_turbine_id": gt_id, "window_minutes": 15,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sample_count"] == 15
    assert body["corrected_power_mw"] > 0
    assert body["batch_no"].startswith("PERF-")
    assert body["cc_total_power_mw"] is not None  # 有 ST 数据


def test_performance_calculation_no_data(client, auth):
    gt_id = _gt_id(client, auth)
    r = client.post("/api/v1/performance/calculate", headers=auth, json={
        "gas_turbine_id": gt_id, "window_minutes": 15,
    })
    assert r.status_code == 400


def test_list_performance(client, auth, seed_window_readings):
    gt_id = _gt_id(client, auth)
    seed_window_readings(gt_id, minutes=15)
    client.post("/api/v1/performance/calculate", headers=auth, json={
        "gas_turbine_id": gt_id, "window_minutes": 15,
    })
    r = client.get("/api/v1/performance/", headers=auth)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_baseline_create_and_list(client, auth):
    gt_id = _gt_id(client, auth)
    r = client.post("/api/v1/baselines/", headers=auth, json={
        "gas_turbine_id": gt_id, "baseline_date": "2026-01-01",
        "baseline_type": "POST_OVERHAUL", "load_pct": 75,
        "iso_corrected_power_mw": 220, "iso_corrected_heat_rate_kj_kwh": 9200,
        "iso_corrected_efficiency": 0.391,
    })
    assert r.status_code == 201
    r2 = client.get("/api/v1/baselines/", headers=auth)
    assert r2.status_code == 200 and len(r2.json()) >= 1


def test_baseline_invalid_gt(client, auth):
    r = client.post("/api/v1/baselines/", headers=auth, json={
        "gas_turbine_id": 9999, "baseline_date": "2026-01-01",
        "load_pct": 100,
        "iso_corrected_power_mw": 298, "iso_corrected_heat_rate_kj_kwh": 9100,
        "iso_corrected_efficiency": 0.395,
    })
    assert r.status_code == 404


def test_baseline_delete(client, auth):
    gt_id = _gt_id(client, auth)
    bid = client.post("/api/v1/baselines/", headers=auth, json={
        "gas_turbine_id": gt_id, "baseline_date": "2026-02-01",
        "load_pct": 50, "iso_corrected_power_mw": 150,
        "iso_corrected_heat_rate_kj_kwh": 9500, "iso_corrected_efficiency": 0.379,
    }).json()["id"]
    r = client.delete(f"/api/v1/baselines/{bid}", headers=auth)
    assert r.status_code == 204
