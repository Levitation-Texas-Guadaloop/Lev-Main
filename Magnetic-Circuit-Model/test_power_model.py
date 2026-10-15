import unittest

import coil_model
import power_model
from reluctance_model import YokeGeometry


class PowerModelTests(unittest.TestCase):
    def test_release_power_manual_r_matches_reference(self):
        r = power_model.release_current_power(YokeGeometry(), 5e-3, coil_resistance_ohm=2.0)
        self.assertAlmostEqual(r["i_release_amp"], 21.744, places=2)
        self.assertAlmostEqual(r["per_yoke"]["peak_power_w"], 1891.1, delta=0.5)
        self.assertAlmostEqual(r["per_yoke"]["series"]["voltage_v"], 86.97, delta=0.02)
        self.assertAlmostEqual(r["per_yoke"]["parallel"]["current_a"], 43.487, delta=0.01)

    def test_total_is_4x_per_yoke(self):
        r = power_model.release_current_power(YokeGeometry(), 5e-3, 2.0)
        self.assertAlmostEqual(r["total"]["peak_power_w"], 4 * r["per_yoke"]["peak_power_w"])
        self.assertAlmostEqual(r["total"]["series"]["current_a"], 4 * r["per_yoke"]["series"]["current_a"])
        self.assertAlmostEqual(r["total"]["parallel"]["voltage_v"], r["per_yoke"]["parallel"]["voltage_v"])

    def test_auto_resistance_ui_defaults(self):
        g = YokeGeometry(mass_kg=226.0)
        self.assertAlmostEqual(power_model.coil_resistance(g), coil_model.resistance(D=6, N=250))
        r = power_model.release_current_power(g, 6e-3)
        self.assertAlmostEqual(r["i_release_amp"], 8.412, places=2)
        self.assertAlmostEqual(r["per_yoke"]["peak_power_w"], 403.3, delta=0.5)
        self.assertAlmostEqual(r["total"]["peak_power_w"], 1613.2, delta=2)

    def test_budget_roundtrip(self):
        g = YokeGeometry(mass_kg=226.0)
        b = power_model.power_budget(g, 1613.2, gap_m=6e-3)
        self.assertAlmostEqual(b["i_coil_amp"], 8.412, delta=0.01)
        self.assertAlmostEqual(b["total"]["peak_power_w"], 1613.2)
        self.assertAlmostEqual(b["max_ampere_turns_per_coil"], b["i_coil_amp"] * 250)

    def test_budget_covers_flag(self):
        g = YokeGeometry(mass_kg=226.0)
        self.assertFalse(power_model.power_budget(g, 500, gap_m=6e-3)["covers_release"])
        self.assertTrue(power_model.power_budget(g, 4000, gap_m=6e-3)["covers_release"])

    def test_budget_rejects_nonpositive(self):
        with self.assertRaises(ValueError):
            power_model.power_budget(YokeGeometry(), 0)


if __name__ == "__main__":
    unittest.main()
