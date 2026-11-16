import unittest

from app_ram_contention_sweep import run_contention_sweep


class AppRamContentionTests(unittest.TestCase):
    def test_matrix_and_request_accounting(self):
        result = run_contention_sweep()
        self.assertEqual(result["cases"], 15)
        self.assertEqual(result["controller_geometry"]["per_core_bytes_per_cycle"], 64
        self.assertEqual(result["controller_geometry"]["aggregate_active_bytes_per_cycle"], 64)
        self.assertEqual(len(result["results"]), 15)
        for row in result["results"]:
            self.assertEqual(row["requests_accepted"], 2)
            self.assertEqual(row["transferred_bytes"], 2 * row["burst_bytes"])

    def test_target_priority_never_worsens_target_ready_time(self):
        result = run_contention_sweep()
        groups = {}
        for row in result["results"]:
            key = (row["burst_bytes"], row["bank_relation"])
            groups.setdefault(key, {})[row["policy"]] = row
        for key, policies in groups.items():
            self.assertLessEqual(
                policies["target_first"]["target_ready_cycle"],
                policies["equal"]["target_ready_cycle"],
                key,
            )
            self.assertLessEqual(
                policies["target_first"]["target_ready_cycle"],
                policies["speculative_first"]["target_ready_cycle"],
                key,
            )

    def test_speculative_priority_can_delay_correct_target(self):
        result = run_contention_sweep()
        row = next(
            r for r in result["results"]
            if r["burst_bytes"] == 2048
            and r["policy"] == "speculative_first"
        )
        self.assertEqual(row["target_ready_cycle"], 104)
        target_first = next(
            r for r in result["results"]
            if r["burst_bytes"] == 2048
            and r["policy"] == "target_first"
        )
        self.assertEqual(target_first["target_ready_cycle"], 72)

    def test_disjoint_short_bursts_have_no_bank_conflict(self):
        result = run_contention_sweep()
        rows = [
            r for r in result["results"]
            if r["bank_relation"] == "disjoint_banks"
        ]
        self.assertTrue(all(r["bank_conflicts"] == 0 for r in rows))


if __name__ == "__main__":
    unittest.main()
