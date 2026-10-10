"""Tests del flujo de autenticación."""

async def test_register_y_login(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "auth1@test.es", "password": "clave-segura-123", "full_name": "Ana",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "auth1@test.es"

    r2 = await client.post("/api/v1/auth/login", json={
        "email": "auth1@test.es", "password": "clave-segura-123",
    })
    assert r2.status_code == 200
    assert r2.json()["access_token"]


async def test_email_duplicado(client):
    payload = {"email": "dup@test.es", "password": "clave-segura-123", "full_name": ""}
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


async def test_login_incorrecto(client):
    r = await client.post("/api/v1/auth/login", json={"email": "x@test.es", "password": "mala"})
    assert r.status_code == 401


async def test_password_corta(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "corta@test.es", "password": "corta", "full_name": "",
    })
    assert r.status_code == 422


async def test_me_con_y_sin_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me(auth):
    client, headers = auth
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"].endswith("@test.es")