"""Tests del CRUD de clientes y su agregado de facturación."""

from tests.test_facturas import PAYLOAD


async def test_crud_y_total_facturado(auth):
    client, headers = auth
    for i, (nombre, nif) in enumerate([("Acme", "A1"), ("Beta", "B2"), ("Gamma", "G3")], start=1):
        r = await client.post("/api/v1/clientes", headers=headers, json={
            "nombre": nombre, "nif": nif, "direccion": "", "cp": "", "ciudad": "",
            "provincia": "", "pais": "España", "email": "", "telefono": "", "notas": "",
        })
        assert r.status_code == 201

    lista = await client.get("/api/v1/clientes", headers=headers)
    clientes = lista.json()
    assert [c["nombre"] for c in clientes] == ["Acme", "Beta", "Gamma"]
    assert all(c["total_facturado"] == "0.00" for c in clientes)

    acme = next(c for c in clientes if c["nombre"] == "Acme")
    p = dict(PAYLOAD, cliente_id=acme["id"],
             lineas=[{"concepto": "X", "cantidad": "1", "precio_unitario": "1000", "orden": 0}])
    assert (await client.post("/api/v1/facturas", headers=headers, json=p)).status_code == 201

    lista = await client.get("/api/v1/clientes", headers=headers)
    acme = next(c for c in lista.json() if c["nombre"] == "Acme")
    assert acme["total_facturado"] == "1060.00"
    assert acme["num_facturas"] == 1

    # Edición
    r = await client.put(f"/api/v1/clientes/{acme['id']}", headers=headers, json={
        "nombre": "Acme Renovada", "nif": "A1", "direccion": "", "cp": "", "ciudad": "",
        "provincia": "", "pais": "España", "email": "", "telefono": "", "notas": "",
    })
    assert r.status_code == 200 and r.json()["nombre"] == "Acme Renovada"

    # Eliminación conserva facturas
    r = await client.delete(f"/api/v1/clientes/{acme['id']}", headers=headers)
    assert r.status_code == 204
    facturas = await client.get("/api/v1/facturas", headers=headers)
    assert len(facturas.json()) == 1

    r = await client.get(f"/api/v1/clientes/{acme['id']}", headers=headers)
    assert r.status_code == 404