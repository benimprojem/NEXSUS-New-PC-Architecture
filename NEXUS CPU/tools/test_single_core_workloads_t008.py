#!/usr/bin/env python3
"""NEX-T008: controlled single-core workload and operation-count validation."""
import unittest

import cpu_comparison_sim as sim


class SingleCoreControlledWorkloadsT008(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = sim.PROFILES["nexus_balanced_128"]
        cls.workloads = sim.build_composite_workload(scale=1)
        cls.cases = {
            "scalar_control": "scalar/control-flow",
            "integer_throughput": "integer ALU",
            "fp_throughput": "FP64",
            "fma_throughput": "FMA",
            "vector_throughput": "512-bit vector",
            "me512_independent_throughput": "ME512",
            "branch_stress": "branch",
            "pointer_graph": "pointer-chasing",
            "cs_starvation": "instruction-stream",
        }
        cls.features = {
            "task_workspace": False,
            "code_slots": True,
            "codeflow": True,
            "p0_capacity_kb": 16,
            "p0_refill_latency": 48,
        }

    def test_all_required_workload_categories_exist(self):
        for name, category in self.cases.items():
            with self.subTest(category=category):
                self.assertIn(name, self.workloads)
                self.assertGreater(len(self.workloads[name]), 0)

    def test_each_workload_retires_exactly_its_declared_operation_count(self):
        for name, category in self.cases.items():
            ops = self.workloads[name]
            with self.subTest(category=category, operations=len(ops)):
                run = sim.simulate_cpu(
                    {name: ops}, self.profile, 1, dict(self.features)
                )
                row = run["kernels"][name]
                self.assertEqual(run["cores_configured"], 1)
                self.assertEqual(row["active_cores"], 1)
                self.assertEqual(row["ops"], len(ops))
                self.assertEqual(len(row["per_core_cycles"]), 1)
                self.assertGreater(row["cycles"], 0)
                self.assertGreater(row["issue_span_cycles"], 0)

    def test_instruction_stream_exercises_codeflow_refill(self):
        ops = self.workloads["cs_starvation"]
        run = sim.simulate_cpu(
            {"instruction_stream": ops}, self.profile, 1, dict(self.features)
        )
        row = run["kernels"]["instruction_stream"]
        self.assertEqual(row["ops"], len(ops))
        self.assertGreater(row["codeflow_counters"]["refills"], 0)
        self.assertGreater(row["codeflow_counters"]["useful_bytes"], 0)
        self.assertGreater(row["codeflow_counters"]["wait_cycles"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
