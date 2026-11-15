import unittest
from p0p1_branch_redirect_sim import simulate_redirect


class BranchRedirectTests(unittest.TestCase):
    def test_default_redirect_discards_one_wrong_block(self):
        r=simulate_redirect()
        self.assertEqual(r.refill_latency,168)
        self.assertEqual(r.wrong_path_bytes_discarded,8192)
        self.assertEqual(r.redirect_stall_cycles,168)
        self.assertEqual(r.redirect_refill_count,1)
        self.assertEqual(r.target_ready_cycle,1192)

    def test_redirect_after_later_block(self):
        r=simulate_redirect(branch_block=3,target_block=9)
        self.assertEqual(r.target_ready_cycle,168+3*1024+1024+168)

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            simulate_redirect(branch_block=2,target_block=3)


if __name__ == "__main__":
    unittest.main()
