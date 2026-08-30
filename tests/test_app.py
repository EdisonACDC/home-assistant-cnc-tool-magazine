import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cnc_tool_magazine"))

import app


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["CNC_DATA_DIR"] = self.temp.name
        app.init_db()

    def tearDown(self):
        self.temp.cleanup()
        os.environ.pop("CNC_DATA_DIR", None)

    def test_creates_exactly_thirty_positions(self):
        tools = app.list_tools()
        self.assertEqual(30, len(tools))
        self.assertEqual(list(range(1, 31)), [tool["slot"] for tool in tools])

    def test_updates_tool_and_cutting_parameters(self):
        tool = app.update_tool(7, {"description": "Fresa MD Ø10", "diameter_mm": "10.0", "flutes": "4"})
        self.assertEqual("Fresa MD Ø10", tool["description"])
        self.assertEqual(10.0, tool["diameter_mm"])
        cutting = app.upsert_cutting(7, {"material": "Acciaio C45", "vc_m_min": "180", "rpm": "5730"})
        self.assertEqual("Acciaio C45", cutting["material"])
        self.assertEqual(5730, cutting["rpm"])
        self.assertEqual(1, len(app.list_tools()[6]["cutting_parameters"]))

    def test_upsert_keeps_one_row_per_material(self):
        app.upsert_cutting(2, {"material": "Alluminio", "vc_m_min": 300})
        app.upsert_cutting(2, {"material": "alluminio", "vc_m_min": 450})
        params = app.list_tools()[1]["cutting_parameters"]
        self.assertEqual(1, len(params))
        self.assertEqual(450.0, params[0]["vc_m_min"])

    def test_reset_restores_default_offsets(self):
        app.update_tool(12, {"t_number": 99, "description": "Punta"})
        app.upsert_cutting(12, {"material": "Inox"})
        app.reset_tool(12)
        tool = app.list_tools()[11]
        self.assertEqual(12, tool["t_number"])
        self.assertEqual("", tool["description"])
        self.assertEqual([], tool["cutting_parameters"])

    def test_rejects_missing_material(self):
        with self.assertRaises(ValueError):
            app.upsert_cutting(1, {"material": ""})

    def test_archives_active_tool_with_cutting_parameters(self):
        app.update_tool(5, {"description": "Fresa Ø8", "diameter_mm": 8})
        app.upsert_cutting(5, {"material": "C45", "rpm": 5000})
        history_id = app.archive_active_tool(5)
        tool = app.list_tools()[4]
        self.assertGreater(history_id, 0)
        self.assertEqual("", tool["description"])
        self.assertEqual(1, len(tool["history"]))
        self.assertEqual("Fresa Ø8", tool["history"][0]["description"])
        self.assertEqual("C45", tool["history"][0]["cutting_parameters"][0]["material"])

    def test_activating_history_swaps_current_tool(self):
        app.update_tool(9, {"description": "Utensile A", "icon": "ball_nose"})
        history_id = app.archive_active_tool(9)
        app.update_tool(9, {"description": "Utensile B"})
        app.activate_history_tool(9, history_id)
        tool = app.list_tools()[8]
        self.assertEqual("Utensile A", tool["description"])
        self.assertEqual("ball_nose", tool["icon"])
        self.assertEqual(1, len(tool["history"]))
        self.assertEqual("Utensile B", tool["history"][0]["description"])

    def test_history_icon_can_be_changed_without_activating_tool(self):
        app.update_tool(4, {"description": "Punta", "icon": "drill"})
        history_id = app.archive_active_tool(4)
        app.update_history_icon(4, history_id, "center_drill")
        tool = app.list_tools()[3]
        self.assertEqual("", tool["description"])
        self.assertEqual("center_drill", tool["history"][0]["icon"])

    def test_rejects_unknown_tool_icon(self):
        with self.assertRaises(ValueError):
            app.update_tool(1, {"icon": "not-an-icon"})

    def test_duplicate_tool_archives_target_and_copies_materials(self):
        app.update_tool(2, {"description": "Fresa sorgente", "diameter_mm": 12, "flutes": 4})
        app.upsert_cutting(2, {"material": "C45", "rpm": 4000})
        app.update_tool(8, {"description": "Utensile precedente"})
        result = app.duplicate_tool(2, 8)
        target = app.list_tools()[7]
        self.assertTrue(result["archived_target"])
        self.assertEqual("Fresa sorgente", target["description"])
        self.assertEqual((8, 8, 8), (target["t_number"], target["d_offset"], target["h_offset"]))
        self.assertEqual("C45", target["cutting_parameters"][0]["material"])
        self.assertEqual("Utensile precedente", target["history"][0]["description"])

    def test_copy_cutting_parameters_merges_and_updates_materials(self):
        app.upsert_cutting(3, {"material": "C45", "rpm": 5000})
        app.upsert_cutting(3, {"material": "Alluminio", "rpm": 9000})
        app.upsert_cutting(4, {"material": "c45", "rpm": 1000})
        result = app.copy_cutting_parameters(3, 4)
        materials = app.list_tools()[3]["cutting_parameters"]
        self.assertEqual(2, result["copied"])
        self.assertEqual(2, len(materials))
        self.assertEqual(5000, next(item for item in materials if item["material"].casefold() == "c45")["rpm"])

    def test_export_restore_round_trip_and_creates_backup(self):
        app.update_tool(6, {"description": "Fresa backup", "icon": "end_mill"})
        app.upsert_cutting(6, {"material": "Inox", "rpm": 3200})
        app.update_tool(11, {"description": "Punta storica"})
        app.archive_active_tool(11)
        exported = app.export_data()
        app.reset_tool(6)
        result = app.restore_export(exported)
        tools = app.list_tools()
        self.assertEqual("Fresa backup", tools[5]["description"])
        self.assertEqual("Inox", tools[5]["cutting_parameters"][0]["material"])
        self.assertEqual("Punta storica", tools[10]["history"][0]["description"])
        self.assertTrue((Path(self.temp.name) / "backups" / result["backup"]).is_file())

    def test_invalid_restore_does_not_change_database(self):
        app.update_tool(1, {"description": "Da conservare"})
        broken = app.export_data()
        broken["tools"] = broken["tools"][:-1]
        with self.assertRaises(ValueError):
            app.restore_export(broken)
        self.assertEqual("Da conservare", app.list_tools()[0]["description"])
        self.assertFalse((Path(self.temp.name) / "backups").exists())

    def test_old_backup_restores_with_new_life_defaults(self):
        exported = app.export_data()
        for tool in exported["tools"]:
            tool.pop("status", None)
            tool.pop("usage_hours", None)
            tool.pop("life_hours", None)
        app.restore_export(exported)
        tool = app.list_tools()[0]
        self.assertEqual("in_use", tool["status"])
        self.assertEqual(0, tool["usage_hours"])
        self.assertIsNone(tool["life_hours"])

    def test_usage_timer_accumulates_and_calculates_remaining_life(self):
        app.update_tool(10, {"description": "Fresa", "life_hours": 10, "usage_hours": 2})
        app.start_usage(10)
        started = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(timespec="seconds")
        with app.connect() as db:
            db.execute("UPDATE tools SET timer_started_at = ? WHERE slot = 10", (started,))
        hours = app.stop_usage(10)
        tool = app.list_tools()[9]
        self.assertAlmostEqual(5, hours, places=2)
        self.assertEqual(50, tool["remaining_percent"])
        self.assertIsNone(tool["timer_started_at"])

    def test_life_limit_sets_status_to_sharpen(self):
        app.update_tool(14, {"description": "Fresa", "life_hours": 1, "usage_hours": 1})
        with app.connect() as db:
            db.execute("UPDATE tools SET timer_started_at = ? WHERE slot = 14", (app.utc_now(),))
        app.stop_usage(14)
        self.assertEqual("to_sharpen", app.list_tools()[13]["status"])

    def test_qr_svg_contains_valid_svg(self):
        content = app.qr_svg("https://home.example/app?slot=7")
        self.assertIn(b"<svg", content)
        self.assertGreater(len(content), 1000)
        with self.assertRaises(ValueError):
            app.qr_svg("javascript:alert(1)")

    def test_pdf_export_contains_active_archived_and_all_positions(self):
        app.update_tool(3, {"description": "Fresa attiva", "icon": "end_mill", "diameter_mm": 10})
        app.upsert_cutting(3, {"material": "C45", "rpm": 4200, "feed_mm_min": 620})
        app.update_tool(7, {"description": "Punta archiviata", "icon": "drill"})
        app.archive_active_tool(7)
        tools = app.list_tools()
        pdf = app.build_pdf_report(tools, {"machine_name": "PentaMac / Visel"}, app.utc_now())
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 5000)
        self.assertEqual(30, len(tools))
        self.assertEqual(1, len(tools[6]["history"]))


if __name__ == "__main__":
    unittest.main()
