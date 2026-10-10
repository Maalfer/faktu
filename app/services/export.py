"""Exporta el 100% de los datos del usuario como un ZIP de CSVs.

Genera un archivo por cada tabla (clientes, facturas, líneas, gastos,
conceptos y configuración), con codificación UTF-8 con BOM (utf-8-sig) para que
Excel/Numbers/Sheets abran los acentos correctamente. Incluye un `README.txt`
con la descripción de columnas y la fecha de generación.
"""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ApiToken,
    Cliente,
    ConceptoTrimestre,
    ConfigAutonomo,
    Factura,
    Gasto,
    LineaFactura,
)


# Cabeceras explícitas = orden estable y fácil de mapear.
CLIENTES_HEADER = [
    "id", "nombre", "nif", "direccion", "cp", "ciudad", "provincia", "pais",
    "email", "telefono", "notas", "created_at",
]

FACTURAS_HEADER = [
    "id", "numero", "serie", "numero_completo", "sin_cliente", "fecha_emision", "estado",
    "metodo_cobro", "cliente_id", "cliente_nombre",
    "emisor_nombre", "emisor_nif", "emisor_direccion", "emisor_cp",
    "emisor_ciudad", "emisor_provincia", "emisor_pais",
    "emisor_email", "emisor_telefono",
    "receptor_nombre", "receptor_nif", "receptor_direccion", "receptor_cp",
    "receptor_ciudad", "receptor_provincia", "receptor_pais",
    "iva_porcentaje", "irpf_porcentaje",
    "base_imponible", "cuota_iva", "cuota_irpf", "total",
    "trimestre", "notas", "created_at", "updated_at",
]

LINEAS_HEADER = [
    "id", "factura_id", "factura_numero", "orden",
    "concepto", "cantidad", "precio_unitario", "importe",
]

GASTOS_HEADER = [
    "id", "concepto", "categoria", "fecha", "importe", "proveedor",
    "notas", "archivo", "archivo_nombre", "deducible", "trimestre", "created_at",
]

CONCEPTOS_HEADER = [
    "id", "year", "trimestre", "tipo", "concepto", "importe", "iva", "orden", "notas",
]

CONFIG_HEADER = [
    "id",
    "emisor_nombre", "emisor_nif", "emisor_direccion", "emisor_cp",
    "emisor_ciudad", "emisor_provincia", "emisor_pais",
    "emisor_email", "emisor_telefono",
    "serie_por_defecto", "iva_por_defecto", "irpf_por_defecto",
    "metodos_cobro", "updated_at",
]

API_TOKENS_HEADER = [
    "id", "name", "prefix", "created_at", "last_used_at", "revoked_at",
]


README_TXT = """Exportación completa de Faktu
==============================

Cada tabla de tu cuenta está en su propio CSV dentro de este ZIP.
Codificación: UTF-8 con BOM (utf-8-sig) — abre directamente en Excel,
Numbers y Google Sheets respetando tildes y caracteres especiales.
Separador: coma (,).  Comillas: estándar CSV (RFC 4180).

Generado: {generated_at}

Archivos
--------

- clientes.csv          — tus clientes / receptores de facturas
- facturas.csv          — facturas (cabeceras). El total es base + IVA - IRPF.
- lineas_factura.csv    — líneas de cada factura (relación por factura_id)
- gastos.csv            — gastos deducibles, con trimestre calculado
- conceptos.csv         — libro de conceptos por trimestre
- configuracion.csv     — datos del emisor y preferencias por defecto
- api_tokens.csv        — tokens de API (prefijo y fechas; nunca el secreto)

Notas
-----

- `importe`, `total`, `base_imponible`, `cuota_*`, `cantidad` y `precio_unitario`
  están en € con dos decimales (formato plano, p.ej. "1234.56"). Sin
  separador de miles.
- Las fechas están en ISO 8601: `YYYY-MM-DD` o `YYYY-MM-DDTHH:MM:SS+00:00`.
- Una factura con `cliente_id` vacío significa que es un borrador sin cliente
  asignado.
- Un gasto con `archivo` vacío no tiene adjunto. Los adjuntos NO se incluyen
  en este ZIP por seguridad y tamaño; descárgalos desde la app.
"""


def _csv_bytes(rows: list[dict[str, Any]], header: list[str]) -> bytes:
    """Serializa una lista de dicts a CSV UTF-8 con BOM, usando `header` como orden."""
    buf = io.StringIO()
    buf.write(",".join(f'"{h.replace(chr(34), chr(34) * 2)}"' for h in header))
    buf.write("\r\n")
    for row in rows:
        cells: list[str] = []
        for h in header:
            v = row.get(h)
            if v is None:
                v = ""
            elif isinstance(v, (int, float)):
                v = f"{v:.2f}" if isinstance(v, float) and h in _DECIMAL_COLS else str(v)
            elif isinstance(v, (list, tuple)):
                v = "|".join(str(x) for x in v)
            else:
                v = str(v)
            # escapar comillas y envolver siempre (RFC 4180)
            v = v.replace('"', '""')
            cells.append(f'"{v}"')
        buf.write(",".join(cells))
        buf.write("\r\n")
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


_DECIMAL_COLS = {
    "importe", "total", "base_imponible",
    "cuota_iva", "cuota_irpf",
    "cantidad", "precio_unitario",
    "iva_porcentaje", "irpf_porcentaje",
    "iva", "iva_por_defecto", "irpf_por_defecto",
}


async def build_export_zip(db: AsyncSession, user_id: int) -> bytes:
    """Genera en memoria un ZIP con todos los CSVs del usuario."""
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    clientes = (await db.scalars(
        select(Cliente).where(Cliente.user_id == user_id).order_by(Cliente.id)
    )).all()
    facturas = (await db.scalars(
        select(Factura)
        .where(Factura.user_id == user_id)
        .options(selectinload(Factura.lineas), selectinload(Factura.cliente))
        .order_by(Factura.fecha_emision, Factura.id)
    )).all()
    lineas = (await db.execute(
        select(LineaFactura, Factura)
        .join(Factura, LineaFactura.factura_id == Factura.id)
        .where(Factura.user_id == user_id)
        .options(selectinload(Factura.lineas))
        .order_by(LineaFactura.factura_id, LineaFactura.orden)
    )).all()
    gastos = (await db.scalars(
        select(Gasto).where(Gasto.user_id == user_id).order_by(Gasto.fecha, Gasto.id)
    )).all()
    conceptos = (await db.scalars(
        select(ConceptoTrimestre).where(ConceptoTrimestre.user_id == user_id)
        .order_by(ConceptoTrimestre.year, ConceptoTrimestre.trimestre,
                  ConceptoTrimestre.tipo, ConceptoTrimestre.orden)
    )).all()
    config = await db.scalar(
        select(ConfigAutonomo).where(ConfigAutonomo.user_id == user_id)
    )
    api_tokens = (await db.scalars(
        select(ApiToken).where(ApiToken.user_id == user_id).order_by(ApiToken.created_at)
    )).all()

    clientes_rows = [
        {
            "id": c.id, "nombre": c.nombre, "nif": c.nif, "direccion": c.direccion,
            "cp": c.cp, "ciudad": c.ciudad, "provincia": c.provincia, "pais": c.pais,
            "email": c.email, "telefono": c.telefono, "notas": c.notas,
            "created_at": c.created_at,
        } for c in clientes
    ]

    facturas_rows = [
        {
            "id": f.id, "numero": f.numero, "serie": f.serie, "sin_cliente": f.sin_cliente,
            "numero_completo": f.numero_completo,
            "fecha_emision": f.fecha_emision, "estado": f.estado,
            "metodo_cobro": f.metodo_cobro,
            "cliente_id": f.cliente_id, "cliente_nombre": (f.cliente.nombre if f.cliente else ""),
            "emisor_nombre": f.emisor_nombre, "emisor_nif": f.emisor_nif,
            "emisor_direccion": f.emisor_direccion, "emisor_cp": f.emisor_cp,
            "emisor_ciudad": f.emisor_ciudad, "emisor_provincia": f.emisor_provincia,
            "emisor_pais": f.emisor_pais, "emisor_email": f.emisor_email,
            "emisor_telefono": f.emisor_telefono,
            "receptor_nombre": f.receptor_nombre, "receptor_nif": f.receptor_nif,
            "receptor_direccion": f.receptor_direccion, "receptor_cp": f.receptor_cp,
            "receptor_ciudad": f.receptor_ciudad, "receptor_provincia": f.receptor_provincia,
            "receptor_pais": f.receptor_pais,
            "iva_porcentaje": f.iva_porcentaje, "irpf_porcentaje": f.irpf_porcentaje,
            "base_imponible": f.base_imponible, "cuota_iva": f.cuota_iva,
            "cuota_irpf": f.cuota_irpf, "total": f.total,
            "trimestre": f.trimestre, "notas": f.notas,
            "created_at": f.created_at, "updated_at": f.updated_at,
        } for f in facturas
    ]

    lineas_rows = [
        {
            "id": l.id, "factura_id": l.factura_id,
            "factura_numero": f_.numero_completo, "orden": l.orden,
            "concepto": l.concepto, "cantidad": l.cantidad,
            "precio_unitario": l.precio_unitario, "importe": l.importe,
        } for l, f_ in lineas
    ]

    gastos_rows = [
        {
            "id": g.id, "concepto": g.concepto, "categoria": g.categoria,
            "fecha": g.fecha, "importe": g.importe, "proveedor": g.proveedor,
            "notas": g.notas, "archivo": g.archivo, "archivo_nombre": g.archivo_nombre, "deducible": g.deducible,
            "trimestre": g.trimestre, "created_at": g.created_at,
        } for g in gastos
    ]

    conceptos_rows = [
        {
            "id": c.id, "year": c.year, "trimestre": c.trimestre,
            "tipo": c.tipo, "concepto": c.concepto,
            "importe": c.importe, "iva": c.iva, "orden": c.orden, "notas": c.notas,
        } for c in conceptos
    ]

    config_rows = []
    if config is not None:
        config_rows.append({
            "id": config.id, "emisor_nombre": config.emisor_nombre,
            "emisor_nif": config.emisor_nif, "emisor_direccion": config.emisor_direccion,
            "emisor_cp": config.emisor_cp, "emisor_ciudad": config.emisor_ciudad,
            "emisor_provincia": config.emisor_provincia, "emisor_pais": config.emisor_pais,
            "emisor_email": config.emisor_email, "emisor_telefono": config.emisor_telefono,
            "serie_por_defecto": config.serie_por_defecto,
            "iva_por_defecto": config.iva_por_defecto,
            "irpf_por_defecto": config.irpf_por_defecto,
            "metodos_cobro": config.metodos_cobro,
            "updated_at": config.updated_at,
        })

    api_tokens_rows = [
        {
            "id": t.id, "name": t.name, "prefix": t.prefix,
            "created_at": t.created_at, "last_used_at": t.last_used_at,
            "revoked_at": t.revoked_at,
        } for t in api_tokens
    ]

    files = {
        "clientes.csv":        _csv_bytes(clientes_rows, CLIENTES_HEADER),
        "facturas.csv":        _csv_bytes(facturas_rows, FACTURAS_HEADER),
        "lineas_factura.csv":  _csv_bytes(lineas_rows, LINEAS_HEADER),
        "gastos.csv":          _csv_bytes(gastos_rows, GASTOS_HEADER),
        "conceptos.csv":       _csv_bytes(conceptos_rows, CONCEPTOS_HEADER),
        "configuracion.csv":   _csv_bytes(config_rows, CONFIG_HEADER),
        "api_tokens.csv":      _csv_bytes(api_tokens_rows, API_TOKENS_HEADER),
        "README.txt":          README_TXT.format(generated_at=generated_at).encode("utf-8"),
    }

    out = io.BytesIO()
    with zipfile.ZipFile(out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, body in files.items():
            zf.writestr(name, body)
    return out.getvalue()
