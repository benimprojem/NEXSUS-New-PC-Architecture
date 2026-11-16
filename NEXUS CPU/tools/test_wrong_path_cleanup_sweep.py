import unittest

from wrong_path_cleanup_sweep import run_cleanup_sweep


class WrongPathCleanupTests(unittest.TestCase):
    def test_matrix_size_and_cleanup_accounting(self):
        result = run_cleanup_sweep()
        self.assertEqual(result["target_delivery_cycles"], 630)
        self.assertEqual(result["cases"], 2 * 3 * 4 * 6)
        for row in result["results"]:
            self.assertEqual(row["queued_wrong_path_pages"], 2)
            self.assertEqual(row["wrong_path_block_bytes_invalidated"], 8192)
            self.assertEqual(row["wrong_path_queued_bytes_invalidated"], 4096)
            self.assertEqual(
                row["slot_cleanup_cycles"],
                max(row["queue_flush_cycles"], row["slot_invalidate_cycles"]),
            )

    def test_no_slot_conflict_preserves_prefetch_overlap(self):
        result = run_cleanup_sweep()
        rows = [r for r in result["results"]
                if not r["target_slot_conflict"]
                and r["flush_pages_per_cycle"] == 1
                and r["slot_invalidate_cycles"] == 4]
        self.assertEqual(
            [r["actual_overlap_cycles"] for r in rows],
            [0, 64, 128, 256, 512, 630],
        )
        self.assertEqual(len({r["target_ready_cycle"] for r in rows}), 6)

    def test_slot_conflict_blocks_prefetch_until_cleanup(self):
        result = run_cleanup_sweep()
        rows = [r for r in result["results"]
                if r["target_slot_conflict"]
                and r["flush_pages_per_cycle"] == 2
                and r["slot_invalidate_cycles"] == 1]
        self.assertTrue(all(r["actual_overlap_cycles"] == 0 for r in rows))
        self.assertTrue(all(r["target_fetch_start_cycle"] == 681 for r in rows))
        self.assertTrue(all(r["target_ready_cycle"] == 1311 for r in rows))
        self.assertEqual(len({r["target_ready_cycle"] for r in rows}), 1)

    def test_faster_queue_flush_reduces_cleanup_only_to_slot_floor(self):
        result = run_cleanup_sweep()
        rows = [r for r in result["results"]
                if r["target_slot_conflict"]
                and r["requested_overlap_cycles"] == 0
                and r["slot_invalidate_cycles"] == 4]
        by_rate = {r["flush_pages_per_cycle"]: r["slot_cleanup_cycles"]
                   for r in rows}
        self.assertEqual(by_rate, {1: 4, 2: 4, 4: 4})


if __name__ == "__main__":
    unittest.main()
