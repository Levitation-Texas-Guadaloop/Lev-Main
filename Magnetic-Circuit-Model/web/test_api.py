"""Stability sweep for api_server.compute: no exceptions/NaN across the knob ranges."""
import itertools
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import api_server  # noqa: E402


def _no_nan(o):
    json.dumps(o, allow_nan=False)  # raises on NaN/inf


class ApiTests(unittest.TestCase):
    def test_defaults_match_reference(self):
        r = api_server.compute({})
        self.assertAlmostEqual(r["g_eq_mm"], 7.485, places=2)
        self.assertAlmostEqual(r["release"]["i_release_amp"], 8.412, places=2)
        self.assertAlmostEqual(r["release"]["total"]["peak_power_w"], 1613.2, delta=2)
        self.assertAlmostEqual(r["R_ohm"], 2.8495, places=3)
        self.assertEqual(len(r["force"]["curves"]), 7)

    def test_knob_grid_is_stable(self):
        for N, D, m, s0, Rm in itertools.product(
            (10, 250, 1000), (1, 6, 20), (10, 226, 1000), (None, 0.5, 6.0, 50.0), (None, 3.0)
        ):
            r = api_server.compute({"N_turns": N, "ydepth_in": D, "mass_kg": m, "s0_mm": s0,
                                    "r_coil_ohm": Rm})
            _no_nan(r)
            self.assertIn(r["release"]["status"], ("ok", "error", "unset"))
            if r["release"]["status"] == "ok":
                self.assertGreater(r["release"]["i_release_amp"], 0)

    def test_manual_r_overrides_auto(self):
        r = api_server.compute({"r_coil_ohm": 3.0})
        self.assertEqual(r["R_ohm"], 3.0)
        self.assertIs(r["r_auto"], False)
        self.assertAlmostEqual(r["coil"]["R_auto_ohm"], 2.8495, places=3)

    def test_bad_input_raises_valueerror(self):
        for bad in ({"gap_min_mm": 10, "gap_max_mm": 5}, {"ceiling_w": 0}, {"N_turns": 0},
                    {"r_coil_ohm": -1}):
            with self.assertRaises(ValueError):
                api_server.compute(bad)


if __name__ == "__main__":
    unittest.main()
