#!/usr/bin/env python3
"""NEX-T006: per-core execution resource and dependency-latency contract."""
import unittest

import cpu_comparison_sim as sim


class ExecutionResourceContractT006(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = sim.PROFILES["nexus_balanced_128"]
        cls.workloads = sim.build_composite_workload(scale=1)

    def test_registered_per_core_resource_counts_and_latencies(self):
        p = self.profile
        self.assertEqual(p["units"]["INT"], 8)
        self.assertEqual(p["units"]["FP"], 6)
        self.assertEqual(p["units"]["FMA"], 4)
        self.assertEqual(p["units"]["VEC"], 2)
        self.assertEqual(p["units"]["ME512"], 1)
        self.assertEqual(p["latency"]["INT"], 1)
        self.assertEqual(p["latency"]["FP"], 3)
        self.assertEqual(p["latency"]["VEC"], 2)
        self.assertEqual(p["latency"]["ME512"], 4)

    def test_fma_is_four_lane_subset_of_six_fp64_lanes(self):
        p = self.profile
        self.assertNotIn("FMA_LANES", p["execution_topology"])
        self.assertEqual(sim.execution_resource_kind("FMA", "ME512"), "FMA")
        self.assertEqual(sim.execution_resource_kind("FP", "ME512"), "FP")

    def test_vector_opcodes_use_two_vector_slots_not_me512(self):
        for opcode in ("VEC_ADD", "VEC_SUB", "VEC_MUL", "VEC_FMA", "VEC_PERMUTE", "VEC_REDUCE"):
            with self.subTest(opcode=opcode):
                self.assertEqual(sim.execution_resource_kind(opcode, "ME512"), "VEC")
        self.assertEqual(sim.execution_resource_kind("ME512", "ME512"), "ME512")

    def test_independent_issue_and_dependency_latency_are_separate_for_vec(self):
        independent = self.workloads["vector_throughput"]
        chain = self.workloads["vec_add_dependency_chain"]
        self.assertEqual(len(independent), 256)
        self.assertEqual(len(chain), 64)
        self.assertTrue(all(not op.deps for op in independent))
        self.assertTrue(all(chain[i].deps == (i - 1,) for i in range(1, len(chain))))

        run = sim.simulate_cpu(
            {"vec_independent": independent, "vec_chain": chain},
            self.profile, 8, {"execution_only": True},
        )
        rows = run["kernels"]
        self.assertEqual(rows["vec_independent"]["ops"], 256)
        self.assertEqual(rows["vec_chain"]["ops"], 64)
        self.assertGreater(rows["vec_independent"]["issue_span_cycles"], 0)
        self.assertGreater(rows["vec_chain"]["issue_span_cycles"], 0)
        self.assertGreater(rows["vec_chain"]["cycles"], rows["vec_independent"]["cycles"])

    def test_independent_issue_and_dependency_latency_are_separate_for_me512(self):
        independent = self.workloads["me512_independent_throughput"]
        chain = self.workloads["me512_dependency_chain"]
        self.assertEqual(len(independent), 128)
        self.assertEqual(len(chain), 128)
        self.assertTrue(all(not op.deps for op in independent))
        self.assertTrue(all(chain[i].deps == (i - 1,) for i in range(1, len(chain))))

        run = sim.simulate_cpu(
            {"me512_independent": independent, "me512_chain": chain},
            self.profile, 8, {"execution_only": True},
        )
        rows = run["kernels"]
        self.assertEqual(rows["me512_independent"]["ops"], 128)
        self.assertEqual(rows["me512_chain"]["ops"], 128)
        self.assertGreater(rows["me512_independent"]["issue_span_cycles"], 0)
        self.assertGreater(rows["me512_chain"]["issue_span_cycles"], 0)
        self.assertGreater(rows["me512_chain"]["cycles"], rows["me512_independent"]["cycles"])

    def test_128_bit_integer_reserves_two_lanes_as_one_issue_resource(self):
        workload = {"mixed_width": [
            sim.Op(0, "INT", exec_width_bits=128),
            sim.Op(1, "INT", exec_width_bits=64),
            sim.Op(2, "INT", exec_width_bits=64),
        ]}
        p = dict(self.profile)
        p["units"] = {**self.profile["units"], "INT": 2, "FP": 2}
        p["execution_topology"] = {"INT128_PAIRS": [[0, 1]]}
        row = sim.simulate_cpu(workload, p, 1, {"execution_only": True})["kernels"]["mixed_width"]
        self.assertEqual(row["ops"], 3)
        self.assertGreater(row["stall_counters"]["execution_unit_blocked_op_cycles"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
