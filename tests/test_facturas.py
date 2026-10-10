"""Tests del CRUD de facturas, numeración, cálculos y PDF."""

PAYLOAD = {
    "numero": "01/2026",
    "serie": "",
    "fecha_emision": "2026-03-15",
    "cliente_id": None,
    "emisor_nombre": "Mario Demo S.L.",
    "emisor_nif": "B12345678",
    "emisor_direccion": "C/ Principal 1",
    "emisor_cp": "28001",
    "emisor_ciudad": "Madrid",
    "emisor_provincia": "Madrid",
    "emisor_pais": "España",
    "emisor_email": "mario@demo.es",
    "emisor_telefono": "600000000",
    "receptor_nombre": "Receptor S.A.",
    "receptor_nif": "A87654321",
    "receptor_direccion": "Av. Test 5",
    "receptor_cp": "46001",
    "receptor_ciudad": "Valencia",
    "receptor_provincia": "Valencia",
    "receptor_pais": "España",
    "iva_porcentaje": "21",
    "irpf_porcentaje": "15",
    "estado": "emitida",
    "metodo_cobro": "Transferencia",
    "notas": "Notas de prueba",
    "lineas": [
        {"concepto": "Servicio A", "cantidad": "2", "precio_unitario": "100", "orden": 0},
        {"concepto": "Servicio B", "cantidad": "1", "precio_unitario": "50", "orden": 1},
    ],
}
# base 250, IVA 52,50, IRPF 37,50 -> total 265,00


async def crear_cliente(client, headers, nombre="Cliente Test"):
    r = await client.post("/api/v1/clientes", headers=headers, json={
        "nombre": nombre, "nif": "B12345678", "direccion": "C/ 1", "cp": "28000",
        "ciudad": "Madrid", "provincia": "Madrid", "pais": "España", "email": "",
        "telefono": "", "notas": "",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def test_crear_factura_con_calculos(auth):
    client, headers = auth
    r = await client.post("/api/v1/facturas", headers=headers, json=PAYLOAD)
    assert r.status_code == 201, r.text
    f = r.json()
    assert f["base_imponible"] == "250.00"
    assert f["cuota_iva"] == "52.50"
    assert f["cuota_irpf"] == "37.50"
    assert f["total"] == "265.00"
    assert f["trimestre"] == 1
    assert len(f["lineas"]) == 2


async def test_numeracion_correlativa(auth):
    client, headers = auth
    for n in ("01/2026", "02/2026"):
        p = dict(PAYLOAD, numero=n)
        p["lineas"] = [{"concepto": "X", "cantidad": "1", "precio_unitario": "10", "orden": 0}]
        assert (await client.post("/api/v1/facturas", headers=headers, json=p)).status_code == 201

    r = await client.get("/api/v1/facturas/next-numero?year=2026", headers=headers)
    assert r.status_code == 200
    assert r.json()["numero"] == "03/2026"

    r = await client.get("/api/v1/facturas/next-numero?year=2027", headers=headers)
    assert r.json()["numero"] == "01/2027"


async def test_editar_y_eliminar(auth):
    client, headers = auth
    r = await client.post("/api/v1/facturas", headers=headers, json=PAYLOAD)
    fid = r.json()["id"]

    p = dict(PAYLOAD, estado="pagada", lineas=[{"concepto": "Solo", "cantidad": "1", "precio_unitario": "500", "orden": 0}])
    r = await client.put(f"/api/v1/facturas/{fid}", headers=headers, json=p)
    assert r.status_code == 200
    assert r.json()["estado"] == "pagada"
    assert len(r.json()["lineas"]) == 1
    assert r.json()["total"] == "530.00"

    r = await client.delete(f"/api/v1/facturas/{fid}", headers=headers)
    assert r.status_code == 204
    r = await client.get(f"/api/v1/facturas/{fid}", headers=headers)
    assert r.status_code == 404


async def test_con_cliente_guardado(auth):
    client, headers = auth
    cliente = await crear_cliente(client, headers)
    p = dict(PAYLOAD, cliente_id=cliente["id"])
    r = await client.post("/api/v1/facturas", headers=headers, json=p)
    assert r.status_code == 201
    assert r.json()["cliente"]["id"] == cliente["id"]

    # cliente no válido -> 422
    p2 = dict(PAYLOAD, cliente_id=999999)
    r = await client.post("/api/v1/facturas", headers=headers, json=p2)
    assert r.status_code == 422


async def test_pdf_descargable(auth):
    client, headers = auth
    fid = (await client.post("/api/v1/facturas", headers=headers, json=PAYLOAD)).json()["id"]
    r = await client.get(f"/api/v1/facturas/{fid}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"

    r2 = await client.get(f"/api/v1/facturas/{fid}/pdf")
    assert r2.status_code == 401


async def test_aislamiento_entre_usuarios(auth):
    client, headers = auth
    fid = (await client.post("/api/v1/facturas", headers=headers, json=PAYLOAD)).json()["id"]

    r = await client.post("/api/v1/auth/register", json={
        "email": "otro@test.es", "password": "clave-segura-123", "full_name": "Otro",
    })
    h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = await client.get(f"/api/v1/facturas/{fid}", headers=h2)
    assert r.status_code == 404
    r = await client.get("/api/v1/facturas", headers=h2)
    assert r.json() == []

async def test_zip_de_facturas_del_trimestre(auth):
    import io, zipfile

    client, headers = auth
    for fecha in ("2026-08-03", "2026-09-10", "2026-10-02"):
        r = await client.post("/api/v1/facturas", headers=headers, json={**PAYLOAD, "fecha_emision": fecha})
        assert r.status_code == 201, r.text
    r = await client.get("/api/v1/facturas/zip?year=2026&trimestre=3", headers=headers)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert len(zf.namelist()) == 2 and all(n.endswith(".pdf") for n in zf.namelist())
    assert zf.read(zf.namelist()[0]).startswith(b"%PDF")
    assert (await client.get("/api/v1/facturas/zip?year=2026&trimestre=1", headers=headers)).status_code == 404
