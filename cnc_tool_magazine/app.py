#!/usr/bin/env python3
"""CNC Tool Magazine: dependency-free Home Assistant app backend."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import signal
import sqlite3
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

APP_DIR = Path(__file__).resolve().parent
WWW_DIR = APP_DIR / "www"
TOOL_FIELDS = {
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
            """
        )
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
    by_slot: dict[int, list[dict]] = {}
    for item in cuts:
        by_slot.setdefault(item["slot"], []).append(item)
    for tool in tools:
        tool["cutting_parameters"] = by_slot.get(tool["slot"], [])
    return tools


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
        return None if field not in {"description", "tool_type", "notes", "material", "coolant"} else ""
    if field in {"t_number", "d_offset", "h_offset", "flutes", "rpm"}:
        return int(value)
    if field in {"diameter_mm", "length_mm", "vc_m_min", "fz_mm_tooth", "feed_mm_min", "ap_mm", "ae_mm"}:
        return float(value)
    return str(value).strip()


def update_tool(slot: int, payload: dict) -> dict:
    values = {field: clean_value(field, payload[field]) for field in TOOL_FIELDS if field in payload}
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


def reset_tool(slot: int) -> None:
    with connect() as db:
        db.execute("DELETE FROM cutting_parameters WHERE slot = ?", (slot,))
        result = db.execute(
            """UPDATE tools SET t_number = ?, d_offset = ?, h_offset = ?,
               diameter_mm = NULL, length_mm = NULL, description = '', tool_type = '',
               flutes = NULL, notes = '', updated_at = ? WHERE slot = ?""",
            (slot, slot, slot, utc_now(), slot),
        )
        if result.rowcount != 1:
            raise LookupError("Posizione non trovata")


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
        if length <= 0 or length > 1_000_000:
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
            self.send_json(
                {"schema_version": 1, "exported_at": utc_now(), "machine": machine_options(), "tools": list_tools()}
            )
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
            if tool_match:
                slot = self.valid_slot(tool_match.group(1))
                self.send_json(update_tool(slot, payload))
                return
            if cutting_match:
                slot = self.valid_slot(cutting_match.group(1))
                self.send_json(upsert_cutting(slot, payload))
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
            if tool_match:
                reset_tool(self.valid_slot(tool_match.group(1)))
                self.send_json({"ok": True})
                return
            if cutting_match:
                delete_cutting(self.valid_slot(cutting_match.group(1)), int(cutting_match.group(2)))
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
