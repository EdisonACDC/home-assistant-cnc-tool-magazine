#!/usr/bin/env python3
"""CNC Tool Magazine Home Assistant app backend."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import signal
import sqlite3
import threading
import uuid
from io import BytesIO
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

APP_DIR = Path(__file__).resolve().parent
WWW_DIR = APP_DIR / "www"
TOOL_FIELDS = {
    "icon",
    "t_number",
    "d_offset",
    "h_offset",
    "diameter_mm",
    "length_mm",
    "description",
    "tool_type",
    "thread_pitch_mm",
    "flutes",
    "notes",
    "status",
    "usage_hours",
    "life_hours",
}
TOOL_STATUSES = {"new", "in_use", "to_sharpen", "maintenance", "worn"}
STATUS_LABELS = {"new": "Nuovo", "in_use": "In uso", "to_sharpen": "Da affilare", "maintenance": "In manutenzione", "worn": "Fuori servizio"}
TOOL_ICONS = {
    "",
    "end_mill",
    "roughing_mill",
    "ball_nose",
    "face_mill",
    "slitting_saw",
    "t_slot",
    "dovetail",
    "chamfer",
    "drill",
    "center_drill",
    "tap",
    "roll_tap",
    "thread_comb",
    "reamer",
    "boring_bar",
    "engraving",
    "probe",
    "custom",
}
TOOL_ICON_FILES = {"thread_comb": "tap"}
DEFAULT_TOOL_TYPE_COLORS = {
    "end_mill": "#2F80ED", "roughing_mill": "#1565C0", "ball_nose": "#56CCF2",
    "face_mill": "#00897B", "slitting_saw": "#6FCF97", "t_slot": "#27AE60",
    "dovetail": "#9B51E0", "chamfer": "#BB6BD9", "drill": "#F2994A",
    "center_drill": "#F2C94C", "tap": "#EB5757", "roll_tap": "#D84315",
    "thread_comb": "#C62828",
    "reamer": "#FF7043", "boring_bar": "#795548", "engraving": "#607D8B",
    "probe": "#455A64", "custom": "#7B8794",
}
CUTTING_FIELDS = {
    "material",
    "vc_m_min",
    "rpm",
    "fz_mm_tooth",
    "feed_mm_min",
    "ap_mm",
    "ae_mm",
    "coolant",
    "notes",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def qr_svg(value: str, size: int = 320) -> bytes:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or len(value) > 2048:
        raise ValueError("Indirizzo QR non valido")
    widget = qr.QrCodeWidget(value)
    x1, y1, x2, y2 = widget.getBounds()
    scale = size / max(x2 - x1, y2 - y1)
    drawing = Drawing(size, size, transform=[scale, 0, 0, scale, -x1 * scale, -y1 * scale])
    drawing.add(widget)
    return renderSVG.drawToString(drawing).encode("utf-8")


def _pdf_text(value: object, suffix: str = "") -> str:
    if value is None or value == "":
        return "-"
    return f"{escape(str(value))}{suffix}"


def _tool_is_occupied(tool: dict) -> bool:
    fields = ("description", "tool_type", "icon", "diameter_mm", "length_mm", "thread_pitch_mm", "flutes", "notes")
    return any(tool.get(field) not in (None, "") for field in fields) or bool(tool.get("cutting_parameters"))


def _tool_icon(icon_name: str) -> Image | str:
    path = WWW_DIR / "tool-icons" / f"{TOOL_ICON_FILES.get(icon_name, icon_name)}.png"
    if icon_name and path.is_file():
        return Image(str(path), width=15 * mm, height=15 * mm, kind="proportional")
    return ""


def _lighten_hex(value: str, amount: float = 0.82) -> colors.Color:
    value = value.lstrip("#")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return colors.Color(
        (red + (255 - red) * amount) / 255,
        (green + (255 - green) * amount) / 255,
        (blue + (255 - blue) * amount) / 255,
    )


def _compact_number(value: object) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def build_machine_table_pdf(tools: list[dict], machine: dict, type_colors: dict[str, str], exported_at: str) -> bytes:
    """Build the printable 30-position machine table with F/S material pairs."""
    output = BytesIO()
    page_width, page_height = landscape(A4)
    pdf = pdfcanvas.Canvas(output, pagesize=(page_width, page_height))
    pdf.setTitle("CNC - Tabella macchina")
    pdf.setAuthor("CNC Tool Magazine")
    by_slot = {int(tool["slot"]): tool for tool in tools}
    material_names: dict[str, str] = {}
    for tool in tools:
        for item in tool.get("cutting_parameters", []):
            name = str(item.get("material") or "").strip()
            if name:
                material_names.setdefault(name.casefold(), name)
    materials = [material_names[key] for key in sorted(material_names)]
    chunks = [materials[index:index + 5] for index in range(0, len(materials), 5)] or [[]]

    left = 9 * mm
    title_y = page_height - 10 * mm
    table_top = page_height - 24 * mm
    first_header_height = 6 * mm
    second_header_height = 5 * mm
    row_height = 5 * mm
    base_widths = [10 * mm, 7 * mm, 9 * mm, 9 * mm, 45 * mm]
    header_color = colors.HexColor("#183748")
    grid_color = colors.HexColor("#6F7F89")

    def centered_text(value: str, x_start: float, width: float, y: float, font: str = "Helvetica", size: float = 6.2):
        pdf.setFont(font, size)
        pdf.drawCentredString(x_start + width / 2, y, value)

    def fit_text(value: str, max_width: float, font: str, size: float) -> str:
        value = str(value)
        if pdf.stringWidth(value, font, size) <= max_width:
            return value
        while value and pdf.stringWidth(value + "...", font, size) > max_width:
            value = value[:-1]
        return value + "..."

    for page_index, material_chunk in enumerate(chunks):
        continuation = f" - materiali {page_index * 5 + 1}-{page_index * 5 + len(material_chunk)}" if len(chunks) > 1 else ""
        pdf.setFillColor(colors.HexColor("#183748"))
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left, title_y, f"Tabella utensili macchina{continuation}")
        pdf.setFillColor(colors.HexColor("#526875"))
        pdf.setFont("Helvetica", 6.5)
        pdf.drawString(left, title_y - 4 * mm, f"{machine.get('machine_name') or 'CNC'} - 30 posti - generata {exported_at.replace('T', ' ')}")

        widths = base_widths + [18 * mm] * (len(material_chunk) * 2)
        x_positions = [left]
        for width in widths:
            x_positions.append(x_positions[-1] + width)
        table_bottom = table_top - first_header_height - second_header_height - row_height * 30
        pdf.setStrokeColor(grid_color)
        pdf.setLineWidth(0.35)

        pdf.setFillColor(header_color)
        pdf.rect(left, table_top - first_header_height - second_header_height, sum(widths), first_header_height + second_header_height, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        fixed_headers = ("Icona", "T", "D", "H", "Descrizione utensile")
        for index, label in enumerate(fixed_headers):
            centered_text(label, x_positions[index], widths[index], table_top - 7.2 * mm, "Helvetica-Bold", 6.3)
        for index, material in enumerate(material_chunk):
            column = 5 + index * 2
            pair_width = widths[column] + widths[column + 1]
            centered_text(fit_text(material, pair_width - 2 * mm, "Helvetica-Bold", 6.3), x_positions[column], pair_width, table_top - 4.1 * mm, "Helvetica-Bold", 6.3)
            centered_text("F", x_positions[column], widths[column], table_top - 9.2 * mm, "Helvetica-Bold", 6.3)
            centered_text("S", x_positions[column + 1], widths[column + 1], table_top - 9.2 * mm, "Helvetica-Bold", 6.3)

        for slot in range(1, 31):
            tool = by_slot.get(slot, {"slot": slot, "cutting_parameters": []})
            occupied = _tool_is_occupied(tool)
            icon_name = tool.get("icon", "") if occupied else ""
            selected = type_colors.get(icon_name, DEFAULT_TOOL_TYPE_COLORS.get(icon_name, "#B0BEC5"))
            row_top = table_top - first_header_height - second_header_height - (slot - 1) * row_height
            row_bottom = row_top - row_height
            pdf.setFillColor(colors.HexColor(selected) if occupied else colors.HexColor("#ECEFF1"))
            pdf.rect(x_positions[0], row_bottom, widths[0], row_height, stroke=0, fill=1)
            pdf.setFillColor(_lighten_hex(selected) if occupied else colors.white)
            pdf.rect(x_positions[1], row_bottom, sum(widths[1:5]), row_height, stroke=0, fill=1)
            icon_path = WWW_DIR / "tool-icons" / f"{TOOL_ICON_FILES.get(icon_name, icon_name)}.png"
            if icon_name and icon_path.is_file():
                pdf.drawImage(str(icon_path), x_positions[0] + 2.9 * mm, row_bottom + .4 * mm, width=4.2 * mm, height=4.2 * mm, preserveAspectRatio=True, mask="auto")
            pdf.setFillColor(colors.HexColor("#17232D"))
            text_y = row_bottom + 1.65 * mm
            centered_text(str(slot), x_positions[1], widths[1], text_y)
            centered_text(_compact_number(tool.get("d_offset")) if occupied else "", x_positions[2], widths[2], text_y)
            centered_text(_compact_number(tool.get("h_offset")) if occupied else "", x_positions[3], widths[3], text_y)
            description = str(tool.get("description") or tool.get("tool_type") or "")
            pdf.setFont("Helvetica-Bold", 6.2)
            pdf.drawString(x_positions[4] + 1.2 * mm, text_y, fit_text(description, widths[4] - 2.4 * mm, "Helvetica-Bold", 6.2))
            cutting_by_name = {
                str(item.get("material") or "").strip().casefold(): item
                for item in tool.get("cutting_parameters", [])
            }
            for material_index, material in enumerate(material_chunk):
                cutting = cutting_by_name.get(material.casefold(), {})
                column = 5 + material_index * 2
                centered_text(_compact_number(cutting.get("feed_mm_min")), x_positions[column], widths[column], text_y)
                centered_text(_compact_number(cutting.get("rpm")), x_positions[column + 1], widths[column + 1], text_y)

        pdf.setStrokeColor(grid_color)
        header_split = table_top - first_header_height
        for column_index, x in enumerate(x_positions):
            is_material_middle = column_index >= 6 and column_index % 2 == 0
            pdf.line(x, table_bottom, x, header_split if is_material_middle else table_top)
        pdf.line(x_positions[5], header_split, x_positions[-1], header_split)
        pdf.line(left, table_top, x_positions[-1], table_top)
        pdf.line(left, table_top - first_header_height - second_header_height, x_positions[-1], table_top - first_header_height - second_header_height)
        for slot in range(31):
            y = table_top - first_header_height - second_header_height - slot * row_height
            pdf.line(left, y, x_positions[-1], y)
        pdf.setFillColor(colors.HexColor("#526875"))
        pdf.setFont("Helvetica", 6.5)
        pdf.drawString(left, 5 * mm, "F = avanzamento mm/min - S = giri/min")
        pdf.drawRightString(page_width - left, 5 * mm, f"Pagina {page_index + 1}/{len(chunks)}")
        pdf.showPage()

    pdf.save()
    return output.getvalue()


def build_pdf_report(
    tools: list[dict],
    machine: dict,
    exported_at: str,
    inventory: list[dict] | None = None,
    templates: list[dict] | None = None,
    events: list[dict] | None = None,
) -> bytes:
    """Build a complete printable report with active and archived tools."""
    output = BytesIO()
    page_width, page_height = landscape(A4)
    document = SimpleDocTemplate(
        output,
        pagesize=(page_width, page_height),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=14 * mm,
        title="CNC Tool Magazine - Rapporto completo",
        author="CNC Tool Magazine",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CncTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22,
        leading=25, textColor=colors.HexColor("#087f74"), alignment=TA_LEFT, spaceAfter=5 * mm,
    )
    h1 = ParagraphStyle(
        "CncH1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16,
        leading=19, textColor=colors.HexColor("#087f74"), spaceAfter=3 * mm,
    )
    h2 = ParagraphStyle(
        "CncH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11,
        leading=14, textColor=colors.HexColor("#183748"), spaceBefore=2 * mm, spaceAfter=2 * mm,
    )
    body = ParagraphStyle("CncBody", parent=styles["BodyText"], fontSize=8.5, leading=11)
    small = ParagraphStyle("CncSmall", parent=body, fontSize=7, leading=8.5)
    centered = ParagraphStyle("CncCentered", parent=small, alignment=TA_CENTER)
    header_bg = colors.HexColor("#087f74")
    line_color = colors.HexColor("#b8c8cf")
    alternate = colors.HexColor("#edf5f4")

    active_count = sum(_tool_is_occupied(tool) for tool in tools)
    archived_count = sum(len(tool.get("history", [])) for tool in tools)
    material_count = sum(
        len(tool.get("cutting_parameters", []))
        + sum(len(item.get("cutting_parameters", [])) for item in tool.get("history", []))
        for tool in tools
    )
    story = [
        Paragraph("CNC Tool Magazine", title_style),
        Paragraph(
            f"<b>Macchina:</b> {_pdf_text(machine.get('machine_name'))} &nbsp;&nbsp; "
            f"<b>Esportato:</b> {_pdf_text(exported_at.replace('T', ' '))}", body,
        ),
        Spacer(1, 3 * mm),
    ]
    summary = Table(
        [["Posizioni", "Utensili montati", "Utensili archiviati", "Schede materiale"],
         [str(len(tools)), str(active_count), str(archived_count), str(material_count)]],
        colWidths=[44 * mm] * 4,
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, 0), 8), ("FONTSIZE", (0, 1), (-1, 1), 15),
        ("GRID", (0, 0), (-1, -1), 0.5, line_color), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary, Spacer(1, 6 * mm), Paragraph("Panoramica delle 30 posizioni", h1)])

    overview = [[Paragraph(value, centered) for value in
                 ("Pos.", "Occupazione", "T", "D", "H", "Descrizione", "Tipo", "Diametro", "Lunghezza", "Condizione", "Vita", "Archivio")]]
    for tool in tools:
        occupied = _tool_is_occupied(tool)
        overview.append([
            Paragraph(str(tool["slot"]), centered), Paragraph("Montato" if occupied else "Libera", centered),
            Paragraph(_pdf_text(tool.get("t_number")), centered), Paragraph(_pdf_text(tool.get("d_offset")), centered),
            Paragraph(_pdf_text(tool.get("h_offset")), centered), Paragraph(_pdf_text(tool.get("description")), small),
            Paragraph(_pdf_text(tool.get("tool_type")), small), Paragraph(_pdf_text(tool.get("diameter_mm"), " mm"), centered),
            Paragraph(_pdf_text(tool.get("length_mm"), " mm"), centered),
            Paragraph(STATUS_LABELS.get(tool.get("status"), "-"), centered),
            Paragraph(_pdf_text(tool.get("remaining_percent"), "%"), centered),
            Paragraph(str(len(tool.get("history", []))), centered),
        ])
    overview_table = LongTable(
        overview, repeatRows=1,
        colWidths=[9 * mm, 17 * mm, 9 * mm, 9 * mm, 9 * mm, 43 * mm, 29 * mm, 21 * mm, 21 * mm, 25 * mm, 15 * mm, 15 * mm],
    )
    overview_style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, line_color), ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]
    for row_number in range(2, len(overview), 2):
        overview_style.append(("BACKGROUND", (0, row_number), (-1, row_number), alternate))
    overview_table.setStyle(TableStyle(overview_style))
    story.append(overview_table)

    def details_table(tool: dict) -> Table:
        data = [[
            _tool_icon(tool.get("icon", "")),
            Paragraph(f"<b>{_pdf_text(tool.get('description') or tool.get('tool_type') or 'Utensile senza descrizione')}</b>", body),
            Paragraph(f"<b>T:</b> {_pdf_text(tool.get('t_number'))}<br/><b>D:</b> {_pdf_text(tool.get('d_offset'))}<br/><b>H:</b> {_pdf_text(tool.get('h_offset'))}", body),
            Paragraph(f"<b>Diametro:</b> {_pdf_text(tool.get('diameter_mm'), ' mm')}<br/><b>Lunghezza:</b> {_pdf_text(tool.get('length_mm'), ' mm')}<br/><b>Passo:</b> {_pdf_text(tool.get('thread_pitch_mm'), ' mm')}<br/><b>Taglienti:</b> {_pdf_text(tool.get('flutes'))}", body),
            Paragraph(
                f"<b>Tipo:</b> {_pdf_text(tool.get('tool_type'))}<br/>"
                f"<b>Stato:</b> {_pdf_text(STATUS_LABELS.get(tool.get('status')))}<br/>"
                f"<b>Utilizzo:</b> {_pdf_text(tool.get('usage_hours_current', tool.get('usage_hours')), ' ore')} / {_pdf_text(tool.get('life_hours'), ' ore')}<br/>"
                f"<b>Documenti:</b> {_pdf_text(', '.join(item.get('original_name', '') for item in tool.get('attachments', [])))}<br/>"
                f"<b>Note:</b> {_pdf_text(tool.get('notes'))}", body,
            ),
        ]]
        table = Table(data, colWidths=[18 * mm, 58 * mm, 30 * mm, 48 * mm, 80 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f9fa")),
            ("BOX", (0, 0), (-1, -1), 0.5, line_color), ("INNERGRID", (0, 0), (-1, -1), 0.3, line_color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    def cutting_table(items: list[dict]) -> Table:
        rows = [[Paragraph(value, centered) for value in
                 ("Materiale", "Vc m/min", "giri/min", "fz mm/dente", "F mm/min", "ap mm", "ae mm", "Refrigerante", "Note")]]
        for item in items:
            rows.append([
                Paragraph(_pdf_text(item.get("material")), small), Paragraph(_pdf_text(item.get("vc_m_min")), centered),
                Paragraph(_pdf_text(item.get("rpm")), centered), Paragraph(_pdf_text(item.get("fz_mm_tooth")), centered),
                Paragraph(_pdf_text(item.get("feed_mm_min")), centered), Paragraph(_pdf_text(item.get("ap_mm")), centered),
                Paragraph(_pdf_text(item.get("ae_mm")), centered), Paragraph(_pdf_text(item.get("coolant")), small),
                Paragraph(_pdf_text(item.get("notes")), small),
            ])
        table = LongTable(rows, repeatRows=1, colWidths=[31 * mm, 21 * mm, 20 * mm, 25 * mm, 23 * mm, 18 * mm, 18 * mm, 35 * mm, 43 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183748")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, line_color), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return table

    for tool in tools:
        history = tool.get("history", [])
        if not _tool_is_occupied(tool) and not history:
            continue
        story.extend([PageBreak(), Paragraph(f"Posizione {tool['slot']}", h1)])
        if _tool_is_occupied(tool):
            story.extend([Paragraph("Utensile montato", h2), details_table(tool)])
            cuts = tool.get("cutting_parameters", [])
            story.extend([Paragraph("Parametri di taglio", h2), cutting_table(cuts)] if cuts else [Paragraph("Nessun parametro di taglio registrato.", body)])
        else:
            story.append(Paragraph("Posizione attualmente libera.", body))
        if history:
            story.extend([Spacer(1, 3 * mm), Paragraph(f"Archivio ({len(history)} utensili)", h1)])
        for index, archived in enumerate(history, start=1):
            archived_at = archived.get("archived_at", "").replace("T", " ")
            story.extend([
                Paragraph(f"Archivio {index} - {_pdf_text(archived.get('description') or archived.get('tool_type') or 'Utensile')} - {_pdf_text(archived_at)}", h2),
                details_table(archived),
            ])
            archived_cuts = archived.get("cutting_parameters", [])
            story.extend([Paragraph("Parametri di taglio archiviati", h2), cutting_table(archived_cuts)] if archived_cuts else [Paragraph("Nessun parametro di taglio archiviato.", body)])

    if inventory:
        story.extend([PageBreak(), Paragraph("Magazzino Officina", h1)])
        for item in inventory:
            story.extend([details_table(item), Spacer(1, 2 * mm)])
            if item.get("cutting_parameters"):
                story.extend([cutting_table(item["cutting_parameters"]), Spacer(1, 3 * mm)])

    if templates:
        story.extend([PageBreak(), Paragraph("Libreria materiali", h1)])
        rows = [["Materiale", "Vc", "Fz", "ap", "ae", "Refrigerazione", "Note"]]
        for item in templates:
            rows.append([
                item.get("name"), item.get("vc_m_min"), item.get("fz_mm_tooth"), item.get("ap_mm"),
                item.get("ae_mm"), item.get("coolant"), item.get("notes"),
            ])
        template_table = LongTable(rows, repeatRows=1, colWidths=[38 * mm, 18 * mm, 18 * mm, 16 * mm, 16 * mm, 42 * mm, 92 * mm])
        template_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_bg), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, line_color), ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(template_table)

    if events:
        story.extend([PageBreak(), Paragraph("Ultimi movimenti", h1)])
        for event in events[:100]:
            story.append(Paragraph(
                f"<b>{_pdf_text(event.get('created_at', '').replace('T', ' '))}</b> — {_pdf_text(event.get('description'))}", body
            ))
            story.append(Spacer(1, 3 * mm))

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(line_color)
        canvas.line(12 * mm, 10 * mm, page_width - 12 * mm, 10 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#526875"))
        canvas.drawString(12 * mm, 6 * mm, f"CNC Tool Magazine - {machine.get('machine_name', '')}")
        canvas.drawRightString(page_width - 12 * mm, 6 * mm, f"Pagina {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return output.getvalue()


def data_dir() -> Path:
    return Path(os.environ.get("CNC_DATA_DIR", "/data"))


def db_path() -> Path:
    return data_dir() / "cnc_tools.db"


def connect() -> sqlite3.Connection:
    data_dir().mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path())
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(slot_count: int = 30) -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS tools (
                slot INTEGER PRIMARY KEY CHECK(slot BETWEEN 1 AND 30),
                t_number INTEGER,
                d_offset INTEGER,
                h_offset INTEGER,
                diameter_mm REAL,
                length_mm REAL,
                description TEXT NOT NULL DEFAULT '',
                tool_type TEXT NOT NULL DEFAULT '',
                icon TEXT NOT NULL DEFAULT '',
                thread_pitch_mm REAL,
                flutes INTEGER,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'in_use',
                usage_hours REAL NOT NULL DEFAULT 0,
                life_hours REAL,
                timer_started_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS cutting_parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot INTEGER NOT NULL REFERENCES tools(slot) ON DELETE CASCADE,
                material TEXT NOT NULL COLLATE NOCASE,
                vc_m_min REAL,
                rpm INTEGER,
                fz_mm_tooth REAL,
                feed_mm_min REAL,
                ap_mm REAL,
                ae_mm REAL,
                coolant TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE(slot, material)
            );

            CREATE TABLE IF NOT EXISTS tool_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot INTEGER NOT NULL CHECK(slot BETWEEN 1 AND 30),
                tool_json TEXT NOT NULL,
                cutting_json TEXT NOT NULL,
                archived_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_uid TEXT NOT NULL UNIQUE,
                tool_json TEXT NOT NULL,
                cutting_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tool_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_uid TEXT NOT NULL,
                event_type TEXT NOT NULL,
                from_slot INTEGER,
                to_slot INTEGER,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS material_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                vc_m_min REAL,
                fz_mm_tooth REAL,
                ap_mm REAL,
                ae_mm REAL,
                coolant TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_uid TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS visel_settings (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                controller_model TEXT NOT NULL DEFAULT 'PentaMac',
                software_version TEXT NOT NULL DEFAULT '',
                host TEXT NOT NULL DEFAULT '',
                connection_type TEXT NOT NULL DEFAULT 'not_configured',
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tool_type_colors (
                icon TEXT PRIMARY KEY,
                color TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(tools)")}
        if "icon" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN icon TEXT NOT NULL DEFAULT ''")
        if "status" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN status TEXT NOT NULL DEFAULT 'in_use'")
        if "usage_hours" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN usage_hours REAL NOT NULL DEFAULT 0")
        if "life_hours" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN life_hours REAL")
        if "timer_started_at" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN timer_started_at TEXT")
        if "tool_uid" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN tool_uid TEXT")
        if "thread_pitch_mm" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN thread_pitch_mm REAL")
        db.executemany(
            "INSERT OR IGNORE INTO tools(slot, t_number, d_offset, h_offset) VALUES (?, ?, ?, ?)",
            ((slot, slot, slot, slot) for slot in range(1, slot_count + 1)),
        )
        occupied_rows = db.execute(
            """SELECT slot FROM tools WHERE tool_uid IS NULL AND
               (description != '' OR tool_type != '' OR icon != '' OR diameter_mm IS NOT NULL OR
                length_mm IS NOT NULL OR thread_pitch_mm IS NOT NULL OR flutes IS NOT NULL OR notes != '' OR
                EXISTS(SELECT 1 FROM cutting_parameters c WHERE c.slot = tools.slot))"""
        ).fetchall()
        for row in occupied_rows:
            db.execute("UPDATE tools SET tool_uid = ? WHERE slot = ?", (uuid.uuid4().hex, row["slot"]))
        starter_templates = [
            ("Acciaio C45", 180, 0.04, 0.5, 0.5, "Emulsione", "Valori iniziali: verificare con utensile e produttore"),
            ("Acciaio inox", 90, 0.03, 0.3, 0.3, "Emulsione abbondante", "Valori iniziali: verificare con utensile e produttore"),
            ("Alluminio", 350, 0.08, 1.0, 2.0, "Aria o emulsione", "Valori iniziali: verificare con utensile e produttore"),
            ("Ottone", 200, 0.06, 0.8, 1.0, "Aria", "Valori iniziali: verificare con utensile e produttore"),
        ]
        db.executemany(
            """INSERT OR IGNORE INTO material_templates
               (name, vc_m_min, fz_mm_tooth, ap_mm, ae_mm, coolant, notes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(*item, utc_now()) for item in starter_templates],
        )
        db.execute(
            """INSERT OR IGNORE INTO visel_settings
               (id, controller_model, software_version, host, connection_type, notes, updated_at)
               VALUES (1, 'PentaMac', '', '', 'not_configured', '', ?)""",
            (utc_now(),),
        )
        db.executemany(
            "INSERT OR IGNORE INTO tool_type_colors(icon, color, updated_at) VALUES (?, ?, ?)",
            [(icon, color, utc_now()) for icon, color in DEFAULT_TOOL_TYPE_COLORS.items()],
        )


def row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def list_tools() -> list[dict]:
    with connect() as db:
        tools = [row_to_dict(row) for row in db.execute("SELECT * FROM tools ORDER BY slot")]
        cuts = [
            row_to_dict(row)
            for row in db.execute("SELECT * FROM cutting_parameters ORDER BY slot, material COLLATE NOCASE")
        ]
        history_rows = [
            row_to_dict(row)
            for row in db.execute("SELECT * FROM tool_history ORDER BY slot, archived_at DESC, id DESC")
        ]
        attachment_rows = [
            row_to_dict(row)
            for row in db.execute("SELECT id, tool_uid, original_name, mime_type, size, created_at FROM attachments ORDER BY created_at DESC")
        ]
    by_slot: dict[int, list[dict]] = {}
    for item in cuts:
        by_slot.setdefault(item["slot"], []).append(item)
    for tool in tools:
        tool["cutting_parameters"] = by_slot.get(tool["slot"], [])
        tool["history"] = []
        usage = float(tool.get("usage_hours") or 0)
        if tool.get("timer_started_at"):
            try:
                started = datetime.fromisoformat(tool["timer_started_at"])
                usage += max(0, (datetime.now(timezone.utc) - started).total_seconds() / 3600)
            except (TypeError, ValueError):
                pass
        tool["usage_hours_current"] = round(usage, 3)
        life = tool.get("life_hours")
        tool["remaining_percent"] = max(0, min(100, round((1 - usage / life) * 100))) if life else None
    by_tool_slot = {tool["slot"]: tool for tool in tools}
    attachments_by_uid: dict[str, list[dict]] = {}
    for attachment in attachment_rows:
        attachments_by_uid.setdefault(attachment.pop("tool_uid"), []).append(attachment)
    for tool in tools:
        tool["attachments"] = attachments_by_uid.get(tool.get("tool_uid"), [])
    for item in history_rows:
        try:
            archived_tool = json.loads(item["tool_json"])
            archived_cuts = json.loads(item["cutting_json"])
        except (TypeError, ValueError):
            continue
        archived_tool.update(
            {
                "history_id": item["id"],
                "archived_at": item["archived_at"],
                "cutting_parameters": archived_cuts,
                "attachments": attachments_by_uid.get(archived_tool.get("tool_uid"), []),
            }
        )
        by_tool_slot[item["slot"]]["history"].append(archived_tool)
    return tools


def validation_report(tools: list[dict] | None = None) -> dict:
    """Return non-blocking consistency warnings for mounted tools."""
    mounted = [tool for tool in (tools or list_tools()) if _tool_is_occupied(tool)]
    warnings: list[dict] = []
    duplicate_fields = (
        ("t_number", "duplicate_t", "Numero T"),
        ("d_offset", "duplicate_d", "Correttore D"),
        ("h_offset", "duplicate_h", "Correttore H"),
    )
    for field, warning_type, label in duplicate_fields:
        grouped: dict[object, list[int]] = {}
        for tool in mounted:
            value = tool.get(field)
            if value not in (None, ""):
                grouped.setdefault(value, []).append(int(tool["slot"]))
        for value, slots in grouped.items():
            if len(slots) > 1:
                warnings.append({
                    "type": warning_type,
                    "severity": "warning",
                    "field": field,
                    "value": value,
                    "slots": slots,
                    "message": f"{label} {value} duplicato nelle posizioni {', '.join(map(str, slots))}",
                })
    for tool in mounted:
        diameter = tool.get("diameter_mm")
        if diameter in (None, "") or float(diameter) <= 0:
            slot = int(tool["slot"])
            warnings.append({
                "type": "missing_diameter",
                "severity": "warning",
                "field": "diameter_mm",
                "value": None,
                "slots": [slot],
                "message": f"Diametro mancante nella posizione {slot}",
            })
    affected = sorted({slot for warning in warnings for slot in warning["slots"]})
    return {"count": len(warnings), "warnings": warnings, "slots": affected}


def global_search(query: str) -> list[dict]:
    """Search mounted, archived, workshop and material-library data."""
    needle = str(query or "").strip().casefold()
    if not needle:
        return []
    if len(needle) > 120:
        raise ValueError("La ricerca è troppo lunga")
    results: list[dict] = []

    def searchable_tool(tool: dict) -> str:
        values = [
            tool.get("description"), tool.get("tool_type"), tool.get("notes"), tool.get("icon"),
            tool.get("diameter_mm"), tool.get("length_mm"), tool.get("thread_pitch_mm"), tool.get("flutes"),
            f"T{tool.get('t_number')}" if tool.get("t_number") is not None else "",
            f"D{tool.get('d_offset')}" if tool.get("d_offset") is not None else "",
            f"H{tool.get('h_offset')}" if tool.get("h_offset") is not None else "",
        ]
        for cut in tool.get("cutting_parameters", []):
            values.extend(cut.get(field) for field in (
                "material", "coolant", "vc_m_min", "rpm", "fz_mm_tooth", "feed_mm_min", "ap_mm", "ae_mm", "notes"
            ))
        return " ".join(str(value) for value in values if value not in (None, "")).casefold()

    def tool_detail(tool: dict) -> str:
        pitch = f" · P {tool['thread_pitch_mm']} mm" if tool.get("thread_pitch_mm") not in (None, "") else ""
        return (
            f"T{tool.get('t_number', '—')} · D{tool.get('d_offset', '—')} · "
            f"H{tool.get('h_offset', '—')} · Ø {tool.get('diameter_mm', '—')} mm{pitch}"
        )

    tools = list_tools()
    for tool in tools:
        if _tool_is_occupied(tool) and needle in searchable_tool(tool):
            results.append({
                "type": "active", "title": tool.get("description") or tool.get("tool_type") or "Utensile montato",
                "location": f"Posto {tool['slot']}", "detail": tool_detail(tool), "slot": tool["slot"],
                "cutting_parameters": tool.get("cutting_parameters", []),
            })
        for archived in tool.get("history", []):
            if needle in searchable_tool(archived):
                results.append({
                    "type": "history", "title": archived.get("description") or archived.get("tool_type") or "Utensile archiviato",
                    "location": f"Storico · posto {tool['slot']}", "detail": tool_detail(archived),
                    "slot": tool["slot"], "history_id": archived["history_id"],
                    "cutting_parameters": archived.get("cutting_parameters", []),
                })
        tool_groups = [("active", tool)] + [("history", item) for item in tool.get("history", [])]
        for kind, item in tool_groups:
            for attachment in item.get("attachments", []):
                if needle in attachment.get("original_name", "").casefold():
                    results.append({
                        "type": "document", "title": attachment["original_name"],
                        "location": f"Documento · {'posto' if kind == 'active' else 'storico posto'} {tool['slot']}",
                        "detail": item.get("description") or item.get("tool_type") or "Utensile",
                        "slot": tool["slot"], "history_id": item.get("history_id"), "attachment_id": attachment["id"],
                        "cutting_parameters": item.get("cutting_parameters", []),
                    })
    for tool in list_inventory():
        if needle in searchable_tool(tool):
            results.append({
                "type": "inventory", "title": tool.get("description") or tool.get("tool_type") or "Utensile",
                "location": "Officina", "detail": tool_detail(tool), "inventory_id": tool["inventory_id"],
                "cutting_parameters": tool.get("cutting_parameters", []),
            })
        for attachment in tool.get("attachments", []):
            if needle in attachment.get("original_name", "").casefold():
                results.append({
                    "type": "document", "title": attachment["original_name"], "location": "Documento · Officina",
                    "detail": tool.get("description") or tool.get("tool_type") or "Utensile",
                    "inventory_id": tool["inventory_id"], "attachment_id": attachment["id"],
                    "cutting_parameters": tool.get("cutting_parameters", []),
                })
    for template in list_material_templates():
        text = " ".join(str(template.get(field) or "") for field in (
            "name", "vc_m_min", "fz_mm_tooth", "ap_mm", "ae_mm", "coolant", "notes"
        )).casefold()
        if needle in text:
            results.append({
                "type": "material", "title": template["name"], "location": "Libreria materiali",
                "detail": f"Vc {template.get('vc_m_min') or '—'} · Fz {template.get('fz_mm_tooth') or '—'} · ap {template.get('ap_mm') or '—'} · ae {template.get('ae_mm') or '—'}",
                "template_id": template["id"],
            })
    return results[:100]


def list_inventory() -> list[dict]:
    with connect() as db:
        rows = db.execute("SELECT * FROM inventory_tools ORDER BY updated_at DESC, id DESC").fetchall()
        attachments = [row_to_dict(row) for row in db.execute(
            "SELECT id, tool_uid, original_name, mime_type, size, created_at FROM attachments ORDER BY created_at DESC"
        )]
    by_uid: dict[str, list[dict]] = {}
    for attachment in attachments:
        by_uid.setdefault(attachment.pop("tool_uid"), []).append(attachment)
    result = []
    for row in rows:
        tool = json.loads(row["tool_json"])
        tool.update({
            "inventory_id": row["id"],
            "tool_uid": row["tool_uid"],
            "cutting_parameters": json.loads(row["cutting_json"]),
            "attachments": by_uid.get(row["tool_uid"], []),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
        result.append(tool)
    return result


def list_events(limit: int = 200) -> list[dict]:
    with connect() as db:
        return [row_to_dict(row) for row in db.execute(
            "SELECT * FROM tool_events ORDER BY created_at DESC, id DESC LIMIT ?", (max(1, min(limit, 500)),)
        )]


def _record_event(
    db: sqlite3.Connection,
    tool_uid: str,
    event_type: str,
    description: str,
    from_slot: int | None = None,
    to_slot: int | None = None,
) -> None:
    db.execute(
        "INSERT INTO tool_events(tool_uid, event_type, from_slot, to_slot, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (tool_uid, event_type, from_slot, to_slot, description, utc_now()),
    )


def export_data() -> dict:
    return {
        "schema_version": 1,
        "exported_at": utc_now(),
        "machine": machine_options(),
        "tools": list_tools(),
        "inventory": list_inventory(),
        "material_templates": list_material_templates(),
        "events": list_events(500),
        "tool_type_colors": list_tool_type_colors(),
    }


def machine_options() -> dict:
    defaults = {"machine_name": "PentaMac / Visel", "magazine_slots": 30}
    options_path = Path("/data/options.json")
    try:
        supplied = json.loads(options_path.read_text(encoding="utf-8"))
        defaults.update({key: supplied[key] for key in defaults.keys() & supplied.keys()})
    except (OSError, ValueError, TypeError):
        pass
    defaults["magazine_slots"] = 30
    return defaults


def clean_value(field: str, value):
    if value in ("", None):
        return None if field not in {"description", "tool_type", "icon", "notes", "material", "coolant"} else ""
    if field in {"t_number", "d_offset", "h_offset", "flutes", "rpm"}:
        return int(value)
    if field in {"diameter_mm", "length_mm", "thread_pitch_mm", "usage_hours", "life_hours", "vc_m_min", "fz_mm_tooth", "feed_mm_min", "ap_mm", "ae_mm"}:
        return float(value)
    return str(value).strip()


def update_tool(slot: int, payload: dict) -> dict:
    values = {field: clean_value(field, payload[field]) for field in TOOL_FIELDS if field in payload}
    if "icon" in values and values["icon"] not in TOOL_ICONS:
        raise ValueError("Icona utensile non valida")
    if "status" in values and values["status"] not in TOOL_STATUSES:
        raise ValueError("Stato utensile non valido")
    if (values.get("usage_hours") or 0) < 0 or (values.get("life_hours") or 0) < 0:
        raise ValueError("Le ore non possono essere negative")
    if (values.get("thread_pitch_mm") or 0) < 0:
        raise ValueError("Il passo della filettatura non può essere negativo")
    if not values:
        raise ValueError("Nessun campo utensile valido")
    with connect() as db:
        current = db.execute("SELECT * FROM tools WHERE slot = ?", (slot,)).fetchone()
        if not current:
            raise LookupError("Posizione non trovata")
        usage = values.get("usage_hours", current["usage_hours"]) or 0
        life = values.get("life_hours", current["life_hours"])
        status = values.get("status", current["status"])
        if life and usage >= life and status not in {"worn", "maintenance"}:
            values["status"] = "to_sharpen"
        merged = row_to_dict(current)
        merged.update(values)
        if merged.get("icon") in {"tap", "roll_tap", "thread_comb"} and not (merged.get("thread_pitch_mm") or 0) > 0:
            raise ValueError("Inserisci il passo della filettatura")
        if not current["tool_uid"] and _has_tool_data(merged):
            values["tool_uid"] = uuid.uuid4().hex
            _record_event(db, values["tool_uid"], "created", f"Utensile creato nella posizione {slot}", to_slot=slot)
        values["updated_at"] = utc_now()
        assignments = ", ".join(f"{field} = ?" for field in values)
        result = db.execute(
            f"UPDATE tools SET {assignments} WHERE slot = ?",
            [*values.values(), slot],
        )
        if result.rowcount != 1:
            raise LookupError("Posizione non trovata")
        row = db.execute("SELECT * FROM tools WHERE slot = ?", (slot,)).fetchone()
    return row_to_dict(row)


def _reset_tool(db: sqlite3.Connection, slot: int) -> None:
    db.execute("DELETE FROM cutting_parameters WHERE slot = ?", (slot,))
    result = db.execute(
            """UPDATE tools SET t_number = ?, d_offset = ?, h_offset = ?,
               diameter_mm = NULL, length_mm = NULL, description = '', tool_type = '', icon = '',
               thread_pitch_mm = NULL, flutes = NULL, notes = '', status = 'in_use', usage_hours = 0, life_hours = NULL,
               timer_started_at = NULL, tool_uid = NULL, updated_at = ? WHERE slot = ?""",
            (slot, slot, slot, utc_now(), slot),
        )
    if result.rowcount != 1:
        raise LookupError("Posizione non trovata")


def reset_tool(slot: int) -> None:
    with connect() as db:
        _reset_tool(db, slot)


def _active_snapshot(db: sqlite3.Connection, slot: int) -> tuple[dict, list[dict]]:
    row = db.execute("SELECT * FROM tools WHERE slot = ?", (slot,)).fetchone()
    if not row:
        raise LookupError("Posizione non trovata")
    tool = row_to_dict(row)
    tool.pop("slot", None)
    cuts = []
    for cutting_row in db.execute("SELECT * FROM cutting_parameters WHERE slot = ? ORDER BY material", (slot,)):
        item = row_to_dict(cutting_row)
        item.pop("id", None)
        item.pop("slot", None)
        cuts.append(item)
    return tool, cuts


def _has_tool_data(tool: dict) -> bool:
    return any(tool.get(field) not in (None, "") for field in ("description", "tool_type", "diameter_mm", "length_mm", "thread_pitch_mm", "flutes", "notes"))


def _store_history(db: sqlite3.Connection, slot: int, tool: dict, cuts: list[dict]) -> int:
    cursor = db.execute(
        "INSERT INTO tool_history(slot, tool_json, cutting_json, archived_at) VALUES (?, ?, ?, ?)",
        (slot, json.dumps(tool, ensure_ascii=False), json.dumps(cuts, ensure_ascii=False), utc_now()),
    )
    return int(cursor.lastrowid)


def _settle_timer(db: sqlite3.Connection, slot: int) -> float:
    row = db.execute("SELECT usage_hours, life_hours, status, timer_started_at FROM tools WHERE slot = ?", (slot,)).fetchone()
    if not row:
        raise LookupError("Posizione non trovata")
    usage = float(row["usage_hours"] or 0)
    if row["timer_started_at"]:
        try:
            started = datetime.fromisoformat(row["timer_started_at"])
            usage += max(0, (datetime.now(timezone.utc) - started).total_seconds() / 3600)
        except (TypeError, ValueError):
            pass
    status = row["status"]
    if row["life_hours"] and usage >= row["life_hours"] and status not in {"worn", "maintenance"}:
        status = "to_sharpen"
    db.execute(
        "UPDATE tools SET usage_hours = ?, status = ?, timer_started_at = NULL, updated_at = ? WHERE slot = ?",
        (round(usage, 3), status, utc_now(), slot),
    )
    return usage


def start_usage(slot: int) -> None:
    with connect() as db:
        tool, cuts = _active_snapshot(db, slot)
        if not (_has_tool_data(tool) or cuts):
            raise ValueError("Inserisci prima un utensile nella posizione")
        if tool.get("timer_started_at"):
            raise ValueError("Il conteggio è già attivo")
        db.execute(
            "UPDATE tools SET timer_started_at = ?, status = 'in_use', updated_at = ? WHERE slot = ?",
            (utc_now(), utc_now(), slot),
        )


def stop_usage(slot: int) -> float:
    with connect() as db:
        row = db.execute("SELECT timer_started_at FROM tools WHERE slot = ?", (slot,)).fetchone()
        if not row:
            raise LookupError("Posizione non trovata")
        if not row["timer_started_at"]:
            raise ValueError("Il conteggio non è attivo")
        return _settle_timer(db, slot)


def archive_active_tool(slot: int) -> int:
    with connect() as db:
        _settle_timer(db, slot)
        tool, cuts = _active_snapshot(db, slot)
        if not _has_tool_data(tool):
            raise ValueError("Non c'è un utensile attivo da archiviare")
        history_id = _store_history(db, slot, tool, cuts)
        if tool.get("tool_uid"):
            _record_event(db, tool["tool_uid"], "archived", f"Utensile archiviato dalla posizione {slot}", from_slot=slot)
        _reset_tool(db, slot)
    return history_id


def activate_history_tool(slot: int, history_id: int) -> None:
    with connect() as db:
        archived = db.execute(
            "SELECT * FROM tool_history WHERE id = ? AND slot = ?", (history_id, slot)
        ).fetchone()
        if not archived:
            raise LookupError("Utensile storico non trovato")
        _settle_timer(db, slot)
        active_tool, active_cuts = _active_snapshot(db, slot)
        if _has_tool_data(active_tool):
            _store_history(db, slot, active_tool, active_cuts)
            if active_tool.get("tool_uid"):
                _record_event(
                    db, active_tool["tool_uid"], "archived", f"Utensile sostituito e archiviato nella posizione {slot}", from_slot=slot
                )

        selected_tool = json.loads(archived["tool_json"])
        selected_cuts = json.loads(archived["cutting_json"])
        _reset_tool(db, slot)
        values = _clean_tool_import({**selected_tool, "slot": slot}, slot)
        values["tool_uid"] = selected_tool.get("tool_uid") or uuid.uuid4().hex
        values["updated_at"] = utc_now()
        assignments = ", ".join(f"{field} = ?" for field in values)
        db.execute(f"UPDATE tools SET {assignments} WHERE slot = ?", [*values.values(), slot])
        for cutting in selected_cuts:
            cut_values = {field: cutting.get(field) for field in CUTTING_FIELDS}
            cut_values["updated_at"] = utc_now()
            columns = ["slot", *cut_values.keys()]
            db.execute(
                f"INSERT INTO cutting_parameters ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                [slot, *cut_values.values()],
            )
        db.execute("DELETE FROM tool_history WHERE id = ?", (history_id,))
        _record_event(db, values["tool_uid"], "mounted", f"Utensile montato dalla cronologia nella posizione {slot}", to_slot=slot)


def delete_history_tool(slot: int, history_id: int) -> None:
    with connect() as db:
        row = db.execute("SELECT tool_json FROM tool_history WHERE id = ? AND slot = ?", (history_id, slot)).fetchone()
        if not row:
            raise LookupError("Utensile storico non trovato")
        tool_uid = json.loads(row["tool_json"]).get("tool_uid")
        stored_files = []
        if tool_uid:
            stored_files = [item["stored_name"] for item in db.execute(
                "SELECT stored_name FROM attachments WHERE tool_uid = ?", (tool_uid,)
            )]
            db.execute("DELETE FROM attachments WHERE tool_uid = ?", (tool_uid,))
        db.execute("DELETE FROM tool_history WHERE id = ? AND slot = ?", (history_id, slot))
    for stored_name in stored_files:
        (attachments_dir() / stored_name).unlink(missing_ok=True)


def update_history_icon(slot: int, history_id: int, icon: str) -> None:
    icon = clean_value("icon", icon)
    if icon not in TOOL_ICONS:
        raise ValueError("Icona utensile non valida")
    with connect() as db:
        row = db.execute(
            "SELECT tool_json FROM tool_history WHERE id = ? AND slot = ?", (history_id, slot)
        ).fetchone()
        if not row:
            raise LookupError("Utensile storico non trovato")
        tool = json.loads(row["tool_json"])
        tool["icon"] = icon
        db.execute(
            "UPDATE tool_history SET tool_json = ? WHERE id = ? AND slot = ?",
            (json.dumps(tool, ensure_ascii=False), history_id, slot),
        )


def upsert_cutting(slot: int, payload: dict) -> dict:
    values = {field: clean_value(field, payload.get(field)) for field in CUTTING_FIELDS}
    if not values["material"]:
        raise ValueError("Il materiale è obbligatorio")
    values["updated_at"] = utc_now()
    columns = ["slot", *values.keys()]
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{field} = excluded.{field}" for field in values if field != "material")
    with connect() as db:
        exists = db.execute("SELECT tool_uid FROM tools WHERE slot = ?", (slot,)).fetchone()
        if not exists:
            raise LookupError("Posizione non trovata")
        if not exists["tool_uid"]:
            tool_uid = uuid.uuid4().hex
            db.execute("UPDATE tools SET tool_uid = ? WHERE slot = ?", (tool_uid, slot))
            _record_event(db, tool_uid, "created", f"Utensile creato nella posizione {slot}", to_slot=slot)
        db.execute(
            f"""INSERT INTO cutting_parameters ({', '.join(columns)}) VALUES ({placeholders})
                ON CONFLICT(slot, material) DO UPDATE SET {updates}""",
            [slot, *values.values()],
        )
        row = db.execute(
            "SELECT * FROM cutting_parameters WHERE slot = ? AND material = ? COLLATE NOCASE",
            (slot, values["material"]),
        ).fetchone()
    return row_to_dict(row)


def delete_cutting(slot: int, item_id: int) -> None:
    with connect() as db:
        result = db.execute("DELETE FROM cutting_parameters WHERE id = ? AND slot = ?", (item_id, slot))
        if result.rowcount != 1:
            raise LookupError("Parametro non trovato")


def _clean_tool_import(raw: object, expected_slot: int) -> dict:
    if not isinstance(raw, dict) or raw.get("slot") != expected_slot:
        raise ValueError(f"Dati non validi per la posizione {expected_slot}")
    defaults = {"status": "in_use", "usage_hours": 0, "life_hours": None}
    values = {field: clean_value(field, raw.get(field, defaults.get(field))) for field in TOOL_FIELDS}
    values["status"] = values["status"] or "in_use"
    values["usage_hours"] = values["usage_hours"] or 0
    if values["icon"] not in TOOL_ICONS:
        raise ValueError(f"Icona non valida nella posizione {expected_slot}")
    if values["status"] not in TOOL_STATUSES:
        raise ValueError(f"Stato non valido nella posizione {expected_slot}")
    if values["usage_hours"] < 0 or (values["life_hours"] is not None and values["life_hours"] < 0):
        raise ValueError(f"Ore non valide nella posizione {expected_slot}")
    if values["thread_pitch_mm"] is not None and values["thread_pitch_mm"] < 0:
        raise ValueError(f"Passo filettatura non valido nella posizione {expected_slot}")
    return values


def _clean_cutting_import(raw: object, context: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"Parametri di taglio non validi: {context}")
    values = {field: clean_value(field, raw.get(field)) for field in CUTTING_FIELDS}
    if not values["material"]:
        raise ValueError(f"Materiale mancante: {context}")
    return values


def _validate_import(payload: dict) -> list[dict]:
    if payload.get("schema_version") != 1:
        raise ValueError("Versione del backup non supportata")
    raw_tools = payload.get("tools")
    if not isinstance(raw_tools, list) or len(raw_tools) != 30:
        raise ValueError("Il backup deve contenere esattamente le 30 posizioni")
    by_slot = {item.get("slot"): item for item in raw_tools if isinstance(item, dict)}
    if set(by_slot) != set(range(1, 31)):
        raise ValueError("Le posizioni del backup devono essere uniche e comprese tra 1 e 30")

    normalized = []
    for slot in range(1, 31):
        raw = by_slot[slot]
        cuts_raw = raw.get("cutting_parameters", [])
        history_raw = raw.get("history", [])
        if not isinstance(cuts_raw, list) or not isinstance(history_raw, list):
            raise ValueError(f"Materiali o storico non validi nella posizione {slot}")
        cuts = [_clean_cutting_import(item, f"posizione {slot}") for item in cuts_raw]
        if len({item["material"].casefold() for item in cuts}) != len(cuts):
            raise ValueError(f"Materiali duplicati nella posizione {slot}")
        history = []
        for index, item in enumerate(history_raw, 1):
            tool = _clean_tool_import({**item, "slot": slot} if isinstance(item, dict) else item, slot)
            archived_cuts_raw = item.get("cutting_parameters", []) if isinstance(item, dict) else []
            if not isinstance(archived_cuts_raw, list):
                raise ValueError(f"Materiali storici non validi nella posizione {slot}")
            archived_cuts = [
                _clean_cutting_import(cut, f"storico {index}, posizione {slot}") for cut in archived_cuts_raw
            ]
            archived_at = item.get("archived_at") or utc_now()
            history.append({
                "tool": tool,
                "tool_uid": item.get("tool_uid") or uuid.uuid4().hex,
                "cuts": archived_cuts,
                "archived_at": str(archived_at),
            })
        normalized.append({
            "slot": slot,
            "tool": _clean_tool_import(raw, slot),
            "tool_uid": raw.get("tool_uid") or (uuid.uuid4().hex if _tool_is_occupied(raw) else None),
            "cuts": cuts,
            "history": history,
        })
    return normalized


def restore_export(payload: dict) -> dict:
    normalized = _validate_import(payload)
    normalized_inventory = []
    raw_inventory = payload.get("inventory", [])
    if not isinstance(raw_inventory, list):
        raise ValueError("Magazzino Officina non valido")
    for index, raw in enumerate(raw_inventory, 1):
        if not isinstance(raw, dict):
            raise ValueError("Utensile Officina non valido")
        tool = _clean_tool_import({**raw, "slot": 1}, 1)
        cuts_raw = raw.get("cutting_parameters", [])
        if not isinstance(cuts_raw, list):
            raise ValueError("Materiali Officina non validi")
        normalized_inventory.append({
            "tool_uid": raw.get("tool_uid") or uuid.uuid4().hex,
            "tool": tool,
            "cuts": [_clean_cutting_import(cut, f"Officina {index}") for cut in cuts_raw],
        })
    raw_templates = payload.get("material_templates", [])
    raw_events = payload.get("events", [])
    raw_colors = payload.get("tool_type_colors", {})
    if not isinstance(raw_templates, list) or not isinstance(raw_events, list):
        raise ValueError("Libreria materiali o registro movimenti non validi")
    if not isinstance(raw_colors, dict):
        raise ValueError("Colori tipi utensile non validi")
    normalized_colors = _validate_tool_type_colors(raw_colors)
    normalized_templates = []
    for raw in raw_templates:
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ValueError("Libreria materiali non valida")
        normalized_templates.append({
            "name": clean_value("material", raw.get("name")),
            "vc_m_min": clean_value("vc_m_min", raw.get("vc_m_min")),
            "fz_mm_tooth": clean_value("fz_mm_tooth", raw.get("fz_mm_tooth")),
            "ap_mm": clean_value("ap_mm", raw.get("ap_mm")),
            "ae_mm": clean_value("ae_mm", raw.get("ae_mm")),
            "coolant": clean_value("coolant", raw.get("coolant")),
            "notes": clean_value("notes", raw.get("notes")),
        })
    backup_dir = data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_dir / f"cnc-tool-magazine-before-import-{stamp}.json"
    backup_path.write_text(json.dumps(export_data(), ensure_ascii=False, indent=2), encoding="utf-8")

    with connect() as db:
        db.execute("DELETE FROM cutting_parameters")
        db.execute("DELETE FROM tool_history")
        db.execute("DELETE FROM inventory_tools")
        db.execute("DELETE FROM tool_events")
        for item in normalized:
            slot = item["slot"]
            values = {
                **item["tool"],
                "tool_uid": item["tool_uid"],
                "timer_started_at": None,
                "updated_at": utc_now(),
            }
            assignments = ", ".join(f"{field} = ?" for field in values)
            db.execute(f"UPDATE tools SET {assignments} WHERE slot = ?", [*values.values(), slot])
            for cutting in item["cuts"]:
                cut_values = {**cutting, "updated_at": utc_now()}
                columns = ["slot", *cut_values.keys()]
                db.execute(
                    f"INSERT INTO cutting_parameters ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                    [slot, *cut_values.values()],
                )
            for archived in reversed(item["history"]):
                db.execute(
                    "INSERT INTO tool_history(slot, tool_json, cutting_json, archived_at) VALUES (?, ?, ?, ?)",
                    (
                        slot,
                        json.dumps({**archived["tool"], "tool_uid": archived["tool_uid"]}, ensure_ascii=False),
                        json.dumps(archived["cuts"], ensure_ascii=False),
                        archived["archived_at"],
                    ),
                )
        for item in normalized_inventory:
            _store_inventory(db, {**item["tool"], "tool_uid": item["tool_uid"]}, item["cuts"])
        if normalized_templates:
            db.execute("DELETE FROM material_templates")
            for item in normalized_templates:
                columns = [*item.keys(), "updated_at"]
                db.execute(
                    f"INSERT INTO material_templates ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                    [*item.values(), utc_now()],
                )
        for raw in raw_events:
            if not isinstance(raw, dict) or not raw.get("tool_uid") or not raw.get("event_type"):
                continue
            db.execute(
                "INSERT INTO tool_events(tool_uid, event_type, from_slot, to_slot, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(raw["tool_uid"]), str(raw["event_type"]), raw.get("from_slot"), raw.get("to_slot"),
                    str(raw.get("description", "")), str(raw.get("created_at") or utc_now()),
                ),
            )
        for icon, color in normalized_colors.items():
            db.execute(
                """INSERT INTO tool_type_colors(icon, color, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(icon) DO UPDATE SET color = excluded.color, updated_at = excluded.updated_at""",
                (icon, color, utc_now()),
            )

    return {
        "ok": True,
        "backup": backup_path.name,
        "tools": sum(_has_tool_data(item["tool"]) or bool(item["cuts"]) for item in normalized),
        "materials": sum(len(item["cuts"]) for item in normalized),
        "history": sum(len(item["history"]) for item in normalized),
        "inventory": len(normalized_inventory),
    }


def duplicate_tool(source_slot: int, target_slot: int) -> dict:
    if source_slot == target_slot:
        raise ValueError("Scegli una posizione di destinazione diversa")
    with connect() as db:
        _settle_timer(db, source_slot)
        _settle_timer(db, target_slot)
        source_tool, source_cuts = _active_snapshot(db, source_slot)
        if not (_has_tool_data(source_tool) or source_cuts):
            raise ValueError("La posizione di origine non contiene un utensile")
        target_tool, target_cuts = _active_snapshot(db, target_slot)
        archived_target = False
        if _has_tool_data(target_tool) or target_cuts:
            _store_history(db, target_slot, target_tool, target_cuts)
            if target_tool.get("tool_uid"):
                _record_event(
                    db, target_tool["tool_uid"], "archived", f"Utensile sostituito e archiviato nella posizione {target_slot}", from_slot=target_slot
                )
            archived_target = True
        _reset_tool(db, target_slot)
        values = {field: source_tool.get(field) for field in TOOL_FIELDS}
        values.update({
            "tool_uid": uuid.uuid4().hex,
            "t_number": target_slot,
            "d_offset": target_slot,
            "h_offset": target_slot,
            "updated_at": utc_now(),
        })
        assignments = ", ".join(f"{field} = ?" for field in values)
        db.execute(f"UPDATE tools SET {assignments} WHERE slot = ?", [*values.values(), target_slot])
        for cutting in source_cuts:
            cut_values = {field: cutting.get(field) for field in CUTTING_FIELDS}
            cut_values["updated_at"] = utc_now()
            columns = ["slot", *cut_values.keys()]
            db.execute(
                f"INSERT INTO cutting_parameters ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                [target_slot, *cut_values.values()],
            )
        _record_event(db, values["tool_uid"], "created", f"Utensile duplicato nella posizione {target_slot}", to_slot=target_slot)
    return {"ok": True, "target_slot": target_slot, "materials": len(source_cuts), "archived_target": archived_target}


def copy_cutting_parameters(source_slot: int, target_slot: int) -> dict:
    if source_slot == target_slot:
        raise ValueError("Scegli una posizione di origine diversa")
    with connect() as db:
        if not db.execute("SELECT 1 FROM tools WHERE slot = ?", (target_slot,)).fetchone():
            raise LookupError("Posizione di destinazione non trovata")
        rows = db.execute("SELECT * FROM cutting_parameters WHERE slot = ? ORDER BY material", (source_slot,)).fetchall()
        if not rows:
            raise ValueError("La posizione di origine non contiene materiali")
        for row in rows:
            values = {field: row[field] for field in CUTTING_FIELDS}
            values["updated_at"] = utc_now()
            columns = ["slot", *values.keys()]
            updates = ", ".join(f"{field} = excluded.{field}" for field in values if field != "material")
            db.execute(
                f"INSERT INTO cutting_parameters ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)}) "
                f"ON CONFLICT(slot, material) DO UPDATE SET {updates}",
                [target_slot, *values.values()],
            )
    return {"ok": True, "copied": len(rows)}


def _store_inventory(db: sqlite3.Connection, tool: dict, cuts: list[dict]) -> int:
    tool_uid = tool.get("tool_uid") or uuid.uuid4().hex
    tool_data = {field: tool.get(field) for field in TOOL_FIELDS}
    now = utc_now()
    cursor = db.execute(
        "INSERT INTO inventory_tools(tool_uid, tool_json, cutting_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (tool_uid, json.dumps(tool_data, ensure_ascii=False), json.dumps(cuts, ensure_ascii=False), now, now),
    )
    return int(cursor.lastrowid)


def create_inventory_tool(payload: dict) -> dict:
    values = {field: clean_value(field, payload.get(field)) for field in TOOL_FIELDS}
    values["status"] = values["status"] or "new"
    values["usage_hours"] = values["usage_hours"] or 0
    if values["icon"] not in TOOL_ICONS or values["status"] not in TOOL_STATUSES:
        raise ValueError("Icona o stato utensile non valido")
    if (values["thread_pitch_mm"] or 0) < 0:
        raise ValueError("Il passo della filettatura non può essere negativo")
    if values["icon"] in {"tap", "roll_tap", "thread_comb"} and not (values["thread_pitch_mm"] or 0) > 0:
        raise ValueError("Inserisci il passo della filettatura")
    if not (values["description"] or values["tool_type"]):
        raise ValueError("Inserisci almeno una descrizione o il tipo utensile")
    tool_uid = uuid.uuid4().hex
    values["t_number"] = values["t_number"] or None
    values["d_offset"] = values["d_offset"] or None
    values["h_offset"] = values["h_offset"] or None
    with connect() as db:
        inventory_id = _store_inventory(db, {**values, "tool_uid": tool_uid}, [])
        _record_event(db, tool_uid, "created_inventory", "Utensile aggiunto al magazzino Officina")
    return {"ok": True, "inventory_id": inventory_id}


def active_to_inventory(slot: int) -> dict:
    with connect() as db:
        _settle_timer(db, slot)
        tool, cuts = _active_snapshot(db, slot)
        if not (_has_tool_data(tool) or cuts):
            raise ValueError("La posizione non contiene un utensile")
        if not tool.get("tool_uid"):
            tool["tool_uid"] = uuid.uuid4().hex
        inventory_id = _store_inventory(db, tool, cuts)
        _record_event(
            db, tool["tool_uid"], "unmounted", f"Utensile smontato dalla posizione {slot} e spostato in Officina", from_slot=slot
        )
        _reset_tool(db, slot)
    return {"ok": True, "inventory_id": inventory_id}


def empty_position(slot: int) -> dict:
    """Empty a physical slot without deleting its mounted tool."""
    return active_to_inventory(slot)


def mount_inventory_tool(inventory_id: int, target_slot: int) -> dict:
    with connect() as db:
        row = db.execute("SELECT * FROM inventory_tools WHERE id = ?", (inventory_id,)).fetchone()
        if not row:
            raise LookupError("Utensile in Officina non trovato")
        _settle_timer(db, target_slot)
        target_tool, target_cuts = _active_snapshot(db, target_slot)
        displaced = False
        if _has_tool_data(target_tool) or target_cuts:
            _store_inventory(db, target_tool, target_cuts)
            if target_tool.get("tool_uid"):
                _record_event(
                    db,
                    target_tool["tool_uid"],
                    "unmounted",
                    f"Utensile sostituito nella posizione {target_slot} e spostato in Officina",
                    from_slot=target_slot,
                )
            displaced = True
        tool = json.loads(row["tool_json"])
        cuts = json.loads(row["cutting_json"])
        _reset_tool(db, target_slot)
        values = {field: tool.get(field) for field in TOOL_FIELDS}
        values.update({
            "tool_uid": row["tool_uid"],
            "t_number": target_slot,
            "status": "in_use",
            "updated_at": utc_now(),
        })
        assignments = ", ".join(f"{field} = ?" for field in values)
        db.execute(f"UPDATE tools SET {assignments} WHERE slot = ?", [*values.values(), target_slot])
        for cutting in cuts:
            cut_values = {field: cutting.get(field) for field in CUTTING_FIELDS}
            cut_values["updated_at"] = utc_now()
            columns = ["slot", *cut_values.keys()]
            db.execute(
                f"INSERT INTO cutting_parameters ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                [target_slot, *cut_values.values()],
            )
        db.execute("DELETE FROM inventory_tools WHERE id = ?", (inventory_id,))
        _record_event(db, row["tool_uid"], "mounted", f"Utensile montato nella posizione {target_slot}", to_slot=target_slot)
    return {"ok": True, "target_slot": target_slot, "displaced_to_inventory": displaced}


def move_active_tool(source_slot: int, target_slot: int) -> dict:
    if source_slot == target_slot:
        raise ValueError("Scegli una posizione diversa")
    with connect() as db:
        _settle_timer(db, source_slot)
        _settle_timer(db, target_slot)
        source_tool, cuts = _active_snapshot(db, source_slot)
        target_tool, target_cuts = _active_snapshot(db, target_slot)
        if not (_has_tool_data(source_tool) or cuts):
            raise ValueError("La posizione di origine non contiene un utensile")
        if _has_tool_data(target_tool) or target_cuts:
            raise ValueError("La posizione di destinazione deve essere libera")
        tool_uid = source_tool.get("tool_uid") or uuid.uuid4().hex
        _reset_tool(db, target_slot)
        values = {field: source_tool.get(field) for field in TOOL_FIELDS}
        values.update({"tool_uid": tool_uid, "t_number": target_slot, "updated_at": utc_now()})
        assignments = ", ".join(f"{field} = ?" for field in values)
        db.execute(f"UPDATE tools SET {assignments} WHERE slot = ?", [*values.values(), target_slot])
        for cutting in cuts:
            cut_values = {field: cutting.get(field) for field in CUTTING_FIELDS}
            cut_values["updated_at"] = utc_now()
            columns = ["slot", *cut_values.keys()]
            db.execute(
                f"INSERT INTO cutting_parameters ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                [target_slot, *cut_values.values()],
            )
        _reset_tool(db, source_slot)
        _record_event(
            db, tool_uid, "moved", f"Utensile spostato dalla posizione {source_slot} alla posizione {target_slot}", source_slot, target_slot
        )
    return {"ok": True, "from_slot": source_slot, "to_slot": target_slot}


def delete_inventory_tool(inventory_id: int) -> None:
    with connect() as db:
        row = db.execute("SELECT tool_uid FROM inventory_tools WHERE id = ?", (inventory_id,)).fetchone()
        if not row:
            raise LookupError("Utensile in Officina non trovato")
        stored_files = [item["stored_name"] for item in db.execute(
            "SELECT stored_name FROM attachments WHERE tool_uid = ?", (row["tool_uid"],)
        )]
        db.execute("DELETE FROM attachments WHERE tool_uid = ?", (row["tool_uid"],))
        db.execute("DELETE FROM inventory_tools WHERE id = ?", (inventory_id,))
        _record_event(db, row["tool_uid"], "removed", "Utensile rimosso dal magazzino Officina")
    for stored_name in stored_files:
        (attachments_dir() / stored_name).unlink(missing_ok=True)


def list_material_templates() -> list[dict]:
    with connect() as db:
        return [row_to_dict(row) for row in db.execute("SELECT * FROM material_templates ORDER BY name COLLATE NOCASE")]


def save_material_template(payload: dict, template_id: int | None = None) -> dict:
    fields = ("name", "vc_m_min", "fz_mm_tooth", "ap_mm", "ae_mm", "coolant", "notes")
    values = {field: clean_value("material" if field == "name" else field, payload.get(field)) for field in fields}
    if not values["name"]:
        raise ValueError("Il nome del materiale è obbligatorio")
    values["updated_at"] = utc_now()
    with connect() as db:
        if template_id is None:
            columns = list(values)
            cursor = db.execute(
                f"INSERT INTO material_templates ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                list(values.values()),
            )
            template_id = int(cursor.lastrowid)
        else:
            assignments = ", ".join(f"{field} = ?" for field in values)
            result = db.execute(
                f"UPDATE material_templates SET {assignments} WHERE id = ?", [*values.values(), template_id]
            )
            if result.rowcount != 1:
                raise LookupError("Modello materiale non trovato")
        row = db.execute("SELECT * FROM material_templates WHERE id = ?", (template_id,)).fetchone()
    return row_to_dict(row)


def delete_material_template(template_id: int) -> None:
    with connect() as db:
        result = db.execute("DELETE FROM material_templates WHERE id = ?", (template_id,))
        if result.rowcount != 1:
            raise LookupError("Modello materiale non trovato")


def get_visel_settings() -> dict:
    with connect() as db:
        row = db.execute("SELECT * FROM visel_settings WHERE id = 1").fetchone()
    settings = row_to_dict(row) if row else {
        "id": 1, "controller_model": "PentaMac", "software_version": "", "host": "",
        "connection_type": "not_configured", "notes": "", "updated_at": utc_now(),
    }
    settings.update({
        "connected": False,
        "safe_mode": True,
        "state": "waiting_protocol" if settings["connection_type"] == "not_configured" else "configuration_saved",
        "message": "Configurazione preparatoria: nessun comando viene inviato alla macchina.",
    })
    return settings


def save_visel_settings(payload: dict) -> dict:
    allowed_types = {"not_configured", "file_export", "network_unknown"}
    connection_type = str(payload.get("connection_type") or "not_configured").strip()
    if connection_type not in allowed_types:
        raise ValueError("Tipo di collegamento Visel non valido")
    values = {
        "controller_model": str(payload.get("controller_model") or "PentaMac").strip()[:120],
        "software_version": str(payload.get("software_version") or "").strip()[:120],
        "host": str(payload.get("host") or "").strip()[:255],
        "connection_type": connection_type,
        "notes": str(payload.get("notes") or "").strip()[:2000],
        "updated_at": utc_now(),
    }
    with connect() as db:
        db.execute(
            """UPDATE visel_settings SET controller_model = ?, software_version = ?, host = ?,
               connection_type = ?, notes = ?, updated_at = ? WHERE id = 1""",
            tuple(values.values()),
        )
    return get_visel_settings()


def list_tool_type_colors() -> dict[str, str]:
    result = dict(DEFAULT_TOOL_TYPE_COLORS)
    with connect() as db:
        for row in db.execute("SELECT icon, color FROM tool_type_colors"):
            if row["icon"] in DEFAULT_TOOL_TYPE_COLORS and re.fullmatch(r"#[0-9A-Fa-f]{6}", row["color"]):
                result[row["icon"]] = row["color"].upper()
    return result


def _validate_tool_type_colors(payload: dict) -> dict[str, str]:
    result = {}
    for icon, color in payload.items():
        if icon not in DEFAULT_TOOL_TYPE_COLORS:
            raise ValueError("Tipo utensile non valido nei colori")
        normalized = str(color or "").strip().upper()
        if not re.fullmatch(r"#[0-9A-F]{6}", normalized):
            raise ValueError(f"Colore non valido per {icon}")
        result[icon] = normalized
    return result


def save_tool_type_colors(payload: dict) -> dict[str, str]:
    supplied = payload.get("colors")
    if not isinstance(supplied, dict):
        raise ValueError("È richiesto l'elenco dei colori")
    values = _validate_tool_type_colors(supplied)
    with connect() as db:
        for icon, color in values.items():
            db.execute(
                """INSERT INTO tool_type_colors(icon, color, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(icon) DO UPDATE SET color = excluded.color, updated_at = excluded.updated_at""",
                (icon, color, utc_now()),
            )
    return list_tool_type_colors()


def attachments_dir() -> Path:
    target = data_dir() / "attachments"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _safe_attachment_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(name).name).strip(" .")[:120]
    if not cleaned:
        raise ValueError("Nome del file non valido")
    return cleaned


def save_attachment(tool_uid: str, name: str, mime_type: str, content: bytes) -> dict:
    safe_name = _safe_attachment_name(name)
    if mime_type in {"", "application/octet-stream"}:
        mime_type = mimetypes.guess_type(safe_name)[0] or mime_type
    allowed_mimes = {
        "application/pdf", "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "text/plain"
    }
    if mime_type not in allowed_mimes:
        raise ValueError("Sono consentiti PDF, JPG, PNG, WEBP, HEIC e file di testo")
    if not content or len(content) > 10_000_000:
        raise ValueError("Il file deve avere una dimensione compresa tra 1 byte e 10 MB")
    stored_name = f"{tool_uid}-{uuid.uuid4().hex}-{safe_name}"
    path = attachments_dir() / stored_name
    path.write_bytes(content)
    try:
        with connect() as db:
            cursor = db.execute(
                "INSERT INTO attachments(tool_uid, original_name, stored_name, mime_type, size, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (tool_uid, safe_name, stored_name, mime_type, len(content), utc_now()),
            )
            attachment_id = int(cursor.lastrowid)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"id": attachment_id, "original_name": safe_name, "mime_type": mime_type, "size": len(content)}


def tool_uid_for_slot(slot: int) -> str:
    with connect() as db:
        row = db.execute("SELECT tool_uid FROM tools WHERE slot = ?", (slot,)).fetchone()
    if not row:
        raise LookupError("Posizione non trovata")
    if not row["tool_uid"]:
        raise ValueError("Inserisci prima un utensile nella posizione")
    return row["tool_uid"]


def tool_uid_for_inventory(inventory_id: int) -> str:
    with connect() as db:
        row = db.execute("SELECT tool_uid FROM inventory_tools WHERE id = ?", (inventory_id,)).fetchone()
    if not row:
        raise LookupError("Utensile in Officina non trovato")
    return row["tool_uid"]


def tool_uid_for_history(slot: int, history_id: int) -> str:
    with connect() as db:
        row = db.execute("SELECT tool_json FROM tool_history WHERE id = ? AND slot = ?", (history_id, slot)).fetchone()
        if not row:
            raise LookupError("Utensile storico non trovato")
        tool = json.loads(row["tool_json"])
        tool_uid = tool.get("tool_uid") or uuid.uuid4().hex
        if not tool.get("tool_uid"):
            tool["tool_uid"] = tool_uid
            db.execute(
                "UPDATE tool_history SET tool_json = ? WHERE id = ? AND slot = ?",
                (json.dumps(tool, ensure_ascii=False), history_id, slot),
            )
    return tool_uid


def attachment_file(attachment_id: int) -> tuple[dict, Path]:
    with connect() as db:
        row = db.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
    if not row:
        raise LookupError("Allegato non trovato")
    item = row_to_dict(row)
    path = attachments_dir() / item["stored_name"]
    if not path.is_file():
        raise LookupError("File allegato non trovato")
    return item, path


def delete_attachment(attachment_id: int) -> None:
    item, path = attachment_file(attachment_id)
    with connect() as db:
        db.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
    path.unlink(missing_ok=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "CNCToolMagazine/0.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def send_json(self, data, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 5_000_000:
            raise ValueError("Corpo richiesta non valido")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("È richiesto un oggetto JSON")
        return value

    def read_binary(self, limit: int = 10_000_000) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > limit:
            raise ValueError("Dimensione del file non valida")
        return self.rfile.read(length)

    def path_only(self) -> str:
        path = unquote(urlparse(self.path).path)
        return path.rstrip("/") or "/"

    def do_GET(self) -> None:
        path = self.path_only()
        if path == "/health":
            self.send_json({"status": "ok"})
            return
        if path == "/api/tools":
            self.send_json({"machine": machine_options(), "tools": list_tools()})
            return
        if path == "/api/inventory":
            self.send_json({"inventory": list_inventory()})
            return
        if path == "/api/events":
            self.send_json({"events": list_events()})
            return
        if path == "/api/material-templates":
            self.send_json({"templates": list_material_templates()})
            return
        if path == "/api/validation":
            self.send_json(validation_report())
            return
        if path == "/api/visel":
            self.send_json(get_visel_settings())
            return
        if path == "/api/tool-type-colors":
            self.send_json({"colors": list_tool_type_colors()})
            return
        if path == "/api/search":
            query = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            try:
                self.send_json({"query": query, "results": global_search(query)})
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/export":
            self.send_json(export_data())
            return
        if path == "/api/export/pdf":
            exported_at = utc_now()
            content = build_pdf_report(
                list_tools(), machine_options(), exported_at, list_inventory(), list_material_templates(), list_events(100)
            )
            filename = f"cnc-tool-magazine-{exported_at[:10]}.pdf"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return
        if path == "/api/export/machine-table.pdf":
            exported_at = utc_now()
            content = build_machine_table_pdf(
                list_tools(), machine_options(), list_tool_type_colors(), exported_at
            )
            filename = f"tabella-utensili-macchina-{exported_at[:10]}.pdf"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return
        qr_match = path == "/api/qr.svg" or re.fullmatch(r"/api/tools/(\d+)/qr\.svg", path)
        if qr_match:
            if qr_match is not True:
                self.valid_slot(qr_match.group(1))
            target = parse_qs(urlparse(self.path).query).get("target", [""])[0]
            try:
                content = qr_svg(target)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "private, max-age=300")
            self.end_headers()
            self.wfile.write(content)
            return
        attachment_match = re.fullmatch(r"/api/attachments/(\d+)", path)
        if attachment_match:
            try:
                item, target = attachment_file(int(attachment_match.group(1)))
            except LookupError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content = target.read_bytes()
            filename = item["original_name"].replace('"', "")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", item["mime_type"])
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "private, max-age=300")
            self.end_headers()
            self.wfile.write(content)
            return
        if path in {"/", "/index.html"}:
            self.send_static("index.html")
            return
        if path.startswith("/static/"):
            self.send_static(path.removeprefix("/static/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        path = self.path_only()
        try:
            payload = self.read_json()
            tool_match = re.fullmatch(r"/api/tools/(\d+)", path)
            cutting_match = re.fullmatch(r"/api/tools/(\d+)/cutting", path)
            history_icon_match = re.fullmatch(r"/api/tools/(\d+)/history/(\d+)/icon", path)
            template_match = re.fullmatch(r"/api/material-templates/(\d+)", path)
            if path == "/api/visel":
                self.send_json(save_visel_settings(payload))
                return
            if path == "/api/tool-type-colors":
                self.send_json({"colors": save_tool_type_colors(payload)})
                return
            if tool_match:
                slot = self.valid_slot(tool_match.group(1))
                self.send_json(update_tool(slot, payload))
                return
            if cutting_match:
                slot = self.valid_slot(cutting_match.group(1))
                self.send_json(upsert_cutting(slot, payload))
                return
            if history_icon_match:
                slot = self.valid_slot(history_icon_match.group(1))
                update_history_icon(slot, int(history_icon_match.group(2)), payload.get("icon", ""))
                self.send_json({"ok": True})
                return
            if template_match:
                self.send_json(save_material_template(payload, int(template_match.group(1))))
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError, sqlite3.IntegrityError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except LookupError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = self.path_only()
        try:
            tool_attachment_match = re.fullmatch(r"/api/tools/(\d+)/attachments", path)
            inventory_attachment_match = re.fullmatch(r"/api/inventory/(\d+)/attachments", path)
            history_attachment_match = re.fullmatch(r"/api/tools/(\d+)/history/(\d+)/attachments", path)
            if tool_attachment_match or inventory_attachment_match or history_attachment_match:
                name = unquote(self.headers.get("X-File-Name", ""))
                mime_type = self.headers.get("X-File-Type", "application/octet-stream").split(";", 1)[0]
                if tool_attachment_match:
                    tool_uid = tool_uid_for_slot(self.valid_slot(tool_attachment_match.group(1)))
                elif inventory_attachment_match:
                    tool_uid = tool_uid_for_inventory(int(inventory_attachment_match.group(1)))
                else:
                    tool_uid = tool_uid_for_history(
                        self.valid_slot(history_attachment_match.group(1)), int(history_attachment_match.group(2))
                    )
                self.send_json(save_attachment(tool_uid, name, mime_type, self.read_binary()), HTTPStatus.CREATED)
                return
            if path == "/api/import":
                self.send_json(restore_export(self.read_json()))
                return
            archive_match = re.fullmatch(r"/api/tools/(\d+)/archive", path)
            activate_match = re.fullmatch(r"/api/tools/(\d+)/history/(\d+)/activate", path)
            duplicate_match = re.fullmatch(r"/api/tools/(\d+)/duplicate", path)
            copy_cutting_match = re.fullmatch(r"/api/tools/(\d+)/cutting/copy", path)
            usage_start_match = re.fullmatch(r"/api/tools/(\d+)/usage/start", path)
            usage_stop_match = re.fullmatch(r"/api/tools/(\d+)/usage/stop", path)
            to_inventory_match = re.fullmatch(r"/api/tools/(\d+)/inventory", path)
            mount_inventory_match = re.fullmatch(r"/api/inventory/(\d+)/mount", path)
            move_match = re.fullmatch(r"/api/tools/(\d+)/move", path)
            if archive_match:
                history_id = archive_active_tool(self.valid_slot(archive_match.group(1)))
                self.send_json({"ok": True, "history_id": history_id})
                return
            if activate_match:
                activate_history_tool(self.valid_slot(activate_match.group(1)), int(activate_match.group(2)))
                self.send_json({"ok": True})
                return
            if duplicate_match:
                payload = self.read_json()
                self.send_json(
                    duplicate_tool(
                        self.valid_slot(duplicate_match.group(1)),
                        self.valid_slot(str(payload.get("target_slot", ""))),
                    )
                )
                return
            if copy_cutting_match:
                payload = self.read_json()
                self.send_json(
                    copy_cutting_parameters(
                        self.valid_slot(str(payload.get("source_slot", ""))),
                        self.valid_slot(copy_cutting_match.group(1)),
                    )
                )
                return
            if usage_start_match:
                start_usage(self.valid_slot(usage_start_match.group(1)))
                self.send_json({"ok": True})
                return
            if usage_stop_match:
                hours = stop_usage(self.valid_slot(usage_stop_match.group(1)))
                self.send_json({"ok": True, "usage_hours": round(hours, 3)})
                return
            if to_inventory_match:
                self.send_json(active_to_inventory(self.valid_slot(to_inventory_match.group(1))))
                return
            if mount_inventory_match:
                payload = self.read_json()
                self.send_json(mount_inventory_tool(
                    int(mount_inventory_match.group(1)), self.valid_slot(str(payload.get("target_slot", "")))
                ))
                return
            if move_match:
                payload = self.read_json()
                self.send_json(move_active_tool(
                    self.valid_slot(move_match.group(1)), self.valid_slot(str(payload.get("target_slot", "")))
                ))
                return
            if path == "/api/inventory":
                self.send_json(create_inventory_tool(self.read_json()), HTTPStatus.CREATED)
                return
            if path == "/api/material-templates":
                self.send_json(save_material_template(self.read_json()), HTTPStatus.CREATED)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError, sqlite3.IntegrityError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except LookupError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        path = self.path_only()
        try:
            tool_match = re.fullmatch(r"/api/tools/(\d+)", path)
            cutting_match = re.fullmatch(r"/api/tools/(\d+)/cutting/(\d+)", path)
            history_match = re.fullmatch(r"/api/tools/(\d+)/history/(\d+)", path)
            inventory_match = re.fullmatch(r"/api/inventory/(\d+)", path)
            template_match = re.fullmatch(r"/api/material-templates/(\d+)", path)
            attachment_match = re.fullmatch(r"/api/attachments/(\d+)", path)
            if tool_match:
                self.send_json(empty_position(self.valid_slot(tool_match.group(1))))
                return
            if cutting_match:
                delete_cutting(self.valid_slot(cutting_match.group(1)), int(cutting_match.group(2)))
                self.send_json({"ok": True})
                return
            if history_match:
                delete_history_tool(self.valid_slot(history_match.group(1)), int(history_match.group(2)))
                self.send_json({"ok": True})
                return
            if inventory_match:
                delete_inventory_tool(int(inventory_match.group(1)))
                self.send_json({"ok": True})
                return
            if template_match:
                delete_material_template(int(template_match.group(1)))
                self.send_json({"ok": True})
                return
            if attachment_match:
                delete_attachment(int(attachment_match.group(1)))
                self.send_json({"ok": True})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except LookupError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

    @staticmethod
    def valid_slot(raw: str) -> int:
        slot = int(raw)
        if not 1 <= slot <= 30:
            raise ValueError("La posizione deve essere compresa tra 1 e 30")
        return slot

    def send_static(self, relative: str) -> None:
        target = (WWW_DIR / relative).resolve()
        if WWW_DIR.resolve() not in target.parents or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", 8099), Handler)
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
    print("CNC Tool Magazine in ascolto sulla porta 8099", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
