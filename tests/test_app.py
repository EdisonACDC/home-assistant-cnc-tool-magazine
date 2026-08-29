import os
import tempfile
import unittest
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
        app.update_tool(9, {"description": "Utensile A"})
        history_id = app.archive_active_tool(9)
        app.update_tool(9, {"description": "Utensile B"})
        app.activate_history_tool(9, history_id)
        tool = app.list_tools()[8]
        self.assertEqual("Utensile A", tool["description"])
        self.assertEqual(1, len(tool["history"]))
        self.assertEqual("Utensile B", tool["history"][0]["description"])


if __name__ == "__main__":
    unittest.main()
