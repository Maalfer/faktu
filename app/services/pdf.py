"""Servicio de generación de PDF de facturas."""
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_INK = colors.HexColor("#111827")
_MUTED = colors.HexColor("#6b7280")
_ACCENT = colors.HexColor("#1e1b4b")
_LIGHT = colors.HexColor("#f5f6fa")
_RULE = colors.HexColor("#e5e7eb")

_W = 180 * mm  # ancho útil (A4 - márgenes de 15 mm)


def _fmt(d) -> str:
    """4.835,50 (formato español)."""
    return f"{Decimal(str(d)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _euro(d) -> str:
    return f"{_fmt(d)} €"


def _qty(d) -> str:
    d = Decimal(str(d))
    return _fmt(d) if d != d.to_integral() else str(int(d))


def _pct(d) -> str:
    d = Decimal(str(d))
    return f"{d:.2f}".rstrip("0").rstrip(".") + " %"


def _e(text) -> str:
    return escape(str(text or "")).replace("\n", "<br/>")


def _style(name, **kw) -> ParagraphStyle:
    base = dict(fontName="Helvetica", fontSize=9, leading=12.5, textColor=_INK)
    base.update(kw)
    return ParagraphStyle(name, **base)


def _lines(*parts) -> str:
    return "<br/>".join(_e(p) for p in parts if p and str(p).strip())


def generar_pdf_factura(factura) -> bytes:
    """Genera una factura en PDF a partir de un objeto Factura."""
    buf = BytesIO()
    s_name = _style("name", fontName="Helvetica-Bold", fontSize=13, leading=17)
    s_small = _style("small", fontSize=8.5, leading=12, textColor=_MUTED)
    s_label = _style("label", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=_MUTED)
    s_text = _style("text")
    s_title = _style("title", fontName="Helvetica-Bold", fontSize=24, leading=28, alignment=TA_RIGHT, textColor=_ACCENT)
    s_right = _style("right", alignment=TA_RIGHT)
    s_right_muted = _style("rm", alignment=TA_RIGHT, textColor=_MUTED, fontSize=8.5)
    s_cell = _style("cell", leading=13)
    s_cell_r = _style("cellr", alignment=TA_RIGHT, leading=13)
    s_head = _style("head", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)
    s_head_r = _style("headr", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_RIGHT)

    body: list = []

    # ── Cabecera: emisor (izq.) · FACTURA, número y fecha (der.) ───────────
    ciudad = " ".join(x for x in (factura.emisor_cp, factura.emisor_ciudad) if x)
    emisor = [Paragraph(_e(factura.emisor_nombre), s_name)]
    detalle = _lines(
        f"NIF {factura.emisor_nif}" if factura.emisor_nif else "",
        factura.emisor_direccion, ciudad,
        factura.emisor_email, factura.emisor_telefono,
    )
    if detalle:
        emisor.append(Paragraph(detalle, s_small))
    numero = [
        Paragraph("FACTURA", s_title),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>Nº {_e(factura.numero_completo)}</b>", s_right),
        Paragraph(f"Fecha de emisión: {factura.fecha_emision.strftime('%d/%m/%Y')}", s_right_muted),
    ]
    head = Table([[emisor, numero]], colWidths=[_W * 0.55, _W * 0.45])
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    body += [head, Spacer(1, 7 * mm), HRFlowable(width=_W, thickness=1.2, hAlign="LEFT", color=_ACCENT), Spacer(1, 8 * mm)]

    # ── Cliente y forma de pago ─────────────────────────────────────────────
    ciudad_r = " ".join(x for x in (factura.receptor_cp, factura.receptor_ciudad) if x)
    cliente = [Paragraph("FACTURAR A", s_label), Spacer(1, 1.5 * mm), Paragraph(f"<b>{_e(factura.receptor_nombre)}</b>", s_text)]
    det_r = _lines(
        f"NIF {factura.receptor_nif}" if factura.receptor_nif else "",
        factura.receptor_direccion, ciudad_r,
        factura.receptor_provincia if factura.receptor_provincia and factura.receptor_provincia != factura.receptor_ciudad else "",
        factura.receptor_pais if factura.receptor_pais and factura.receptor_pais != "España" else "",
    )
    if det_r:
        cliente.append(Paragraph(det_r, s_small))
    celdas, anchos = [cliente], [_W]
    if (factura.notas or "").strip():
        notas = [Paragraph("FORMA DE PAGO / NOTAS", s_label), Spacer(1, 1.5 * mm), Paragraph(_e(factura.notas.strip()), s_small)]
        celdas, anchos = [cliente, notas], [_W * 0.45, _W * 0.55]
    bloque = Table([celdas], colWidths=anchos)
    bloque.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    body += [bloque, Spacer(1, 10 * mm)]

    # ── Líneas ──────────────────────────────────────────────────────────────
    data = [[Paragraph("CONCEPTO", s_head), Paragraph("CANT.", s_head_r),
             Paragraph("PRECIO UNIT.", s_head_r), Paragraph("IMPORTE", s_head_r)]]
    for l in factura.lineas:
        data.append([Paragraph(_e(l.concepto), s_cell), Paragraph(_qty(l.cantidad), s_cell_r),
                     Paragraph(_euro(l.precio_unitario), s_cell_r), Paragraph(_euro(l.importe), s_cell_r)])
    tabla = Table(data, colWidths=[_W * 0.52, _W * 0.11, _W * 0.18, _W * 0.19], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, _RULE),
    ]))
    body += [tabla, Spacer(1, 6 * mm)]

    # ── Totales (alineados con las columnas de la tabla) ────────────────────
    filas = [[Paragraph("Base imponible", s_text), Paragraph(_euro(factura.base_imponible), s_cell_r)],
             [Paragraph(f"IVA ({_pct(factura.iva_porcentaje)})", s_text), Paragraph(_euro(factura.cuota_iva), s_cell_r)]]
    if factura.cuota_irpf > 0:
        filas.append([Paragraph(f"IRPF (−{_pct(factura.irpf_porcentaje)})", s_text),
                      Paragraph(f"−{_euro(factura.cuota_irpf)}", s_cell_r)])
    s_tot = _style("tot", fontName="Helvetica-Bold", fontSize=12, textColor=_ACCENT)
    s_tot_r = _style("totr", fontName="Helvetica-Bold", fontSize=12, textColor=_ACCENT, alignment=TA_RIGHT)
    filas.append([Paragraph("TOTAL", s_tot), Paragraph(_euro(factura.total), s_tot_r)])
    ancho = _W * 0.19 + _W * 0.18 + _W * 0.11
    tot = Table(filas, colWidths=[ancho - _W * 0.19, _W * 0.19], hAlign="RIGHT")
    tot.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, -1), (-1, -1), 1, _ACCENT),
        ("BACKGROUND", (0, -1), (-1, -1), _LIGHT),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
    ]))
    body.append(tot)

    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
        leftMargin=15 * mm - 6, rightMargin=15 * mm - 6,
        title=f"Factura {factura.numero_completo}", author=factura.emisor_nombre,
    )
    doc.build(body)
    return buf.getvalue()
