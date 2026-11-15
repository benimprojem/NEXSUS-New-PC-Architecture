#!/usr/bin/env python3
import unittest

from p0p1_l0i_px_workload_sweep import MIDDLE_RATES, PAGE_COUNTS, run_sweep


class FrontendWorkloadSweepTests(unittest.TestCase):
    def test_matrix_shape_and_work_completion(self):
        data = run_sweep()
        self.assertEqual(data["cases"], 21)
        self.assertEqual(data["page_counts"], list(PAGE_COUNTS))
        self.assertEqual(data["middle_rates_bytes_per_cycle"], list(MIDDLE_RATES))
        self.assertEqual(len(data["results"]), 21)
        for row in data["results"]:
            with self.subTest(pages=row["pages"], rate=row["middle_rate_bytes_per_cycle"]):
                self.assertEqual(row["pages_requested"], row["pages"])
                self.assertEqual(row["pages_retired"], row["pages"])
                self.assertEqual(row["app_refill_latency"], 168)
                self.assertEqual(row["p0p1_refills"], (row["pages"] + 3) // 4)
                self.assertEqual(row["app_bytes_read"], row["p0p1_refills"] * 8192)
                self.assertEqual(row["boundary_stall_cycles"], 0)
                self.assertTrue(all(value <= 2 for value in row["queue_peaks"].values()))

    def test_known_32_page_reference_points(self):
        data = run_sweep()
        cycles = {
            row["middle_rate_bytes_per_cycle"]: row["cycles"]
            for row in data["results"] if row["pages"] == 32
        }
        self.assertEqual(cycles, {16: 4652, 20: 4602, 32: 4524})

    def test_faster_middle_stages_do_not_increase_cycles(self):
        data = run_sweep()
        by_pages = {}
        for row in data["results"]:
            by_pages.setdefault(row["pages"], {})[row["middle_rate_bytes_per_cycle"]] = row["cycles"]
        for pages, rates in by_pages.items():
            with self.subTest(pages=pages):
                self.assertLessEqual(rates[20], rates[16])
                self.assertLessEqual(rates[32], rates[20])


if __name__ == "__main__":
    unittest.main()
