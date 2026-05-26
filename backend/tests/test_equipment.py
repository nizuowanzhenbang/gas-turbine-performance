def test_list_turbines(client, auth):
    r = client.get("/api/v1/gas-turbines/", headers=auth)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["code"] == "GT-01"


def test_create_turbine_admin(client, auth):
    payload = {
        "code": "GT-02", "name": "燃机 2 号", "manufacturer": "Siemens", "model": "SGT5-4000F",
        "rated_power_mw": 290.0, "rated_heat_rate_kj_kwh": 9200.0, "rated_efficiency": 0.39,
        "status": "STANDBY",
    }
    r = client.post("/api/v1/gas-turbines/", headers=auth, json=payload)
    assert r.status_code == 201
    assert r.json()["code"] == "GT-02"


def test_create_turbine_viewer_forbidden(client, viewer_token):
    r = client.post(
        "/api/v1/gas-turbines/",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "code": "GT-99", "name": "x", "rated_power_mw": 100, "rated_heat_rate_kj_kwh": 9000,
            "rated_efficiency": 0.4,
        },
    )
    assert r.status_code == 403


def test_create_turbine_perfeng_allowed(client, perfeng_token):
    r = client.post(
        "/api/v1/gas-turbines/",
        headers={"Authorization": f"Bearer {perfeng_token}"},
        json={
            "code": "GT-03", "name": "燃机 3 号", "rated_power_mw": 280, "rated_heat_rate_kj_kwh": 9300,
            "rated_efficiency": 0.39,
        },
    )
    assert r.status_code == 201


def test_create_turbine_invalid_code_pattern(client, auth):
    r = client.post("/api/v1/gas-turbines/", headers=auth, json={
        "code": "BAD-99", "name": "x", "rated_power_mw": 100,
        "rated_heat_rate_kj_kwh": 9000, "rated_efficiency": 0.4,
    })
    assert r.status_code == 422


def test_create_turbine_duplicate_conflict(client, auth):
    payload = {
        "code": "GT-01", "name": "x", "rated_power_mw": 100,
        "rated_heat_rate_kj_kwh": 9000, "rated_efficiency": 0.4,
    }
    r = client.post("/api/v1/gas-turbines/", headers=auth, json=payload)
    assert r.status_code == 409


def test_get_turbine_by_id(client, auth):
    list_r = client.get("/api/v1/gas-turbines/", headers=auth).json()
    gt_id = list_r[0]["id"]
    r = client.get(f"/api/v1/gas-turbines/{gt_id}", headers=auth)
    assert r.status_code == 200
    assert r.json()["code"] == "GT-01"


def test_get_turbine_not_found(client, auth):
    r = client.get("/api/v1/gas-turbines/9999", headers=auth)
    assert r.status_code == 404


def test_patch_turbine(client, auth):
    gt_id = client.get("/api/v1/gas-turbines/", headers=auth).json()[0]["id"]
    r = client.patch(f"/api/v1/gas-turbines/{gt_id}", headers=auth, json={"location": "1号机房"})
    assert r.status_code == 200
    assert r.json()["location"] == "1号机房"


def test_delete_turbine(client, auth):
    create = client.post("/api/v1/gas-turbines/", headers=auth, json={
        "code": "GT-04", "name": "可删", "rated_power_mw": 280,
        "rated_heat_rate_kj_kwh": 9300, "rated_efficiency": 0.39,
    }).json()
    r = client.delete(f"/api/v1/gas-turbines/{create['id']}", headers=auth)
    assert r.status_code == 204


def test_hrsg_crud(client, auth):
    r = client.get("/api/v1/hrsg/", headers=auth)
    assert r.status_code == 200 and len(r.json()) == 1
    r2 = client.post("/api/v1/hrsg/", headers=auth, json={
        "code": "HRSG-02", "name": "余热锅炉 2 号",
        "rated_hp_steam_t_h": 350, "rated_hp_pressure_mpa": 12.5, "rated_hp_temp_c": 565,
    })
    assert r2.status_code == 201


def test_steam_turbine_crud(client, auth):
    r = client.get("/api/v1/steam-turbines/", headers=auth)
    assert r.status_code == 200 and len(r.json()) == 1
    r2 = client.post("/api/v1/steam-turbines/", headers=auth, json={
        "code": "ST-02", "name": "汽轮机 2 号", "rated_power_mw": 130,
    })
    assert r2.status_code == 201


def test_cc_unit_create_and_list(client, auth):
    r = client.get("/api/v1/cc-units/", headers=auth)
    assert r.status_code == 200 and len(r.json()) == 1
    # 先建 GT/HRSG/ST 再建 CC
    gt = client.post("/api/v1/gas-turbines/", headers=auth, json={
        "code": "GT-05", "name": "x", "rated_power_mw": 280,
        "rated_heat_rate_kj_kwh": 9300, "rated_efficiency": 0.39,
    }).json()
    hr = client.post("/api/v1/hrsg/", headers=auth, json={
        "code": "HRSG-05", "name": "x",
    }).json()
    st = client.post("/api/v1/steam-turbines/", headers=auth, json={
        "code": "ST-05", "name": "x", "rated_power_mw": 120,
    }).json()
    r = client.post("/api/v1/cc-units/", headers=auth, json={
        "code": "CC-05", "name": "联合循环 5 号",
        "gas_turbine_id": gt["id"], "hrsg_id": hr["id"], "steam_turbine_id": st["id"],
        "rated_total_power_mw": 420,
    })
    assert r.status_code == 201


def test_cc_unit_missing_fk(client, auth):
    r = client.post("/api/v1/cc-units/", headers=auth, json={
        "code": "CC-99", "name": "x",
        "gas_turbine_id": 9999, "hrsg_id": 1, "steam_turbine_id": 1,
        "rated_total_power_mw": 420,
    })
    assert r.status_code == 400
