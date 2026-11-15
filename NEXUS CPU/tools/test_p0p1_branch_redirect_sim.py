import unittest
from p0p1_branch_redirect_sim import simulate_redirect, simulate_integrated_redirect


class BranchRedirectTests(unittest.TestCase):
    def test_default_redirect_discards_one_wrong_block(self):
        r=simulate_redirect()
        self.assertEqual(r.refill_latency,168)
        self.assertEqual(r.wrong_path_bytes_discarded,8192)
        self.assertEqual(r.redirect_stall_cycles,168)
        self.assertEqual(r.redirect_refill_count,1)
        self.assertEqual(r.target_ready_cycle,1360)

    def test_redirect_after_later_block(self):
        r=simulate_redirect(branch_block=3,target_block=9)
        self.assertEqual(r.target_ready_cycle,168+3*1024+1024+168)

    def test_integrated_redirect_uses_selected_frontend_rates(self):
        r = simulate_integrated_redirect()
        self.assertEqual(r.app_refill_cycles, 168)
        self.assertEqual(r.p0p1_to_c0_cycles, 128)
        self.assertEqual(r.c0_to_cs_cycles, 103)
        self.assertEqual(r.cs_to_eb_cycles, 103)
        self.assertEqual(r.eb_delivery_cycles, 128)
        self.assertEqual(r.target_delivery_latency, 630)
        self.assertEqual(r.p0p1_wrong_path_block_discarded_bytes, 8192)
        self.assertEqual(r.queued_wrong_path_pages_flushed, 2)
        self.assertEqual(r.queued_wrong_path_bytes_flushed, 4096)
        self.assertEqual(r.target_ready_cycle, 1310)

    def test_integrated_redirect_rejects_negative_flush_count(self):
        with self.assertRaises(ValueError):
            simulate_integrated_redirect(queued_wrong_path_pages=-1)

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            simulate_redirect(branch_block=2,target_block=3)


if __name__ == "__main__":
    unittest.main()
