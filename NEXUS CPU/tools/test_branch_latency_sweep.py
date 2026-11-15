import unittest

from branch_latency_sweep import DEFAULT_PENALTIES, TARGET_KERNELS, run_branch_latency_sweep


class BranchLatencySweepTests(unittest.TestCase):
    def test_sweep_preserves_work_and_mispredict_pattern(self):
        result = run_branch_latency_sweep(scale=1)
        self.assertEqual(result["penalties_cycles"], list(DEFAULT_PENALTIES))
        self.assertEqual(set(result["results"]), {str(x) for x in DEFAULT_PENALTIES})
        for penalty, kernels in result["results"].items():
            self.assertEqual(set(kernels), set(TARGET_KERNELS))
            for name, row in kernels.items():
                self.assertTrue(row["ops_preserved"], (penalty, name))
                self.assertGreater(row["ops"], 0)
                self.assertGreaterEqual(row["mispredicts"], 0)
                self.assertGreaterEqual(row["branch_recovery_cycles"], 0)

    def test_more_recovery_cycles_do_not_reduce_branch_stress_cost(self):
        result = run_branch_latency_sweep(scale=1)
        rows = [
            result["results"][str(penalty)]["branch_stress"]
            for penalty in DEFAULT_PENALTIES
        ]
        self.assertGreater(rows[0]["mispredicts"], 0)
        self.assertEqual(len({row["mispredicts"] for row in rows}), 1)
        self.assertEqual(len({row["ops"] for row in rows}), 1)
        self.assertLess(rows[0]["cycles"], rows[-1]["cycles"])
        self.assertLessEqual(
            rows[0]["branch_recovery_cycles"],
            rows[-1]["branch_recovery_cycles"],
        )


if __name__ == "__main__":
    unittest.main()
