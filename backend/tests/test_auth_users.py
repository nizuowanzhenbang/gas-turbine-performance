def test_health(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_success(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "demo123"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "ADMIN"
    assert "access_token" in body
    assert body["expires_in"] > 0


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_me_endpoint(client, admin_token):
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "admin"


def test_me_no_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_bad_token(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_list_users_requires_admin(client, viewer_token, admin_token):
    r1 = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {viewer_token}"})
    assert r1.status_code == 403
    r2 = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {admin_token}"})
    assert r2.status_code == 200
    assert len(r2.json()) == 5


def test_create_user_lifecycle(client, auth):
    r = client.post("/api/v1/users/", headers=auth, json={
        "username": "newop", "full_name": "新员工", "password": "demo123",
        "role": "OPERATOR", "is_active": True,
    })
    assert r.status_code == 201
    new_id = r.json()["id"]

    # duplicate username
    r2 = client.post("/api/v1/users/", headers=auth, json={
        "username": "newop", "full_name": "x", "password": "demo123", "role": "OPERATOR", "is_active": True,
    })
    assert r2.status_code == 409

    # patch
    r3 = client.patch(f"/api/v1/users/{new_id}", headers=auth, json={"full_name": "更新的名字"})
    assert r3.status_code == 200 and r3.json()["full_name"] == "更新的名字"

    # delete
    r4 = client.delete(f"/api/v1/users/{new_id}", headers=auth)
    assert r4.status_code == 204

    # not found
    r5 = client.delete(f"/api/v1/users/{new_id}", headers=auth)
    assert r5.status_code == 404


def test_patch_user_password_then_login(client, auth):
    create = client.post("/api/v1/users/", headers=auth, json={
        "username": "passchange", "full_name": "x", "password": "demo123", "role": "VIEWER", "is_active": True,
    }).json()
    client.patch(f"/api/v1/users/{create['id']}", headers=auth, json={"password": "newpass1"})
    r = client.post("/api/v1/auth/login", json={"username": "passchange", "password": "newpass1"})
    assert r.status_code == 200
