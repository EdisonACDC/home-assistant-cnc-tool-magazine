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
from io import BytesIO
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
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
    "flutes",
    "notes",
}
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
    "reamer",
    "boring_bar",
    "engraving",
    "probe",
    "custom",
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


def _pdf_text(value: object, suffix: str = "") -> str:
    if value is None or value == "":
        return "-"
    return f"{escape(str(value))}{suffix}"


def _tool_is_occupied(tool: dict) -> bool:
    fields = ("description", "tool_type", "icon", "diameter_mm", "length_mm", "flutes", "notes")
    return any(tool.get(field) not in (None, "") for field in fields) or bool(tool.get("cutting_parameters"))


def _tool_icon(icon_name: str) -> Image | str:
    path = WWW_DIR / "tool-icons" / f"{icon_name}.png"
    if icon_name and path.is_file():
        return Image(str(path), width=15 * mm, height=15 * mm, kind="proportional")
    return ""


def build_pdf_report(tools: list[dict], machine: dict, exported_at: str) -> bytes:
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
                 ("Pos.", "Stato", "T", "D", "H", "Descrizione", "Tipo", "Diametro", "Lunghezza", "Archivio")]]
    for tool in tools:
        occupied = _tool_is_occupied(tool)
        overview.append([
            Paragraph(str(tool["slot"]), centered), Paragraph("Montato" if occupied else "Libera", centered),
            Paragraph(_pdf_text(tool.get("t_number")), centered), Paragraph(_pdf_text(tool.get("d_offset")), centered),
            Paragraph(_pdf_text(tool.get("h_offset")), centered), Paragraph(_pdf_text(tool.get("description")), small),
            Paragraph(_pdf_text(tool.get("tool_type")), small), Paragraph(_pdf_text(tool.get("diameter_mm"), " mm"), centered),
            Paragraph(_pdf_text(tool.get("length_mm"), " mm"), centered), Paragraph(str(len(tool.get("history", []))), centered),
        ])
    overview_table = LongTable(
        overview, repeatRows=1,
        colWidths=[10 * mm, 18 * mm, 10 * mm, 10 * mm, 10 * mm, 53 * mm, 35 * mm, 24 * mm, 24 * mm, 17 * mm],
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
            Paragraph(f"<b>Diametro:</b> {_pdf_text(tool.get('diameter_mm'), ' mm')}<br/><b>Lunghezza:</b> {_pdf_text(tool.get('length_mm'), ' mm')}<br/><b>Taglienti:</b> {_pdf_text(tool.get('flutes'))}", body),
            Paragraph(f"<b>Tipo:</b> {_pdf_text(tool.get('tool_type'))}<br/><b>Note:</b> {_pdf_text(tool.get('notes'))}", body),
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
                flutes INTEGER,
                notes TEXT NOT NULL DEFAULT '',
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
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(tools)")}
        if "icon" not in columns:
            db.execute("ALTER TABLE tools ADD COLUMN icon TEXT NOT NULL DEFAULT ''")
        db.executemany(
            "INSERT OR IGNORE INTO tools(slot, t_number, d_offset, h_offset) VALUES (?, ?, ?, ?)",
            ((slot, slot, slot, slot) for slot in range(1, slot_count + 1)),
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
    by_slot: dict[int, list[dict]] = {}
    for item in cuts:
        by_slot.setdefault(item["slot"], []).append(item)
    for tool in tools:
        tool["cutting_parameters"] = by_slot.get(tool["slot"], [])
        tool["history"] = []
    by_tool_slot = {tool["slot"]: tool for tool in tools}
    for item in history_rows:
        try:
            archived_tool = json.loads(item["tool_json"])
            archived_cuts = json.loads(item["cutting_json"])
        except (TypeError, ValueError):
            continue
        archived_tool.update(
            {"history_id": item["id"], "archived_at": item["archived_at"], "cutting_parameters": archived_cuts}
        )
        by_tool_slot[item["slot"]]["history"].append(archived_tool)
    return tools


def export_data() -> dict:
    return {"schema_version": 1, "exported_at": utc_now(), "machine": machine_options(), "tools": list_tools()}


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
    if field in {"diameter_mm", "length_mm", "vc_m_min", "fz_mm_tooth", "feed_mm_min", "ap_mm", "ae_mm"}:
        return float(value)
    return str(value).strip()


def update_tool(slot: int, payload: dict) -> dict:
    values = {field: clean_value(field, payload[field]) for field in TOOL_FIELDS if field in payload}
    if "icon" in values and values["icon"] not in TOOL_ICONS:
        raise ValueError("Icona utensile non valida")
    if not values:
        raise ValueError("Nessun campo utensile valido")
    values["updated_at"] = utc_now()
    assignments = ", ".join(f"{field} = ?" for field in values)
    with connect() as db:
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
               flutes = NULL, notes = '', updated_at = ? WHERE slot = ?""",
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
    return any(tool.get(field) not in (None, "") for field in ("description", "tool_type", "diameter_mm", "length_mm", "flutes", "notes"))


def _store_history(db: sqlite3.Connection, slot: int, tool: dict, cuts: list[dict]) -> int:
    cursor = db.execute(
        "INSERT INTO tool_history(slot, tool_json, cutting_json, archived_at) VALUES (?, ?, ?, ?)",
        (slot, json.dumps(tool, ensure_ascii=False), json.dumps(cuts, ensure_ascii=False), utc_now()),
    )
    return int(cursor.lastrowid)


def archive_active_tool(slot: int) -> int:
    with connect() as db:
        tool, cuts = _active_snapshot(db, slot)
        if not _has_tool_data(tool):
            raise ValueError("Non c'è un utensile attivo da archiviare")
        history_id = _store_history(db, slot, tool, cuts)
        _reset_tool(db, slot)
    return history_id


def activate_history_tool(slot: int, history_id: int) -> None:
    with connect() as db:
        archived = db.execute(
            "SELECT * FROM tool_history WHERE id = ? AND slot = ?", (history_id, slot)
        ).fetchone()
        if not archived:
            raise LookupError("Utensile storico non trovato")
        active_tool, active_cuts = _active_snapshot(db, slot)
        if _has_tool_data(active_tool):
            _store_history(db, slot, active_tool, active_cuts)

        selected_tool = json.loads(archived["tool_json"])
        selected_cuts = json.loads(archived["cutting_json"])
        _reset_tool(db, slot)
        values = {field: selected_tool.get(field) for field in TOOL_FIELDS}
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


def delete_history_tool(slot: int, history_id: int) -> None:
    with connect() as db:
        result = db.execute("DELETE FROM tool_history WHERE id = ? AND slot = ?", (history_id, slot))
        if result.rowcount != 1:
            raise LookupError("Utensile storico non trovato")


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
        exists = db.execute("SELECT 1 FROM tools WHERE slot = ?", (slot,)).fetchone()
        if not exists:
            raise LookupError("Posizione non trovata")
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
    values = {field: clean_value(field, raw.get(field)) for field in TOOL_FIELDS}
    if values["icon"] not in TOOL_ICONS:
        raise ValueError(f"Icona non valida nella posizione {expected_slot}")
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
            history.append({"tool": tool, "cuts": archived_cuts, "archived_at": str(archived_at)})
        normalized.append({"slot": slot, "tool": _clean_tool_import(raw, slot), "cuts": cuts, "history": history})
    return normalized


def restore_export(payload: dict) -> dict:
    normalized = _validate_import(payload)
    backup_dir = data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_dir / f"cnc-tool-magazine-before-import-{stamp}.json"
    backup_path.write_text(json.dumps(export_data(), ensure_ascii=False, indent=2), encoding="utf-8")

    with connect() as db:
        db.execute("DELETE FROM cutting_parameters")
        db.execute("DELETE FROM tool_history")
        for item in normalized:
            slot = item["slot"]
            values = {**item["tool"], "updated_at": utc_now()}
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
                        json.dumps(archived["tool"], ensure_ascii=False),
                        json.dumps(archived["cuts"], ensure_ascii=False),
                        archived["archived_at"],
                    ),
                )

    return {
        "ok": True,
        "backup": backup_path.name,
        "tools": sum(_has_tool_data(item["tool"]) or bool(item["cuts"]) for item in normalized),
        "materials": sum(len(item["cuts"]) for item in normalized),
        "history": sum(len(item["history"]) for item in normalized),
    }


def duplicate_tool(source_slot: int, target_slot: int) -> dict:
    if source_slot == target_slot:
        raise ValueError("Scegli una posizione di destinazione diversa")
    with connect() as db:
        source_tool, source_cuts = _active_snapshot(db, source_slot)
        if not (_has_tool_data(source_tool) or source_cuts):
            raise ValueError("La posizione di origine non contiene un utensile")
        target_tool, target_cuts = _active_snapshot(db, target_slot)
        archived_target = False
        if _has_tool_data(target_tool) or target_cuts:
            _store_history(db, target_slot, target_tool, target_cuts)
            archived_target = True
        _reset_tool(db, target_slot)
        values = {field: source_tool.get(field) for field in TOOL_FIELDS}
        values.update({"t_number": target_slot, "d_offset": target_slot, "h_offset": target_slot, "updated_at": utc_now()})
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
        if path == "/api/export":
            self.send_json(export_data())
            return
        if path == "/api/export/pdf":
            exported_at = utc_now()
            content = build_pdf_report(list_tools(), machine_options(), exported_at)
            filename = f"cnc-tool-magazine-{exported_at[:10]}.pdf"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
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
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except LookupError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = self.path_only()
        try:
            if path == "/api/import":
                self.send_json(restore_export(self.read_json()))
                return
            archive_match = re.fullmatch(r"/api/tools/(\d+)/archive", path)
            activate_match = re.fullmatch(r"/api/tools/(\d+)/history/(\d+)/activate", path)
            duplicate_match = re.fullmatch(r"/api/tools/(\d+)/duplicate", path)
            copy_cutting_match = re.fullmatch(r"/api/tools/(\d+)/cutting/copy", path)
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
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except LookupError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        path = self.path_only()
        try:
            tool_match = re.fullmatch(r"/api/tools/(\d+)", path)
            cutting_match = re.fullmatch(r"/api/tools/(\d+)/cutting/(\d+)", path)
            history_match = re.fullmatch(r"/api/tools/(\d+)/history/(\d+)", path)
            if tool_match:
                reset_tool(self.valid_slot(tool_match.group(1)))
                self.send_json({"ok": True})
                return
            if cutting_match:
                delete_cutting(self.valid_slot(cutting_match.group(1)), int(cutting_match.group(2)))
                self.send_json({"ok": True})
                return
            if history_match:
                delete_history_tool(self.valid_slot(history_match.group(1)), int(history_match.group(2)))
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
