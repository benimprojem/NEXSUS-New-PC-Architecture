#!/usr/bin/env python3
"""NEX-T010: simultaneous mixed-resource CPU stress and independent memory paths."""
import unittest

import cpu_comparison_sim as sim


class MixedResourceStressT010(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = dict(sim.PROFILES["nexus_balanced_128"])
        workloads = sim.build_composite_workload(scale=1)
        # Keep distinct deterministic components in one operation stream.
        # Dependencies are remapped so every component retains its own graph.
        selected = (
            "numeric_tile",
            "streaming",
            "fp_fma_mixed",
            "vector_throughput",
            "me512_matrix",
            "vec_me512_memory_overlap",
            "atomic_contention",
            "irq_exception_stress",
            "cs_starvation",
        )
        cls.ops = []
        cls.expected_kinds = set()
        for name in selected:
            component = workloads[name]
            offset = len(cls.ops)
            for op in component:
                cls.ops.append(sim.Op(
                    len(cls.ops),
                    op.kind,
                    tuple(dep + offset for dep in op.deps),
                    op.address,
                    op.width,
                    op.label,
                    op.command_address,
                    op.exec_width_bits,
                ))
                cls.expected_kinds.add(op.kind)
        cls.features = {
            "task_workspace": True,
            "code_slots": True,
            "codeflow": True,
            "p0_capacity_kb": 16,
            "p0_refill_latency": 48,
        }
        cls.simulation_result = sim.simulate_cpu(
            {"mixed_resource_stress": cls.ops},
            cls.profile,
            8,
            dict(cls.features),
        )

    def test_all_resource_classes_execute_in_one_eight_core_run(self):
        self.assertGreater(len(self.ops), 0)
        run = self.simulation_result
        row = run["kernels"]["mixed_resource_stress"]
        self.assertEqual(run["cores_configured"], 8)
        self.assertEqual(row["active_cores"], 8)
        self.assertEqual(row["ops"], len(self.ops))
        self.assertEqual(len(row["per_core_cycles"]), 8)
        self.assertGreater(row["cycles"], 0)
        self.assertGreater(row["issue_span_cycles"], 0)
        self.assertTrue({
            "INT", "FP", "FMA", "LOAD", "STORE", "VEC_ADD",
            "ME512", "ATOM", "IRQ", "CTX"
        }.issubset(self.expected_kinds))

    def test_data_ram_and_app_ram_progress_independently_in_same_run(self):
        run = self.simulation_result
        row = run["kernels"]["mixed_resource_stress"]
        data = row["memory_controller"]
        app = row["app_ram_controller"]
        self.assertEqual(data["model"], "per_core_fabric_ports")
        self.assertEqual(data["per_core_bytes_per_cycle"], 64)
        self.assertEqual(data["active_core_count"], 8)
        self.assertEqual(data["aggregate_core_facing_capacity_bytes_per_cycle"], 512)
        self.assertGreater(data["transferred_bytes"], 0)
        self.assertEqual(sum(data["bytes_by_core"].values()), data["transferred_bytes"])
        self.assertEqual(set(data["bytes_by_core"]), set(range(8)))

        self.assertIsNotNone(app)
        self.assertEqual(app["per_core_bytes_per_cycle"], 64)
        self.assertEqual(app["active_core_count"], 8)
        self.assertEqual(app["aggregate_bytes_per_cycle"], 512)
        self.assertGreater(app["transferred_bytes"], 0)
        self.assertEqual(sum(app["bytes_by_core"].values()), app["transferred_bytes"])
        self.assertEqual(set(app["bytes_by_core"]), set(range(8)))

    def test_codeflow_and_resource_contention_are_observed(self):
        run = self.simulation_result
        row = run["kernels"]["mixed_resource_stress"]
        self.assertGreater(row["codeflow_counters"]["refills"], 0)
        self.assertGreater(row["codeflow_counters"]["app_ram_bytes"], 0)
        self.assertGreater(row["stall_counters"]["execution_unit_blocked_op_cycles"], 0)
        self.assertGreater(row["cache_accesses"]["DRAM"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
