import io

import pandas as pd

from app.services.fuel_cache import clear_cache, get_latest_fuel


def test_integration_fuel_update_bad_secret(client, auth):
    r = client.post("/api/v1/integration/fuel-update",
                    headers={**auth, "X-Integration-Secret": "wrong"},
                    json={"gas_source_code": "SRC-001", "lhv_kj_nm3": 35900.0, "timestamp": "2026-05-25T00:00:00Z"})
    assert r.status_code == 403


def test_integration_fuel_update_ok(client, auth):
    clear_cache()
    r = client.post("/api/v1/integration/fuel-update",
                    headers={**auth, "X-Integration-Secret": "gtp-integration-shared-secret"},
                    json={"gas_source_code": "SRC-001", "lhv_kj_nm3": 36000.0,
                          "wobbe_index_kj_nm3": 48000.0,
                          "timestamp": "2026-05-25T00:00:00Z"})
    assert r.status_code == 200
    cached = get_latest_fuel("SRC-001")
    assert cached and cached["lhv"] == 36000.0


def test_integration_fuel_update_invalid_lhv(client, auth):
    r = client.post("/api/v1/integration/fuel-update",
                    headers={**auth, "X-Integration-Secret": "gtp-integration-shared-secret"},
                    json={"gas_source_code": "SRC-001", "lhv_kj_nm3": -1.0, "timestamp": "2026-05-25T00:00:00Z"})
    assert r.status_code == 422


def test_upload_readings_csv(client, auth):
    df = pd.DataFrame([
        {"gas_turbine_code": "GT-01", "timestamp": "2026-05-25T00:00:00",
         "ambient_temp_c": 20, "fuel_flow_nm3_h": 60000, "gross_power_mw": 290},
        {"gas_turbine_code": "GT-01", "timestamp": "2026-05-25T00:01:00",
         "ambient_temp_c": 20.1, "fuel_flow_nm3_h": 60100, "gross_power_mw": 291},
    ])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    raw = buf.getvalue().encode("utf-8")
    r = client.post("/api/v1/upload/readings", headers=auth,
                    files={"file": ("data.csv", raw, "text/csv")})
    assert r.status_code == 201
    assert r.json()["inserted"] == 2


def test_upload_missing_columns(client, auth):
    df = pd.DataFrame([{"foo": 1}])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    raw = buf.getvalue().encode("utf-8")
    r = client.post("/api/v1/upload/readings", headers=auth,
                    files={"file": ("bad.csv", raw, "text/csv")})
    assert r.status_code == 400


def test_upload_unknown_turbine_code_is_error_row(client, auth):
    df = pd.DataFrame([
        {"gas_turbine_code": "GT-99", "timestamp": "2026-05-25T00:00:00",
         "ambient_temp_c": 20, "fuel_flow_nm3_h": 60000, "gross_power_mw": 290},
    ])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    raw = buf.getvalue().encode("utf-8")
    r = client.post("/api/v1/upload/readings", headers=auth,
                    files={"file": ("data.csv", raw, "text/csv")})
    assert r.status_code == 201
    body = r.json()
    assert body["inserted"] == 0
    assert body["error_count"] == 1


def test_upload_bad_extension(client, auth):
    r = client.post("/api/v1/upload/readings", headers=auth,
                    files={"file": ("data.txt", b"hello", "text/plain")})
    assert r.status_code == 400
