"""Semilla de datos de DEMO para capturas y documentación.

Uso:
    .venv/bin/python -m scripts.seed_demo

Crea (o reemplaza) la cuenta «demo@faktu.app / demo1234» con:
- Datos del autónomo (configuración).
- 8 clientes con todos sus datos.
- ~22 facturas repartidas entre 2025 y 2026, varios estados y líneas.
- ~30 gastos con categorías variadas y un par de adjuntos PDF.
- Conceptos trimestrales para los dos años.

⚠️  Pensado para demos / capturas. NO ejecuta migraciones destructivas en la
base de datos completa: solo BORRA los datos de la cuenta demo para dejarlos
limpio y poblados de forma idempotente.
"""
from __future__ import annotations

import asyncio
import io
import random
from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.pdfgen import canvas
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    ApiToken,
    Cliente,
    ConceptoTrimestre,
    ConfigAutonomo,
    Factura,
    Gasto,
    LineaFactura,
    User,
)

DEMO_EMAIL = "demo@faktu.app"
DEMO_PASSWORD = "demo1234"
DEMO_NAME = "Marta Robles Diseño"

random.seed(42)


# ── Datos del autónomo ────────────────────────────────────────────────────────

EMISOR = {
    "emisor_nombre": "Marta Robles Diseño",
    "emisor_nif": "53812764B",
    "emisor_direccion": "Calle Almagro 28, 3º izq",
    "emisor_cp": "28010",
    "emisor_ciudad": "Madrid",
    "emisor_provincia": "Madrid",
    "emisor_pais": "España",
    "emisor_email": "hola@martarobles.es",
    "emisor_telefono": "+34 612 803 471",
    "serie_por_defecto": "F-",
    "iva_por_defecto": 21.0,
    "irpf_por_defecto": 15.0,
    "metodos_cobro": ["Transferencia", "Tarjeta", "Bizum", "Efectivo"],
}


CLIENTES = [
    {
        "nombre": "Estudio Atrio Arquitectura S.L.",
        "nif": "B87456123",
        "direccion": "Calle Velázquez 110, 5º",
        "cp": "28006", "ciudad": "Madrid", "provincia": "Madrid",
        "email": "facturacion@atrioarq.com", "telefono": "+34 911 234 567",
        "notas": "Cliente recurrente desde 2023. Pagos a 30 días.",
    },
    {
        "nombre": "Cafetería La Encina",
        "nif": "B12345678",
        "direccion": "Plaza Mayor 7",
        "cp": "37002", "ciudad": "Salamanca", "provincia": "Salamanca",
        "email": "laencina@gmail.com", "telefono": "+34 923 21 04 55",
        "notas": "",
    },
    {
        "nombre": "Bosque Verde Jardinería",
        "nif": "B56127349",
        "direccion": "Av. del Parque 42",
        "cp": "48001", "ciudad": "Bilbao", "provincia": "Vizcaya",
        "email": "info@bosqueverde.eu", "telefono": "+34 944 870 311",
        "notas": "",
    },
    {
        "nombre": "Carmen Saavedra Fotografía",
        "nif": "47891234X",
        "direccion": "Rúa do Vilar 18, 2º",
        "cp": "15705", "ciudad": "Santiago de Compostela", "provincia": "A Coruña",
        "email": "carmen@saavedrafoto.com", "telefono": "+34 698 221 447",
        "notas": "",
    },
    {
        "nombre": "Editorial Ribera del Duero",
        "nif": "A09876543",
        "direccion": "C/ Postas 23",
        "cp": "09400", "ciudad": "Aranda de Duero", "provincia": "Burgos",
        "email": "pagos@editorialribera.com", "telefono": "+34 947 50 22 19",
        "notas": "Editorial pequeña, paga a 15 días.",
    },
    {
        "nombre": "Wabi Consulting",
        "nif": "B71234567",
        "direccion": "Paseo de la Castellana 81, planta 14",
        "cp": "28046", "ciudad": "Madrid", "provincia": "Madrid",
        "email": "finanzas@wabi.es", "telefono": "+34 910 448 802",
        "notas": "",
    },
    {
        "nombre": "Asociación Cultural Lavapiés",
        "nif": "G28301122",
        "direccion": "Calle del Olmo 24",
        "cp": "28012", "ciudad": "Madrid", "provincia": "Madrid",
        "email": "tesoreria@aclava.org", "telefono": "+34 915 27 84 30",
        "notas": "Asociación sin ánimo de lucro (exenta de IVA).",
    },
    {
        "nombre": "Clínica Dental Sonríe+",
        "nif": "B90011234",
        "direccion": "Av. de Andalucía s/n",
        "cp": "29002", "ciudad": "Málaga", "provincia": "Málaga",
        "email": "admin@sonriemas.es", "telefono": "+34 952 33 61 80",
        "notas": "",
    },
]


# (lineas) — base para generar facturas. (cantidad, precio_unitario, concepto)
LINEAS_POOL = [
    [(Decimal("40"), Decimal("55"), "Diseño de identidad corporativa · jornada")],
    [(Decimal("3"), Decimal("150"), "Maquetación tríptico (3 pliegos)")],
    [(Decimal("1"), Decimal("250"), "Diseño landing page"), (Decimal("1"), Decimal("120"), "Maquetación responsive")],
    [(Decimal("2"), Decimal("320"), "Sesión fotográfica producto")],
    [(Decimal("12"), Decimal("48"), "Retoque fotográfico por imagen")],
    [(Decimal("1"), Decimal("850"), "Diseño cartel A2 para evento")],
    [(Decimal("5"), Decimal("95"), "Mantenimiento mensual web")],
    [(Decimal("1"), Decimal("420"), "Diseño etiqueta producto")],
    [(Decimal("8"), Decimal("60"), "Diseño plantilla newsletter")],
    [(Decimal("1"), Decimal("1200"), "Rediseño completo de sitio web")],
    [(Decimal("2"), Decimal("180"), "Iconografía personalizada (pack)")],
    [(Decimal("1"), Decimal("540"), "Identidad visual · fase 1 (moodboard)")],
]


def next_numero(existing: list[str]) -> str:
    nums = [int(n.split("/")[0]) for n in existing if "/" in n]
    n = (max(nums) if nums else 0) + 1
    return f"{n:02d}/2026" if date.today().year == 2026 else f"{n:02d}/{date.today().year}"


# Estados por fecha — pasado pagadas, presente emitidas, futuro borrador
def estado_para(fecha: date, hoy: date) -> str:
    if fecha > hoy:
        return "borrador"
    if fecha.month < hoy.month or fecha.year < hoy.year:
        return "pagada"
    if fecha.day + 7 < hoy.day:
        return "pagada"
    return "emitida"


# ── Gastos (categoría, importe medio, concepto, proveedor) ─────────────────────

GASTOS_TEMPLATES = [
    # (categoría, importe, concepto, proveedor)
    ("Software",       "48.00",  "Suscripción Figma Professional (mensual)",        "Figma, Inc."),
    ("Software",       "25.99",  "Adobe Creative Cloud · plan fotográfico",         "Adobe Systems"),
    ("Software",       "12.00",  "Dominio martarobles.es (renovación anual)",      "CDmon"),
    ("Software",       "9.99",   "1Password · plan individual (mensual)",          "AgileBits"),
    ("Material",       "62.40",  "Pack de muestras Pantone Coated",                 "Gráficas Tres"),
    ("Material",       "23.95",  "Bloc bocetos A3 · papel 200g",                    "Mungyo"),
    ("Material",       "18.50",  "Rotuladores Copic (set 6)",                       "Wonderful Pen"),
    ("Transporte",     "32.10",  "Bono transporte zona A (5 viajes)",               "Consorcio Madrid"),
    ("Transporte",     "14.50",  "Parking centro",                                  "SABA"),
    ("Transporte",     "48.60",  "Viaje AVE Madrid-Valencia (ida y vuelta)",        "Renfe"),
    ("Hostelería",     "21.45",  "Comida de trabajo con cliente Atrio",             "Restaurante Lacón"),
    ("Hostelería",     "9.80",   "Café + croissant (cliente nuevo)",                "Café Comercial"),
    ("Alojamiento",    "142.00", "Noche hotel cliente Salamanca",                   "Hotel Catalonia"),
    ("Alojamiento",    "98.50",  "Noche Airbnb visita cliente Bilbao",              "Airbnb"),
    ("Formación",      "169.00", "Curso UX Writing online",                         "Domestika"),
    ("Formación",      "55.00",  "Workshop branding (jornada completa)",            "Escuela de Diseño"),
    ("Mercadotecnia",  "45.00",  "Publicidad Instagram (campaña mes)",              "Meta Ads"),
    ("Mercadotecnia",  "18.00",  "Tarjetas de visita (250 uds.)",                   "Moo Print"),
    ("Varios",         "12.30",  "Limpieza material fotográfico",                   "Limpiezas Rápidas"),
    ("Varios",         "75.00",  "Gestoría trimestre 4",                            "Asesoría Montes"),
    ("Material",       "104.20", "Impresión A3 calidad estudio (10 uds.)",          "PixPrinting"),
    ("Software",       "39.00",  "Suscripción Notion Business (trimestral)",        "Notion Labs"),
    ("Hostelería",     "16.20",  "Cena equipo fin de proyecto",                     "La Mafia se sienta a la mesa"),
    ("Transporte",     "29.10",  "Gasolina trayecto cliente Málaga",                "Repsol"),
    ("Alojamiento",    "165.00", "2 noches hotel viaje Málaga (cliente Sonríe+)",   "Hotel Vincci"),
    ("Material",       "47.80",  "Calibrador color X-Rite i1Display",               "ColorConfidence"),
    ("Formación",      "89.00",  "Congreso Fotonoviembre (inscripción)",            "Fotonoviembre"),
    ("Varios",         "8.45",   "Material oficina (sobres, sellos, cinta)",        "Amazon Business"),
    ("Mercadotecnia",  "60.00",  "Actualización portfolio en Behance",              "Behance Pro"),
    ("Software",       "15.00",  "Renovación licencia Capture One",                 "Capture One"),
]


# ── Conceptos trimestrales ────────────────────────────────────────────────────

SEED_CONCEPTOS = {
    1: {
        "ingresos": [
            ("Diseño landing cliente Atrio",      Decimal("2200"), Decimal("21")),
            ("Mantenimiento web Wabi",           Decimal("950.00"), Decimal("21")),
        ],
        "gastos": [
            ("Suscripciones de software",         Decimal("180")),
            ("Material de oficina",               Decimal("95.40")),
        ],
    },
    2: {
        "ingresos": [
            ("Rediseño web completo",             Decimal("3200")),
            ("Sesión fotográfica producto",       Decimal("640")),
            ("Plantilla newsletter (pack 8)",     Decimal("480")),
        ],
        "gastos": [
            ("Publicidad Instagram (trimestral)", Decimal("135")),
            ("Viajes a clientes",                 Decimal("210.70")),
            ("Formación / cursos online",         Decimal("169")),
        ],
    },
}


def _stub_pdf(titulo: str, body: list[str]) -> bytes:
    """Genera un PDF mínimo para adjuntar a un gasto (ticket 'escaneado')."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 770, titulo)
    c.setFont("Helvetica", 10)
    y = 740
    for line in body:
        c.drawString(72, y, line)
        y -= 18
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(72, y - 30, "Documento generado para demo · Faktu")
    c.showPage()
    c.save()
    return buf.getvalue()


# ── Funciones de carga ────────────────────────────────────────────────────────

async def _wipe_user_data(db, user_id: int) -> None:
    await db.execute(delete(ApiToken).where(ApiToken.user_id == user_id))
    await db.execute(delete(LineaFactura).where(LineaFactura.factura_id.in_(select(Factura.id).where(Factura.user_id == user_id))))
    await db.execute(delete(Factura).where(Factura.user_id == user_id))
    await db.execute(delete(Gasto).where(Gasto.user_id == user_id))
    await db.execute(delete(Cliente).where(Cliente.user_id == user_id))
    await db.execute(delete(ConceptoTrimestre).where(ConceptoTrimestre.user_id == user_id))
    await db.execute(delete(ConfigAutonomo).where(ConfigAutonomo.user_id == user_id))


def _build_facturas(user: User) -> tuple[list[Factura], list[ConceptoTrimestre], list[date]]:
    """Genera facturas, conceptos y fechas de gastos para los años 2025 y 2026."""
    hoy = date.today()
    # Si hoy es 2026, también poblamos 2025 (cerrado).
    years = sorted({hoy.year, hoy.year - 1})
    fact_cards: list[tuple[date, int, list[tuple[Decimal, Decimal, str]], int | None]] = []
    # Por cada año: ~2-4 facturas por trimestre, mezclando clientes aleatorios.
    for y in years:
        for q in range(1, 5):
            n = random.randint(2, 4)
            for _ in range(n):
                mes = random.randint((q - 1) * 3 + 1, q * 3)
                dia = random.randint(1, 28)
                cliente_idx = random.randint(0, len(CLIENTES) - 1)
                lineas = random.choice(LINEAS_POOL)
                fact_cards.append((date(y, mes, dia), cliente_idx, lineas, None))

    return [], [], []  # placeholder — no usado, lo rellena el caller


async def run() -> None:
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing:
            await _wipe_user_data(db, existing.id)
            existing.full_name = DEMO_NAME
            existing.is_active = True
            user = existing
        else:
            user = User(
                email=DEMO_EMAIL,
                full_name=DEMO_NAME,
                hashed_password=hash_password(DEMO_PASSWORD),
                is_active=True,
            )
            db.add(user)

        await db.flush()

        # Config del autónomo
        cfg = ConfigAutonomo(user_id=user.id, **EMISOR)
        db.add(cfg)

        # Clientes
        clientes: list[Cliente] = []
        for c in CLIENTES:
            cli = Cliente(user_id=user.id, **c)
            db.add(cli)
            clientes.append(cli)
        await db.flush()

        # Facturas (cerradas 2025 + actual 2026)
        hoy = date.today()
        years = sorted({hoy.year, hoy.year - 1})
        numeros_por_anio: dict[int, list[str]] = {y: [] for y in years}

        for y in years:
            for q in range(1, 5):
                count = random.randint(3, 5)
                for _ in range(count):
                    mes = random.randint((q - 1) * 3 + 1, q * 3)
                    dia = random.randint(1, 28)
                    fecha = date(y, mes, dia)
                    cliente = random.choice(clientes)
                    lineas = random.choice(LINEAS_POOL)
                    num = f"{len(numeros_por_anio[y]) + 1:02d}/{y}"
                    numeros_por_anio[y].append(num)
                    metodo = random.choice(["Transferencia", "Tarjeta", "Bizum"])
                    estado = estado_para(fecha, hoy)
                    if y < hoy.year:
                        estado = "pagada"
                    if estado == "borrador":
                        # los borradores no tienen cliente
                        cliente_obj = None
                        receptor = "Borrador — pendiente de asignar"
                        receptor_nif = ""
                    else:
                        cliente_obj = cliente
                        receptor = cliente.nombre
                        receptor_nif = cliente.nif
                    fact = Factura(
                        user_id=user.id,
                        cliente_id=cliente_obj.id if cliente_obj else None,
                        numero=num,
                        serie=EMISOR["serie_por_defecto"],
                        fecha_emision=fecha,
                        emisor_nombre=EMISOR["emisor_nombre"],
                        emisor_nif=EMISOR["emisor_nif"],
                        emisor_direccion=EMISOR["emisor_direccion"],
                        emisor_cp=EMISOR["emisor_cp"],
                        emisor_ciudad=EMISOR["emisor_ciudad"],
                        emisor_provincia=EMISOR["emisor_provincia"],
                        emisor_pais=EMISOR["emisor_pais"],
                        emisor_email=EMISOR["emisor_email"],
                        emisor_telefono=EMISOR["emisor_telefono"],
                        receptor_nombre=receptor,
                        receptor_nif=receptor_nif,
                        receptor_direccion=cliente.direccion if cliente_obj else "",
                        receptor_cp=cliente.cp if cliente_obj else "",
                        receptor_ciudad=cliente.ciudad if cliente_obj else "",
                        receptor_provincia=cliente.provincia if cliente_obj else "",
                        receptor_pais=cliente.pais if cliente_obj else "España",
                        iva_porcentaje=Decimal("21"),
                        irpf_porcentaje=Decimal("15") if random.random() > 0.3 else Decimal("0"),
                        estado=estado,
                        metodo_cobro=metodo,
                        notas="" if random.random() > 0.25 else "Gracias por la confianza. Plazo de pago a 30 días desde la emisión.",
                    )
                    db.add(fact)
                    await db.flush()
                    for orden, (cant, precio, concepto) in enumerate(lineas):
                        db.add(LineaFactura(
                            factura_id=fact.id,
                            concepto=concepto,
                            cantidad=cant,
                            precio_unitario=precio,
                            orden=orden,
                        ))

        # Gastos — repartidos por todos los trimestres de los dos años
        for y in years:
            for q in range(1, 5):
                sample_size = random.randint(5, 8)
                sample = random.sample(GASTOS_TEMPLATES, k=min(sample_size, len(GASTOS_TEMPLATES)))
                for cat, imp, concepto, prov in sample:
                    mes = random.randint((q - 1) * 3 + 1, q * 3)
                    dia = random.randint(1, 28)
                    await db.flush()
                    g = Gasto(
                        user_id=user.id,
                        concepto=concepto,
                        categoria=cat,
                        fecha=date(y, mes, dia),
                        importe=Decimal(imp),
                        proveedor=prov,
                        notas="",
                    )
                    db.add(g)
                    await db.flush()
                    # Adjuntar PDF sólo a ~25% de los gastos y solo si no es 2026
                    if y < hoy.year and random.random() < 0.45 and not g.archivo:
                        pdf = _stub_pdf(
                            f"Ticket — {prov}",
                            [
                                f"Fecha: {fecha_str(g.fecha)}",
                                f"Concepto: {concepto}",
                                f"Importe: {imp} €",
                                "",
                                "Documento generado para demo · Faktu",
                            ],
                        )
                        dest_dir = settings.media_path / "gastos"
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        from uuid import uuid4
                        fname = f"{uuid4().hex[:12]}.pdf"
                        full = dest_dir / fname
                        full.write_bytes(pdf)
                        g.archivo = f"gastos/{fname}"

        # Conceptos trimestrales
        for y in years:
            for q, data in SEED_CONCEPTOS.items():
                for i, row in enumerate(data["ingresos"]):
                    concepto, importe, iva = row[0], row[1], (row[2] if len(row) > 2 else None)
                    db.add(ConceptoTrimestre(
                        user_id=user.id, year=y, trimestre=q, tipo="ingreso",
                        concepto=concepto, importe=importe, iva=iva, orden=i,
                    ))
                for i, row in enumerate(data["gastos"]):
                    concepto, importe = row[0], row[1]
                    db.add(ConceptoTrimestre(
                        user_id=user.id, year=y, trimestre=q, tipo="gasto",
                        concepto=concepto, importe=importe, iva=None, orden=i,
                    ))

        await db.commit()
        print("✅ Demo poblado:")
        print(f"   · usuario: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"   · {len(CLIENTES)} clientes")
        print(f"   · {sum(len(v) for v in numeros_por_anio.values())} facturas en {len(years)} años")
        print(f"   · {len(GASTOS_TEMPLATES) * 4} gastos aprox.")
        print(f"   · conceptos trimestrales en {len(years)} años")


def fecha_str(d: date) -> str:
    return d.strftime("%d/%m/%Y")


if __name__ == "__main__":
    asyncio.run(run())
