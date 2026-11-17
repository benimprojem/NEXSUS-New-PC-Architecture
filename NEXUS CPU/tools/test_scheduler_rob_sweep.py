#!/usr/bin/env python3
"""Contract tests for the fixed-512 ROB / 64-vs-128 scheduler experiment."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("scheduler_rob_sweep", HERE / "scheduler_rob_sweep.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load scheduler_rob_sweep.py")
SWEEP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SWEEP
SPEC.loader.exec_module(SWEEP)


class SchedulerRobSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = SWEEP.run_sweep(scale=1)

    def test_sweep_covers_both_scheduler_sizes_all_core_counts_and_kernels(self):
        expected = 2 * 4 * len(SWEEP.KERNELS)
        self.assertEqual(self.result["row_count"], expected)
        self.assertEqual(self.result["scheduler_entries_tested"], [64, 128])
        self.assertEqual(self.result["cores"], [1, 2, 4, 8])
        self.assertEqual(len(self.result["paired_comparison"]), 4 * len(SWEEP.KERNELS))

    def test_rob_is_512_and_scheduler_is_independently_bounded(self):
        for row in self.result["rows"]:
            with self.subTest(cores=row["cores"], kernel=row["kernel"],
                              scheduler=row["scheduler_entries"]):
                self.assertEqual(row["rob_entries"], 512)
                self.assertLessEqual(row["max_rob_occupancy"], 512)
                self.assertLessEqual(row["max_scheduler_occupancy"], row["scheduler_entries"])
                self.assertGreater(row["cycles"], 0)
                self.assertGreater(row["ops"], 0)
                self.assertGreaterEqual(row["scheduler_full_cycles"], 0)
                self.assertGreaterEqual(row["rob_full_cycles"], 0)

    def test_paired_runs_execute_identical_operation_counts(self):
        for cores in SWEEP.CORE_COUNTS:
            for kernel in SWEEP.KERNELS:
                rows = [row for row in self.result["rows"]
                        if row["cores"] == cores and row["kernel"] == kernel]
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["ops"], rows[1]["ops"])

    def test_stress_workload_exposes_scheduler_window_pressure(self):
        rows = {
            row["scheduler_entries"]: row
            for row in self.result["rows"]
            if row["cores"] == 8 and row["kernel"] == "scheduler_window_stress"
        }
        self.assertEqual(set(rows), {64, 128})
        self.assertEqual(rows[64]["rob_entries"], 512)
        self.assertGreater(rows[64]["scheduler_full_cycles"], 0)
        self.assertLess(rows[128]["scheduler_full_cycles"],
                        rows[64]["scheduler_full_cycles"])
        self.assertGreater(rows[128]["max_scheduler_occupancy"],
                           rows[64]["max_scheduler_occupancy"])

    def test_experiment_does_not_auto_select_hardware_value(self):
        self.assertIn("No scheduler capacity selected automatically",
                      self.result["decision"])
        self.assertEqual(self.result["rob_entries_fixed"], 512)


if __name__ == "__main__":
    unittest.main(verbosity=2)
