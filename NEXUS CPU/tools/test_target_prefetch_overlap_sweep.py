import unittest

from target_prefetch_overlap_sweep import (
    OVERLAP_CYCLES,
    run_target_prefetch_sweep,
)


class TargetPrefetchOverlapTests(unittest.TestCase):
    def test_overlap_hides_target_delivery_without_changing_wrong_path_cost(self):
        result = run_target_prefetch_sweep()
        self.assertEqual(
            result["serialized_target_delivery_cycles"],
            630,
        )
        rows = [result["results"][str(x)] for x in OVERLAP_CYCLES]
        self.assertEqual(rows[0]["remaining_target_wait_cycles"], 630)
        self.assertEqual(rows[-1]["remaining_target_wait_cycles"], 0)
        self.assertEqual(rows[-1]["hidden_delivery_cycles"], 630)
        self.assertEqual(
            len({row["wrong_path_block_bytes_discarded"] for row in rows}),
            1,
        )
        self.assertEqual(
            len({row["wrong_path_queued_bytes_flushed"] for row in rows}),
            1,
        )
        self.assertTrue(
            all(
                rows[i]["target_ready_cycle"] >= rows[i + 1]["target_ready_cycle"]
                for i in range(len(rows) - 1)
            )
        )

    def test_no_prefetch_baseline_includes_branch_penalty(self):
        result = run_target_prefetch_sweep()
        row = result["results"]["0"]
        self.assertEqual(
            row["target_ready_cycle"],
            result["branch_resolution_cycle"] + 8 + 630,
        )
        self.assertEqual(row["cycles_saved_vs_no_prefetch"], 0)


if __name__ == "__main__":
    unittest.main()
