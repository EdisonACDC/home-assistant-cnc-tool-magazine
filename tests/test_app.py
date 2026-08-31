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

    def test_thread_pitch_is_required_and_follows_threading_tool(self):
        with self.assertRaises(ValueError):
            app.update_tool(4, {"description": "Maschio M10", "icon": "tap"})
        tool = app.update_tool(4, {
            "description": "Maschio M10", "icon": "tap", "thread_pitch_mm": "1.5", "diameter_mm": 10,
        })
        self.assertEqual(1.5, tool["thread_pitch_mm"])
        inventory_id = app.active_to_inventory(4)["inventory_id"]
        self.assertEqual(1.5, app.list_inventory()[0]["thread_pitch_mm"])
        app.mount_inventory_tool(inventory_id, 11)
        self.assertEqual(1.5, app.list_tools()[10]["thread_pitch_mm"])
        exported = app.export_data()
        app.restore_export(exported)
        self.assertEqual(1.5, app.list_tools()[10]["thread_pitch_mm"])

    def test_roll_tap_requires_pitch_and_keeps_its_icon(self):
        with self.assertRaises(ValueError):
            app.update_tool(5, {"description": "Maschio a rullare M8", "icon": "roll_tap"})
        tool = app.update_tool(5, {
            "description": "Maschio a rullare M8", "tool_type": "Maschio a rullare",
            "icon": "roll_tap", "thread_pitch_mm": "1.25", "diameter_mm": 8,
        })
        self.assertEqual("roll_tap", tool["icon"])
        self.assertEqual(1.25, tool["thread_pitch_mm"])
        inventory_id = app.active_to_inventory(5)["inventory_id"]
        app.mount_inventory_tool(inventory_id, 15)
        mounted = app.list_tools()[14]
        self.assertEqual("roll_tap", mounted["icon"])
        self.assertEqual(1.25, mounted["thread_pitch_mm"])

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

    def test_moves_tool_to_inventory_and_mounts_it_again(self):
        app.update_tool(5, {"description": "Fresa Officina", "diameter_mm": 10, "d_offset": 205, "h_offset": 305})
        app.upsert_cutting(5, {"material": "C45", "rpm": 5000})
        original_uid = app.list_tools()[4]["tool_uid"]
        result = app.active_to_inventory(5)
        self.assertEqual("", app.list_tools()[4]["description"])
        inventory = app.list_inventory()
        self.assertEqual(1, len(inventory))
        self.assertEqual(original_uid, inventory[0]["tool_uid"])
        app.mount_inventory_tool(result["inventory_id"], 12)
        mounted = app.list_tools()[11]
        self.assertEqual("Fresa Officina", mounted["description"])
        self.assertEqual(original_uid, mounted["tool_uid"])
        self.assertEqual(12, mounted["t_number"])
        self.assertEqual(205, mounted["d_offset"])
        self.assertEqual(305, mounted["h_offset"])
        self.assertEqual("C45", mounted["cutting_parameters"][0]["material"])
        self.assertEqual([], app.list_inventory())
        descriptions = [event["description"] for event in app.list_events()]
        self.assertTrue(any("montato nella posizione 12" in text for text in descriptions))

    def test_empty_position_moves_tool_to_inventory_without_deleting_it(self):
        app.update_tool(18, {"description": "Fresa da conservare", "diameter_mm": 16, "d_offset": 118, "h_offset": 218})
        app.upsert_cutting(18, {"material": "C45", "vc_m_min": 175})
        uid = app.list_tools()[17]["tool_uid"]
        result = app.empty_position(18)
        emptied = app.list_tools()[17]
        stored = next(item for item in app.list_inventory() if item["inventory_id"] == result["inventory_id"])
        self.assertEqual("", emptied["description"])
        self.assertEqual(uid, stored["tool_uid"])
        self.assertEqual("Fresa da conservare", stored["description"])
        self.assertEqual(118, stored["d_offset"])
        self.assertEqual(218, stored["h_offset"])
        self.assertEqual("C45", stored["cutting_parameters"][0]["material"])

    def test_moves_active_tool_between_free_slots_and_records_event(self):
        app.update_tool(3, {"description": "Punta mobile", "d_offset": 103, "h_offset": 203})
        uid = app.list_tools()[2]["tool_uid"]
        app.move_active_tool(3, 7)
        tools = app.list_tools()
        self.assertEqual("", tools[2]["description"])
        self.assertEqual("Punta mobile", tools[6]["description"])
        self.assertEqual(uid, tools[6]["tool_uid"])
        self.assertEqual(7, tools[6]["t_number"])
        self.assertEqual(103, tools[6]["d_offset"])
        self.assertEqual(203, tools[6]["h_offset"])
        self.assertEqual("moved", app.list_events()[0]["event_type"])

    def test_material_library_has_starters_and_supports_custom_templates(self):
        names = {item["name"] for item in app.list_material_templates()}
        self.assertTrue({"Acciaio C45", "Acciaio inox", "Alluminio", "Ottone"}.issubset(names))
        created = app.save_material_template({"name": "Plastica POM", "vc_m_min": 250, "fz_mm_tooth": 0.06})
        updated = app.save_material_template({"name": "POM", "vc_m_min": 280}, created["id"])
        self.assertEqual("POM", updated["name"])
        self.assertEqual(280, updated["vc_m_min"])

    def test_attachments_follow_tool_between_slot_and_inventory(self):
        app.update_tool(2, {"description": "Fresa documentata"})
        uid = app.list_tools()[1]["tool_uid"]
        attachment = app.save_attachment(uid, "scheda tecnica.pdf", "application/pdf", b"%PDF-test")
        self.assertEqual("scheda tecnica.pdf", app.list_tools()[1]["attachments"][0]["original_name"])
        result = app.active_to_inventory(2)
        self.assertEqual(attachment["id"], app.list_inventory()[0]["attachments"][0]["id"])
        app.mount_inventory_tool(result["inventory_id"], 9)
        self.assertEqual(attachment["id"], app.list_tools()[8]["attachments"][0]["id"])
        app.delete_attachment(attachment["id"])
        self.assertEqual([], app.list_tools()[8]["attachments"])

    def test_export_restore_includes_inventory_templates_and_events(self):
        app.create_inventory_tool({"description": "Utensile di scorta", "tool_type": "Fresa"})
        exported = app.export_data()
        self.assertEqual(1, len(exported["inventory"]))
        app.delete_inventory_tool(app.list_inventory()[0]["inventory_id"])
        app.restore_export(exported)
        self.assertEqual("Utensile di scorta", app.list_inventory()[0]["description"])
        self.assertGreaterEqual(len(app.list_material_templates()), 4)
        self.assertTrue(app.list_events())

    def test_pdf_includes_inventory_material_library_and_events(self):
        app.create_inventory_tool({"description": "Fresa di scorta", "tool_type": "Fresa"})
        pdf = app.build_pdf_report(
            app.list_tools(), {"machine_name": "PentaMac / Visel"}, app.utc_now(),
            app.list_inventory(), app.list_material_templates(), app.list_events(),
        )
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 8000)

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

    def test_machine_table_pdf_uses_30_slots_materials_and_saved_colors(self):
        app.update_tool(1, {"description": "Fresa prova", "icon": "end_mill", "d_offset": 41, "h_offset": 51})
        for index, material in enumerate(("Alluminio", "C45", "Inox", "Ottone", "POM", "Rame", "Titanio"), 1):
            app.upsert_cutting(1, {"material": material, "feed_mm_min": index * 100, "rpm": index * 1000})
        saved = app.save_tool_type_colors({"colors": {"end_mill": "#123ABC"}})
        self.assertEqual("#123ABC", saved["end_mill"])
        pdf = app.build_machine_table_pdf(
            app.list_tools(), {"machine_name": "PentaMac / Visel"}, app.list_tool_type_colors(), app.utc_now()
        )
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 10000)

    def test_rejects_invalid_machine_table_color(self):
        with self.assertRaises(ValueError):
            app.save_tool_type_colors({"colors": {"end_mill": "rosso"}})

    def test_validation_reports_duplicate_numbers_and_missing_diameter(self):
        app.update_tool(2, {"description": "Fresa A", "diameter_mm": 10, "t_number": 7, "d_offset": 8, "h_offset": 9})
        app.update_tool(5, {"description": "Fresa B", "t_number": 7, "d_offset": 8, "h_offset": 9})
        report = app.validation_report()
        self.assertEqual({"duplicate_t", "duplicate_d", "duplicate_h", "missing_diameter"}, {item["type"] for item in report["warnings"]})
        self.assertEqual([2, 5], report["slots"])

    def test_validation_ignores_default_numbers_in_empty_slots(self):
        app.update_tool(4, {"description": "Fresa", "diameter_mm": 6})
        report = app.validation_report()
        self.assertEqual(0, report["count"])
        self.assertEqual([], report["slots"])

    def test_visel_settings_are_persistent_and_safe(self):
        saved = app.save_visel_settings({
            "controller_model": "PentaMac 30", "software_version": "4.2",
            "host": "visel.example.test", "connection_type": "network_unknown", "notes": "Porta da verificare",
        })
        self.assertEqual("PentaMac 30", saved["controller_model"])
        self.assertEqual("configuration_saved", saved["state"])
        self.assertFalse(saved["connected"])
        self.assertTrue(saved["safe_mode"])
        self.assertEqual("visel.example.test", app.get_visel_settings()["host"])

    def test_global_search_covers_all_magazine_sections(self):
        app.update_tool(3, {"description": "Fresa montata speciale", "diameter_mm": 10, "t_number": 41})
        app.upsert_cutting(3, {"material": "Titanio ricerca", "notes": "Parametri prova"})
        app.update_tool(7, {"description": "Punta storica ricerca", "diameter_mm": 6})
        uid = app.list_tools()[6]["tool_uid"]
        app.save_attachment(uid, "catalogo-ricerca.pdf", "application/pdf", b"%PDF-test")
        app.archive_active_tool(7)
        inventory = app.create_inventory_tool({"description": "Alesatore Officina ricerca", "diameter_mm": 12})
        app.save_material_template({"name": "Bronzo ricerca", "vc_m_min": 120})

        self.assertEqual("active", app.global_search("T41")[0]["type"])
        active = next(item for item in app.global_search("Titanio ricerca") if item["type"] == "active")
        self.assertEqual("Titanio ricerca", active["cutting_parameters"][0]["material"])
        self.assertTrue(any(item["type"] == "history" for item in app.global_search("Punta storica ricerca")))
        self.assertTrue(any(item["type"] == "document" for item in app.global_search("catalogo-ricerca")))
        workshop = app.global_search("Alesatore Officina ricerca")
        self.assertEqual(inventory["inventory_id"], next(item for item in workshop if item["type"] == "inventory")["inventory_id"])
        self.assertTrue(any(item["type"] == "material" for item in app.global_search("Bronzo ricerca")))


if __name__ == "__main__":
    unittest.main()
