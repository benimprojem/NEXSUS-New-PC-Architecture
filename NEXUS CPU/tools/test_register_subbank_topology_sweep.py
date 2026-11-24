#!/usr/bin/env python3
"""Regression checks for NEX-T019 physical register sub-bank topology sensitivity."""
import unittest
from register_subbank_topology_sweep import run_sweep


class RegisterSubbankTopologySweepTests(unittest.TestCase):
    def test_sweep_preserves_work_and_does_not_select_a_default(self):
        data = run_sweep(rounds=3)
        self.assertEqual(data["result_count"], 32)
        self.assertEqual(data["operations_per_case"], 21)
        self.assertFalse(data["architecture_defaults_selected"])
        self.assertEqual({r["status"] for r in data["results"]}, {"completed", "infeasible"})
        for row in data["results"]:
            self.assertEqual(row["logical_ops"], 21)
            if row["status"] == "completed":
                self.assertTrue(row["completed"])
                self.assertEqual(row["retired_ops"], 21)
                self.assertGreater(row["cycles"], 0)
            else:
                self.assertTrue(row["reason"])

    def test_two_bank_one_read_port_concentrated_pattern_is_infeasible(self):
        row = next(r for r in run_sweep(rounds=2)["results"]
                   if r["pattern"] == "concentrated"
                   and r["bank_count_per_class"] == 2
                   and r["read_ports_per_bank"] == 1
                   and r["write_ports_per_bank"] == 1)
        self.assertEqual(row["status"], "infeasible")
        self.assertIn("requires", row["reason"])

    def test_four_bank_one_read_write_port_concentrated_pattern_completes(self):
        row = next(r for r in run_sweep(rounds=2)["results"]
                   if r["pattern"] == "concentrated"
                   and r["bank_count_per_class"] == 4
                   and r["read_ports_per_bank"] == 1
                   and r["write_ports_per_bank"] == 1)
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["retired_ops"], row["logical_ops"])


if __name__ == "__main__":
    unittest.main()
