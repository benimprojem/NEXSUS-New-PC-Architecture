import unittest
from p0p1_refill_sweep import run_sweep


class RefillSweepTests(unittest.TestCase):
    def test_sweep_coverage_and_invariants(self):
        data = run_sweep()
        self.assertEqual(data["blocks"], 16)
        self.assertEqual(data["cases"], len(data["results"]))
        self.assertGreater(data["cases"], 100)
        for row in data["results"]:
            self.assertEqual(row["refills"], 16)
            self.assertEqual(row["refill_bytes"], 16 * row["buffer_kb"] * 1024)
            self.assertEqual(row["refill_latency_cycles"],
                             row["transfer_cycles"] + row["setup_cycles"])
            self.assertGreaterEqual(row["boundary_stalls"], row["refill_latency_cycles"])
            self.assertEqual(row["starvation_after_cold_fill"],
                             row["boundary_stalls"] > row["refill_latency_cycles"])

    def test_reference_8k_configuration(self):
        rows = [r for r in run_sweep()["results"] if
                (r["buffer_kb"], r["app_bytes_per_cycle"], r["setup_cycles"],
                 r["consume_bytes_per_cycle"]) == (8, 64, 40, 8)]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["refill_latency_cycles"], 168)
        self.assertEqual(row["block_consume_cycles"], 1024)
        self.assertFalse(row["starvation_after_cold_fill"])


if __name__ == "__main__":
    unittest.main()
