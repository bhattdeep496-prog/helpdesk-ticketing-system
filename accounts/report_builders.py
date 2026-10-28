"""CSV / PDF file banane ke helpers (Django se independent)."""
import csv
import io
from xml.sax.saxutils import escape

# CSV me jo cell in characters se shuru ho, Excel use formula samajh leta hai.
_FORMULA_STARTS = ('=', '+', '-', '@', '\t', '\r')


def safe_cell(value):
    """CSV injection se bachav: formula jaise text ke aage ' laga do."""
    if value is None:
        return ''
    if isinstance(value, str) and value.startswith(_FORMULA_STARTS):
        return "'" + value
    return value


def csv_bytes(headers, rows):
    """UTF-8 (BOM ke saath, taaki Excel me sahi khule) CSV bytes."""
    buffer = io.StringIO()
    buffer.write('\ufeff')
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([safe_cell(c) for c in row])
    return buffer.getvalue().encode('utf-8')


def pdf_bytes(title, subtitle, headers, rows, col_widths_mm):
    """
    Landscape A4 table PDF. `reportlab` chahiye (pip install reportlab).
    Note: default font sirf Latin (English) text dikhata hai.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        'cell', parent=styles['BodyText'], fontSize=8, leading=10
    )
    head_style = ParagraphStyle(
        'head', parent=cell_style, textColor=colors.white,
        fontName='Helvetica-Bold',
    )

    data = [[Paragraph(escape(h), head_style) for h in headers]]
    for row in rows:
        data.append([
            Paragraph(escape('' if c is None else str(c)), cell_style)
            for c in row
        ])

    table = Table(
        data, colWidths=[w * mm for w in col_widths_mm], repeatRows=1
    )
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#f2f6fa')]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#b8c4d0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements = [
        Paragraph(escape(title), styles['Title']),
        Paragraph(escape(subtitle), styles['Normal']),
        Spacer(1, 6 * mm),
        table,
    ]
    doc.build(elements)
    return buffer.getvalue()