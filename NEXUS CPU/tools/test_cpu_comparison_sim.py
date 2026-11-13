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
