#!/usr/bin/env python3
"""Regression tests for the focused frontend bottleneck interaction sweep."""
import unittest

import p0p1_l0i_px_bottleneck_sweep as sweep


class FrontendBottleneckSweepTests(unittest.TestCase):
    def test_expected_rate_matrix_and_queue_cases(self):
        cases = sweep.build_cases()
        labels = [label for label, _ in cases]
        self.assertEqual(len(labels), 29)
        self.assertEqual(len(labels), len(set(labels)))
        self.assertIn("p0p1=8,eb=8", labels)
        self.assertIn("p0p1=32,eb=32", labels)
        self.assertIn("balanced16_queue=1", labels)
        self.assertIn("balanced16_queue=8", labels)

    def test_baseline_matches_integrated_frontend(self):
        data = sweep.run_sweep(8)
        baseline = next(row for row in data["results"] if row["case"] == "p0p1=8,eb=8")
        self.assertEqual(data["baseline_cycles"], baseline["cycles"])
        self.assertEqual(baseline["pages_retired"], 8)
        self.assertEqual(baseline["p0p1_to_c0_busy_cycles"], 8 * 256)
        self.assertEqual(baseline["eb_consume_busy_cycles"], 8 * 256)

    def test_all_cases_retire_identical_work_and_respect_queue_bounds(self):
        data = sweep.run_sweep(8)
        self.assertEqual(data["cases"], 29)
        for row in data["results"]:
            with self.subTest(case=row["case"]):
                self.assertEqual(row["pages_retired"], 8)
                depth = row["config"]["queue_depth"]
                for stage in ("c0", "cs", "eb"):
                    self.assertLessEqual(row["queue_peaks"][stage], depth)

    def test_nonpositive_page_count_rejected(self):
        with self.assertRaises(ValueError):
            sweep.run_sweep(0)


if __name__ == "__main__":
    unittest.main()
