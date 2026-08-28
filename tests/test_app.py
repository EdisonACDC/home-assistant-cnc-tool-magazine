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


if __name__ == "__main__":
    unittest.main()
