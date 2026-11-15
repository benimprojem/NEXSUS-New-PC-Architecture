#!/usr/bin/env python3
"""Regression tests for the integrated instruction frontend parameter sweep."""
import unittest

import p0p1_l0i_px_integrated_sweep as sweep
from p0p1_l0i_px_integrated_sim import Config, IntegratedFrontend


class IntegratedFrontendSweepTests(unittest.TestCase):
    def test_sweep_contains_baseline_one_factor_and_interaction_cases(self):
        cases = sweep.build_cases()
        labels = [label for label, _ in cases]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(labels[0], "baseline")
        self.assertIn("app_bandwidth=16", labels)
        self.assertIn("c0_to_cs=32", labels)
        self.assertIn("slow_app_and_narrow_downstream", labels)
        self.assertIn("slow_consumer_shallow_queues", labels)
        self.assertIn("fast_frontend_and_deep_queues", labels)
        self.assertGreaterEqual(len(cases), 20)

    def test_baseline_matches_integrated_simulator(self):
        data = sweep.run_sweep(pages=12)
        baseline = next(row for row in data["results"] if row["case"] == "baseline")
        expected = IntegratedFrontend(Config()).run(12)
        self.assertEqual(data["cases"], len(sweep.build_cases()))
        self.assertEqual(baseline["cycles"], expected.cycles)
        self.assertEqual(baseline["pages_retired"], 12)
        self.assertEqual(baseline["app_refill_latency"], 168)
        self.assertEqual(baseline["cold_stall_cycles"], 168)
        self.assertEqual(baseline["boundary_stall_cycles"], 0)

    def test_every_case_retires_same_requested_workload(self):
        data = sweep.run_sweep(pages=8)
        self.assertEqual(data["pages"], 8)
        for row in data["results"]:
            with self.subTest(case=row["case"]):
                self.assertEqual(row["pages_requested"], 8)
                self.assertEqual(row["pages_retired"], 8)
                self.assertEqual(row["p0p1_refills"], 2)
                self.assertEqual(row["app_bytes_read"], 2 * 8192)
                self.assertEqual(
                    row["cycles_delta_vs_baseline"] if "cycles_delta_vs_baseline" in row
                    else row["cycle_delta_vs_baseline"],
                    row["cycles"] - data["baseline_cycles"],
                )
                for stage in ("c0", "cs", "eb"):
                    self.assertLessEqual(row["queue_peaks"][stage],
                                         row["config"]["queue_depth"])

    def test_nonpositive_page_count_rejected(self):
        with self.assertRaises(ValueError):
            sweep.run_sweep(0)


if __name__ == "__main__":
    unittest.main()
