"""
Unit tests for coil_model.py. Run with:
    guadaloop_lev_control/.venv/bin/python3 -m unittest Magnetic-Circuit-Model/test_coil_model.py
or just:
    guadaloop_lev_control/.venv/bin/python3 Magnetic-Circuit-Model/test_coil_model.py

Uses stdlib unittest (not pytest, which isn't in the project venv).
"""

import unittest

import coil_model as cm


class TestResistanceFormula(unittest.TestCase):
    # The original handoff assumed t_b = 1/4" (k=1.39). Bobbin wall is actually 1/8", which
    # shifts MLT by -1 in (-0.133 Ohm) and moves the D=9 fit to k=1.45. Handoff numbers are
    # kept as regression checks by passing the old t_b explicitly.
    def test_old_handoff_tb_quarter_inch_D9(self):
        self.assertAlmostEqual(cm.resistance(9, t_b=0.25, k=1.39, c=1.0), 4.00, delta=0.01)

    def test_old_handoff_tb_quarter_inch_D1(self):
        self.assertAlmostEqual(cm.resistance(1, t_b=0.25, k=1.39, c=1.0), 1.04, delta=0.01)

    def test_default_bobbin_is_eighth_inch(self):
        self.assertEqual(cm.BOBBIN_WALL_IN, 0.125)

    def test_defaults_match_measured_coils(self):
        # empirical 2026-10-13: D=1 -> 1.1 ohm, D=9 -> 3.8-4.0 ohm (3.9 used in the fit)
        self.assertAlmostEqual(cm.resistance(1), 1.1, delta=0.02)
        self.assertGreaterEqual(cm.resistance(9), 3.8)
        self.assertLessEqual(cm.resistance(9), 4.0)

    def test_k1_geometry_only_is_affine_in_D(self):
        # handoff gives a *rounded* display formula "0.27D + 0.67" for the k=1 (no
        # pillowing) reference. Plugging those rounded coefficients back in drifts from
        # the precise formula by ~0.03-0.04 Ohm at D=9 (rounding 0.2667->0.27 compounds
        # over D), so this uses a loose tolerance rather than the ~0.01 Ohm precision the
        # handoff's own formula achieves against itself.
        for D in (1, 9):
            self.assertAlmostEqual(cm.resistance(D, t_b=0.25, k=1.0, c=1.0), 0.27 * D + 0.67, delta=0.05)

    def test_k1_vs_k139_only_differ_in_long_side_term(self):
        # the two long (D-direction) sides are the only k-dependent term, so the k=1.39
        # vs k=1 gap should scale linearly with D and equal 2*(k-1)*rho*N*D.
        for D in (1, 5, 9):
            gap = cm.resistance(D, k=1.39) - cm.resistance(D, k=1.0)
            expected_gap = 2 * (1.39 - 1.0) * cm.RHO_OHM_PER_IN * cm.N_TURNS_DEFAULT * D
            self.assertAlmostEqual(gap, expected_gap, delta=1e-9)

    def test_temperature_correction(self):
        r20 = cm.resistance(5, T=20.0)
        r40 = cm.resistance(5, T=40.0)
        self.assertAlmostEqual(r40, r20 * (1 + 0.00393 * 20), delta=1e-9)

    def test_resistance_increases_with_depth(self):
        self.assertLess(cm.resistance(1), cm.resistance(5))
        self.assertLess(cm.resistance(5), cm.resistance(9))


class TestLayerGeometry(unittest.TestCase):
    def test_layer_counts_matches_handoff(self):
        # handoff: "250/34 -> 7 full layers plus 12 turns on layer 8"
        counts = cm._layer_turn_counts(h=1.5, d=0.043, N=250)
        self.assertEqual(counts, [34, 34, 34, 34, 34, 34, 34, 12])
        self.assertEqual(sum(counts), 250)

    def test_mean_radial_offset_matches_handoff(self):
        # handoff: "r_bar ~= 3.7d ~= 0.16 in, so 2*pi*r_bar ~= 1.0 in"
        r_bar = cm.mean_radial_offset_in(h=1.5, d=0.043, N=250)
        self.assertAlmostEqual(r_bar, 0.16, delta=0.01)
        self.assertAlmostEqual(2 * 3.14159265 * r_bar, 1.0, delta=0.05)

    def test_single_full_layer(self):
        # N turns that fit in exactly one layer -> every turn at the same offset.
        counts = cm._layer_turn_counts(h=1.5, d=0.043, N=10)
        self.assertEqual(counts, [10])
        r_bar = cm.mean_radial_offset_in(h=1.5, d=0.043, N=10)
        self.assertAlmostEqual(r_bar, 0.5 * 0.043, delta=1e-9)


class TestFitK(unittest.TestCase):
    def test_fit_k_recovers_known_k_from_synthetic_data(self):
        true_k = 1.25
        rows = [
            {"D_in": D, "R_ohm": cm.resistance(D, k=true_k), "method": "4wire",
             "temp_C": 20.0, "notes": "synthetic"}
            for D in (2.0, 6.0, 9.0)
        ]
        k_hat, se_k, n = fit = cm.fit_k(rows=rows)
        self.assertEqual(n, 3)
        self.assertAlmostEqual(k_hat, true_k, delta=1e-6)
        self.assertGreater(se_k, 0)

    def test_fit_k_c_reproduces_defaults(self):
        k, c, _, _, n = cm.fit_k_c()  # real measurements.csv
        self.assertEqual(n, 2)
        self.assertAlmostEqual(k, cm.K_BULGE_DEFAULT, delta=0.01)
        self.assertAlmostEqual(c, cm.C_SCALE_DEFAULT, delta=0.01)

    def test_fit_k_c_recovers_synthetic(self):
        rows = [{"D_in": D, "R_ohm": cm.resistance(D, k=2.2, c=0.6), "method": "4wire",
                 "temp_C": 20.0, "notes": ""} for D in (1.0, 3.0, 7.0)]
        k, c, _, _, _ = cm.fit_k_c(rows=rows)
        self.assertAlmostEqual(k, 2.2, delta=1e-6)
        self.assertAlmostEqual(c, 0.6, delta=1e-6)

    def test_fit_k_c_needs_two_distinct_depths(self):
        rows = [{"D_in": 2.0, "R_ohm": 1.0, "method": "4wire", "temp_C": 20.0, "notes": ""}] * 2
        with self.assertRaises(ValueError):
            cm.fit_k_c(rows=rows)

    def test_fit_k_power_requires_3_points(self):
        with self.assertRaises(ValueError):
            cm.fit_k_power()  # measurements.csv only has 2 usable points

    def test_fit_k_power_recovers_power_law_from_synthetic_data(self):
        true_beta, true_p = 0.05, 1.5

        def k_of_D(D):
            return 1.0 + true_beta * D ** true_p

        rows = [
            {"D_in": D, "R_ohm": cm.resistance(D, k=k_of_D(D)), "method": "4wire",
             "temp_C": 20.0, "notes": "synthetic"}
            for D in (1.0, 3.0, 5.0, 7.0, 9.0)
        ]
        result = cm.fit_k_power(rows=rows)
        self.assertAlmostEqual(result["beta_power"], true_beta, delta=1e-3)
        self.assertAlmostEqual(result["p_power"], true_p, delta=1e-2)
        self.assertTrue(result["power_law_better"])


class TestReport(unittest.TestCase):
    def test_report_seeded_rows_pass(self):
        table = cm.report()
        by_D = {row["D_in"]: row for row in table}
        self.assertTrue(by_D[1.0]["passed"])
        self.assertTrue(by_D[9.0]["passed"])
        self.assertIsNone(by_D[5.0]["passed"])  # pending row: no measurement yet


if __name__ == "__main__":
    unittest.main()
