#!/usr/bin/env python3
"""Focused regression tests for the NEXSUS CPU comparison simulator."""
import unittest

import cpu_comparison_sim as sim


class BandwidthPolicyTests(unittest.TestCase):
    def test_chip_wide_bandwidth_is_divided_across_configured_cores(self):
        profile = sim.PROFILES["nexus_balanced_128"]
        for cores, expected in ((8, 4.0), (16, 2.0), (32, 1.0), (64, 0.5)):
            with self.subTest(cores=cores):
                result = sim.simulate_cpu({"tiny": [sim.Op(0, "INT")]}, profile, cores)
                self.assertEqual(result["aggregate_dram_bytes_per_cycle"], 32)
                self.assertAlmostEqual(result["per_core_dram_bytes_per_cycle"], expected)
                self.assertEqual(
                    result["dram_bandwidth_policy"],
                    "static equal share across configured cores; not work-conserving",
                )

    def test_vendor_profiles_use_same_chip_wide_bandwidth_ceiling(self):
        for key in ("amd_9950x", "intel_285k_p", "intel_285k_e",
                    "nexus_candidate", "nexus_8l4s",
                    "nexus_balanced_128", "nexus_wide_balanced"):
            with self.subTest(profile=key):
                self.assertEqual(sim.PROFILES[key]["dram_bytes_per_cycle"], 32)


class SharedMemoryControllerTests(unittest.TestCase):
    def test_same_bank_requests_serialize_but_different_banks_overlap(self):
        same = sim.SharedMemoryController(bank_count=8, beat_bytes=8,
                                          aggregate_bytes_per_cycle=32)
        same_result = same.reserve_batch(0, [
            {"id": "a", "core": 0, "address": 0, "width": 8},
            {"id": "b", "core": 1, "address": 64, "width": 8},
        ], bank_hash="low")
        self.assertEqual(same_result["a"]["bank_wait"], 0)
        self.assertEqual(same_result["b"]["bank_wait"], 1)

        separate = sim.SharedMemoryController(bank_count=8, beat_bytes=8,
                                              aggregate_bytes_per_cycle=32)
        separate_result = separate.reserve_batch(0, [
            {"id": "a", "core": 0, "address": 0, "width": 8},
            {"id": "b", "core": 1, "address": 8, "width": 8},
        ], bank_hash="low")
        self.assertEqual(separate_result["a"]["bank_wait"], 0)
        self.assertEqual(separate_result["b"]["bank_wait"], 0)

    def test_bus_enforces_chip_wide_bandwidth_without_static_core_quotas(self):
        controller = sim.SharedMemoryController(
            bank_count=8, beat_bytes=8, aggregate_bytes_per_cycle=32
        )
        result = controller.reserve_batch(0, [
            {"id": "single-core-a", "core": 3, "address": 0, "width": 32},
            {"id": "single-core-b", "core": 3, "address": 8, "width": 32},
        ])
        self.assertEqual(result["single-core-a"]["bus_wait"], 0)
        self.assertEqual(result["single-core-b"]["bus_wait"], 1)
        self.assertEqual(controller.bus_next_cycle, 2)

    def test_rotating_priority_changes_first_core_between_batches(self):
        controller = sim.SharedMemoryController()
        first = controller.reserve_batch(0, [
            {"id": "c0", "core": 0, "address": 0, "width": 32},
            {"id": "c1", "core": 1, "address": 8, "width": 32},
        ])
        second = controller.reserve_batch(2, [
            {"id": "c0", "core": 0, "address": 16, "width": 32},
            {"id": "c1", "core": 1, "address": 24, "width": 32},
        ])
        self.assertEqual(first["c0"]["bus_wait"], 0)
        self.assertEqual(second["c1"]["bus_wait"], 0)


class CandidateProfileTests(unittest.TestCase):
    def test_balanced_128_matches_experimental_target(self):
        p = sim.PROFILES["nexus_balanced_128"]
        self.assertEqual((p["frontend"], p["dispatch"], p["issue"], p["retire"], p["rob"]),
                         (8, 8, 10, 8, 128))
        self.assertEqual(p["units"], {
            "INT": 4, "FP": 4, "VEC": 2, "LOAD": 8,
            "STORE": 4, "BR": 2, "CTX": 1, "ATOM": 1,
        })

    def test_wide_balanced_differs_only_by_window_size(self):
        a = dict(sim.PROFILES["nexus_balanced_128"])
        b = dict(sim.PROFILES["nexus_wide_balanced"])
        self.assertEqual(a.pop("rob"), 128)
        self.assertEqual(b.pop("rob"), 192)
        a.pop("name")
        b.pop("name")
        self.assertEqual(a, b)


class WorkloadPartitionTests(unittest.TestCase):
    def test_partition_preserves_operation_count_and_dependencies(self):
        workloads = sim.build_composite_workload(scale=1)
        for name, ops in workloads.items():
            with self.subTest(kernel=name):
                shards = sim.partition_dependency_components(ops, 8)
                self.assertEqual(sum(len(shard) for shard in shards), len(ops))
                for shard in shards:
                    for op in shard:
                        self.assertTrue(all(0 <= dep < len(shard) for dep in op.deps))


if __name__ == "__main__":
    unittest.main(verbosity=2)
