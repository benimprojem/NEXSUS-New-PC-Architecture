#!/usr/bin/env python3
"""NEX-T009: NEXSUS 1/2/4/8-core scaling and per-core path accounting."""
import unittest

import cpu_comparison_sim as sim


class CoreScalingT009(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = dict(sim.PROFILES["nexus_balanced_128"])
        cls.workloads = sim.build_composite_workload(scale=1)
        cls.features = {
            "task_workspace": False,
            "code_slots": True,
            "codeflow": True,
            "p0_capacity_kb": 16,
            "p0_refill_latency": 48,
        }

    def test_same_logical_work_scales_across_one_two_four_eight_cores(self):
        expected = len(self.workloads["integer_throughput"])
        for cores in (1, 2, 4, 8):
            with self.subTest(cores=cores):
                run = sim.simulate_cpu(
                    {"integer_throughput": self.workloads["integer_throughput"]},
                    self.profile, cores, dict(self.features),
                )
                row = run["kernels"]["integer_throughput"]
                self.assertEqual(run["cores_configured"], cores)
                self.assertEqual(row["active_cores"], cores)
                self.assertEqual(row["ops"], expected)
                self.assertEqual(len(row["per_core_cycles"]), cores)
                self.assertGreater(row["cycles"], 0)
                self.assertGreater(row["issue_span_cycles"], 0)

    def test_data_ram_paths_remain_independent_and_accounted_per_core(self):
        ops = self.workloads["streaming"]
        expected = len(ops)
        for cores in (1, 2, 4, 8):
            with self.subTest(cores=cores):
                run = sim.simulate_cpu(
                    {"streaming": ops}, self.profile, cores, dict(self.features),
                )
                row = run["kernels"]["streaming"]
                controller = row["memory_controller"]
                self.assertEqual(row["ops"], expected)
                self.assertEqual(controller["model"], "per_core_fabric_ports")
                self.assertEqual(controller["per_core_bytes_per_cycle"], 64)
                self.assertEqual(controller["active_core_count"], cores)
                self.assertEqual(
                    controller["aggregate_core_facing_capacity_bytes_per_cycle"],
                    64 * cores,
                )
                per_core = controller["bytes_by_core"]
                self.assertEqual(set(per_core), set(range(cores)))
                self.assertTrue(all(value > 0 for value in per_core.values()))
                self.assertEqual(sum(per_core.values()), controller["transferred_bytes"])

    def test_app_ram_codeflow_capacity_scales_separately_from_data_ram(self):
        ops = self.workloads["cs_starvation"]
        for cores in (1, 2, 4, 8):
            with self.subTest(cores=cores):
                run = sim.simulate_cpu(
                    {"instruction_stream": ops}, self.profile, cores,
                    dict(self.features),
                )
                row = run["kernels"]["instruction_stream"]
                app = row["app_ram_controller"]
                self.assertEqual(row["ops"], len(ops))
                self.assertIsNotNone(app)
                self.assertEqual(app["per_core_bytes_per_cycle"], 64)
                self.assertEqual(app["active_core_count"], cores)
                self.assertEqual(app["aggregate_bytes_per_cycle"], 64 * cores)
                self.assertGreater(app["transferred_bytes"], 0)
                self.assertEqual(
                    sum(app["bytes_by_core"].values()), app["transferred_bytes"]
                )
                self.assertEqual(row["memory_controller"]["per_core_bytes_per_cycle"], 64)
                self.assertEqual(
                    row["memory_controller"]["aggregate_core_facing_capacity_bytes_per_cycle"],
                    64 * cores,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
