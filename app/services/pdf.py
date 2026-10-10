"""Servicio de generación de PDF de facturas."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_ACCENT = colors.HexColor("#4f46e5")
_LIGHT = colors.HexColor("#f3f4f6")
_GRID = colors.HexColor("#d1d5db")

# Logo de la marca (si no existe, el PDF se genera sin imagen)
_LOGO = Path(__file__).resolve().parent.parent.parent / "app" / "static" / "assets" / "logo.png"


def _fmt(d) -> str:
    """4 835,50 (formato español)."""
    return f"{Decimal(str(d)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _euro(d) -> str:
    return f"{_fmt(d)} €"


def generar_pdf_factura(factura) -> bytes:
    """Genera una factura profesional en PDF a partir de un objeto Factura."""
    buf = BytesIO()
    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    body: list = []
    # ── Encabezado (logo + emisor + nº de factura) ──────────────────────────
    head_row = [
        Paragraph(
            f"<b>{factura.emisor_nombre or 'FACTURA'}</b><br/>"
            f"<font size=8 color=#6b7280>{factura.emisor_nif}<br/>"
            f"{factura.emisor_direccion}<br/>{factura.emisor_cp} {factura.emisor_ciudad}</font>",
            normal,
        ),
        Paragraph(
            "<font size=18><b>FACTURA</b></font><br/>"
            f"<font size=11 color=#6b7280>{factura.numero_completo}</font><br/>"
            f"<font size=9>Emitida: {factura.fecha_emision.strftime('%d/%m/%Y')}</font>",
            ParagraphStyle("num", parent=normal, fontSize=13, alignment=TA_RIGHT),
        ),
    ]
    head_cols = [100 * mm, 90 * mm]
    if _LOGO.exists():
        head_row.insert(0, Image(str(_LOGO), width=22 * mm, height=22 * mm))
        head_cols = [22 * mm, 78 * mm, 90 * mm]
    head = Table([head_row], colWidths=head_cols)
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
    ]))
    body.append(head)
    body.append(Spacer(1, 8 * mm))

    # ── Cliente + notas ─────────────────────────────────────────────────────
    cliente_html = (
        "<b>CLIENTE</b><br/><br/>"
        f"{factura.receptor_nombre}<br/>"
        f"<font size=8>{factura.receptor_nif}</font><br/>" if factura.receptor_nif else ""
    ) + (f"<font size=8>{factura.receptor_direccion}</font><br/>" if factura.receptor_direccion else "") + (
        f"<font size=8>{factura.receptor_cp} {factura.receptor_ciudad}</font>" if factura.receptor_ciudad else ""
    )
    cells = [Paragraph(cliente_html, normal)]
    cols = [190 * mm]
    if factura.notas.strip():
        cells.append(Paragraph("<b>NOTAS</b><br/><br/>" + factura.notas.replace("\n", "<br/>"), normal))
        cols = [120 * mm, 70 * mm]
    rec = Table([cells], colWidths=cols)
    rec.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    body.append(rec)
    body.append(Spacer(1, 8 * mm))

    # ── Líneas ──────────────────────────────────────────────────────────────
    data = [["Concepto", "Cantidad", "Precio unit.", "Importe"]]
    for l in factura.lineas:
        data.append([l.concepto, _fmt(l.cantidad), _euro(l.precio_unitario), _euro(l.importe)])

    line_table = Table(data, colWidths=[85 * mm, 25 * mm, 35 * mm, 45 * mm])
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    body.append(line_table)
    body.append(Spacer(1, 6 * mm))

    # ── Totales ─────────────────────────────────────────────────────────────
    totals: list[list[str]] = [
        ["Base imponible", _euro(factura.base_imponible)],
        [f"IVA ({factura.iva_porcentaje}%)", _euro(factura.cuota_iva)],
    ]
    if factura.cuota_irpf > 0:
        totals.append([f"IRPF ({factura.irpf_porcentaje}%)", f"-{_euro(factura.cuota_irpf)}"])
    totals.append(["TOTAL", _euro(factura.total)])

    tot_tab = Table(totals, colWidths=[110 * mm, 80 * mm], hAlign="RIGHT")
    tot_tab.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (1, -1), 13),
        ("TEXTCOLOR", (0, -1), (1, -1), _ACCENT),
        ("LINEABOVE", (0, -2), (-1, -1), 0.8, _ACCENT),
        ("INNERGRID", (0, 0), (-1, -2), 0.4, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, -1), (-1, -1), _LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    body.append(tot_tab)

    # ── Pie ─────────────────────────────────────────────────────────────────
    estado = {"pagada": "Pagada", "emitida": "Emitida", "borrador": "Borrador"}.get(factura.estado, factura.estado)
    body.append(Spacer(1, 10 * mm))
    body.append(Paragraph(
        f"<font size=7 color=#9ca3af>Generada con Faktu · {date.today().strftime('%d/%m/%Y')} "
        f"· Estado: {estado}</font>"
    ))

    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
        title=f"Factura {factura.numero_completo}", author=factura.emisor_nombre,
    )
    doc.build(body)
    return buf.getvalue()