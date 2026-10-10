"""Tests de gastos, archivos adjuntos y agregación por trimestres/dashboard."""

from tests.test_facturas import PAYLOAD


async def crear_gasto(client, headers, fecha="2026-09-01", importe=45.85, concepto="Gasolina"):
    r = await client.post("/api/v1/gastos", headers=headers, json={
        "concepto": concepto, "categoria": "Transporte", "fecha": fecha,
        "importe": importe, "proveedor": "Repsol", "notas": "",
    })
    assert r.status_code == 201, r.text
    return r.json()


async def test_crud_gastos(auth):
    client, headers = auth
    g = await crear_gasto(client, headers)
    assert g["trimestre"] == 3

    r = await client.put(f"/api/v1/gastos/{g['id']}", headers=headers, json={
        "concepto": "Gasolina (editado)", "categoria": "Transporte", "fecha": "2026-09-02",
        "importe": 50, "proveedor": "Repsol", "notas": "con IVA rescatado",
    })
    assert r.status_code == 200
    assert r.json()["importe"] == 50.0

    r = await client.delete(f"/api/v1/gastos/{g['id']}", headers=headers)
    assert r.status_code == 204
    r = await client.get(f"/api/v1/gastos/{g['id']}", headers=headers)
    assert r.status_code == 404


async def test_subida_y_descarga_de_archivo(auth):
    client, headers = auth
    g = await crear_gasto(client, headers)

    r = await client.post(
        f"/api/v1/gastos/{g['id']}/archivo", headers=headers,
        files={"archivo": ("ticket.jpg", b"\xff\xd8\xff\xe0data-de-prueba", "image/jpeg")},
    )
    assert r.status_code == 200
    assert r.json()["archivo"]

    r = await client.get(f"/api/v1/gastos/{g['id']}/archivo", headers=headers)
    assert r.status_code == 200
    assert r.content == b"\xff\xd8\xff\xe0data-de-prueba"

    # sin token -> 401
    r = await client.get(f"/api/v1/gastos/{g['id']}/archivo")
    assert r.status_code == 401


async def test_trimestres_agregan_y_ordenan(auth):
    client, headers = auth
    # Factura en T1 and una en T4
    for num, fecha in (("01/2026", "2026-01-10"), ("02/2026", "2026-11-20")):
        p = dict(PAYLOAD, numero=num, fecha_emision=fecha,
                 lineas=[{"concepto": "Consultoría", "cantidad": "1", "precio_unitario": "1000", "orden": 0}])
        assert (await client.post("/api/v1/facturas", headers=headers, json=p)).status_code == 201
    await crear_gasto(client, headers, fecha="2026-02-05", importe=100)

    r = await client.get("/api/v1/trimestres?year=2026", headers=headers)
    assert r.status_code == 200
    t = r.json()
    assert t["year"] == 2026
    cq = t["current_quarter"]
    order = [q["num"] for q in t["trimestres"]]
    assert order[0] == cq  # el trimestre actual va primero
    assert sorted(order) == [1, 2, 3, 4]

    t1 = next(q for q in t["trimestres"] if q["num"] == 1)
    assert t1["datos"]["total_facturado"] == "1060.00"  # 1000 + 21% - 15%
    assert t1["datos"]["total_gastos"] == "100.00"
    assert t1["datos"]["neto"] == "960.00"
    assert t1["is_past"] is True

    current = next(q for q in t["trimestres"] if q["is_current"])
    assert current["num"] == cq
    assert current["datos"]["total_facturado"] == "1060.00"

    r = await client.get("/api/v1/trimestres?year=2025", headers=headers)
    vacios = r.json()["trimestres"]
    assert len(vacios) == 4  # los 4 trimestres del año, sin datos
    assert all(q["datos"]["num_facturas"] == 0 and q["datos"]["total_gastos"] == "0" for q in vacios)


async def test_filtros_por_año_y_trimestre(auth):
    client, headers = auth
    await crear_gasto(client, headers, fecha="2025-06-01", importe=10, concepto="Año pasado")
    g = await crear_gasto(client, headers, fecha="2026-06-15", importe=20, concepto="T2 2026")

    r = await client.get("/api/v1/gastos?year=2025", headers=headers)
    assert [x["concepto"] for x in r.json()] == ["Año pasado"]
    r = await client.get("/api/v1/gastos?year=2026&trimestre=2", headers=headers)
    assert [x["id"] for x in r.json()] == [g["id"]]


async def test_dashboard(auth):
    client, headers = auth
    p = dict(PAYLOAD, numero="01/2026", fecha_emision="2026-01-10",
             lineas=[{"concepto": "X", "cantidad": "1", "precio_unitario": "1000", "orden": 0}])
    assert (await client.post("/api/v1/facturas", headers=headers, json=p)).status_code == 201
    await crear_gasto(client, headers, fecha="2026-01-15", importe=50)

    r = await client.get("/api/v1/dashboard?year=2026", headers=headers)
    d = r.json()
    assert d["year"] == 2026
    assert d["total_facturado"] == "1060.00"
    assert d["total_gastos"] == "50.00"
    assert d["total_neto"] == "1010.00"
    assert d["pendientes_cobro"] == 1

    r = await client.get("/api/v1/dashboard", headers=headers)
    assert r.json()["year"] == 2026  # el último año con datos

async def test_archivo_conserva_nombre_original_y_no_es_publico(auth):
    client, headers = auth
    g = await crear_gasto(client, headers)
    r = await client.post(
        f"/api/v1/gastos/{g['id']}/archivo", headers=headers,
        files={"archivo": ("2026-09-01 - Repsol - Gasolina.pdf", b"%PDF-1.4 prueba", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["archivo_nombre"] == "2026-09-01 - Repsol - Gasolina.pdf"
    r = await client.get(f"/api/v1/gastos/{g['id']}/archivo", headers=headers)
    assert "2026-09-01" in r.headers["content-disposition"]
    lst = await client.get("/api/v1/trimestres?year=2026", headers=headers)
    gasto = next(x for q in lst.json()["trimestres"] for x in q["gastos"] if x["id"] == g["id"])
    assert gasto["archivo_nombre"] == "2026-09-01 - Repsol - Gasolina.pdf"
    # los adjuntos no se sirven como estáticos: /media/... cae en la SPA, no en el PDF
    ruta = (await client.get(f"/api/v1/gastos/{g['id']}", headers=headers)).json()["archivo"]
    pub = await client.get(f"/media/{ruta}")
    assert not pub.content.startswith(b"%PDF")
