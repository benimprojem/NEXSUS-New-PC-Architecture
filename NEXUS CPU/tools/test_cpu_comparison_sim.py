#!/usr/bin/env python3
"""Focused regression tests for the NEXSUS CPU comparison simulator."""
import unittest

import cpu_comparison_sim as sim


class BandwidthPolicyTests(unittest.TestCase):
    def test_bandwidth_is_shared_without_static_per_core_quota(self):
        profile = sim.PROFILES["nexus_balanced_128"]
        for cores in (8, 16, 32, 64):
            with self.subTest(cores=cores):
                result = sim.simulate_cpu({"tiny": [sim.Op(0, "INT")]}, profile, cores)
                self.assertEqual(result["aggregate_dram_bytes_per_cycle"], 32)
                self.assertIsNone(result["per_core_dram_bytes_per_cycle"])
                self.assertEqual(
                    result["dram_bandwidth_policy"],
                    "shared lockstep controller; work-conserving aggregate bus; no static per-core quota",
                )

    def test_vendor_profiles_use_same_chip_wide_bandwidth_ceiling(self):
        for key in ("amd_9950x", "intel_285k_p", "intel_285k_e", "nexus_balanced_128"):
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

    def test_unaligned_wide_access_reserves_extra_bank_beat(self):
        controller = sim.SharedMemoryController(
            bank_count=8, beat_bytes=8, aggregate_bytes_per_cycle=32
        )
        result = controller.reserve_batch(0, [
            {"id": "unaligned-512", "core": 0, "address": 1, "width": 64},
        ], bank_hash="low")
        # Nine 64-bit slices are touched; bank zero is used twice.
        self.assertEqual(result["unaligned-512"]["bank_wait"], 1)

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

    def test_lockstep_cores_contend_for_one_global_bank(self):
        profile_data = dict(sim.PROFILES["nexus_balanced_128"])
        profile_data["bank_hash"] = "low"
        profile = sim.profile_from_dict(profile_data)
        shards = [
            [sim.Op(0, "LOAD", address=0, width=8)],
            [sim.Op(0, "LOAD", address=64, width=8)],
        ]
        result = sim.simulate_multicore_streams(shards, profile, 32)
        self.assertEqual(result["cores"][0]["ready_at"][0], 128)
        self.assertEqual(result["cores"][1]["ready_at"][0], 129)

    def test_lockstep_cores_use_independent_banks_in_parallel(self):
        profile_data = dict(sim.PROFILES["nexus_balanced_128"])
        profile_data["bank_hash"] = "low"
        profile = sim.profile_from_dict(profile_data)
        shards = [
            [sim.Op(0, "LOAD", address=0, width=8)],
            [sim.Op(0, "LOAD", address=8, width=8)],
        ]
        result = sim.simulate_multicore_streams(shards, profile, 32)
        self.assertEqual(result["cores"][0]["ready_at"][0], 120)
        self.assertEqual(result["cores"][1]["ready_at"][0], 120)


class SelectedNexusProfileTests(unittest.TestCase):
    def test_only_selected_nexus_profile_is_exposed(self):
        self.assertEqual([k for k in sim.PROFILES if k.startswith("nexus_")], ["nexus_balanced_128"])

    def test_balanced_128_matches_selected_architecture(self):
        p = sim.PROFILES["nexus_balanced_128"]
        self.assertEqual((p["frontend"], p["dispatch"], p["issue"], p["retire"], p["rob"]),
                         (8, 8, 10, 8, 128))
        self.assertEqual(p["units"], {
            "INT": 4, "FP": 4, "VEC": 2, "LOAD": 8,
            "STORE": 4, "BR": 2, "CTX": 1, "ATOM": 1,
        })


class SharedCacheGroupTests(unittest.TestCase):
    def test_l1_is_private_but_l2_is_shared_by_pair(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        self.assertIsNot(caches[0].l1, caches[1].l1)
        self.assertIs(caches[0].l2, caches[1].l2)
        self.assertIsNot(caches[0].l2, caches[2].l2)
        caches[0].fill(0x1000, "DRAM")
        self.assertEqual(caches[1].probe(0x1000)[1], "L2")
        self.assertEqual(caches[2].probe(0x1000)[1], "L3")

    def test_l3_is_shared_by_four_cores(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        self.assertIs(caches[0].l3, caches[3].l3)
        self.assertIsNot(caches[0].l3, caches[4].l3)
        caches[0].fill(0x2000, "DRAM")
        self.assertEqual(caches[3].probe(0x2000)[1], "L3")
        self.assertEqual(caches[4].probe(0x2000)[1], "L4")

    def test_l4_is_shared_by_eight_core_group_not_next_group(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 16)
        self.assertIs(caches[0].l4, caches[7].l4)
        self.assertIsNot(caches[0].l4, caches[8].l4)
        caches[0].fill(0x3000, "DRAM")
        self.assertEqual(caches[7].probe(0x3000)[1], "L4")
        self.assertEqual(caches[8].probe(0x3000)[1], "DRAM")

    def test_shared_cache_fill_is_deferred_until_access_completion(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        latency, level = caches[0].probe(0x4000)
        self.assertEqual(level, "DRAM")
        self.assertEqual(caches[1].probe(0x4000)[1], "DRAM")
        caches[0].fill(0x4000, level)
        self.assertEqual(caches[1].probe(0x4000)[1], "L2")



class SpmP0ModelTests(unittest.TestCase):
    def test_spm2_enabled_hits_local_store_and_preserves_work(self):
        workloads = {"hot": [sim.Op(i, "LOAD", address=(i % 32)*64, width=64,
                                     label="SPM2: hot") for i in range(256)]}
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(workloads["hot"], 8)
        full = sim.simulate_multicore_streams(shards, p, 32, {"spm": True, "p0": True})
        off = sim.simulate_multicore_streams(shards, p, 32, {"spm": False, "p0": True})
        self.assertEqual(sum(len(x) for x in shards), 256)
        self.assertEqual(sum(x["spm"]["accesses"] for x in full["cores"]), 256)
        self.assertEqual(sum(x["spm"]["fallback_bytes"] for x in off["cores"]), 256*64)

    def test_spm2_capacity_overflow_falls_back_without_dropping_accesses(self):
        ops = [sim.Op(i, "LOAD", address=(i % 256)*64, width=64,
                      label="SPM2: capacity") for i in range(512)]
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(ops, 8)
        result = sim.simulate_multicore_streams(shards, p, 32, {"spm": True, "p0": True})
        counters = [x["spm"] for x in result["cores"]]
        self.assertEqual(sum(x["spm"]["accesses"] for x in result["cores"]), 256)
        self.assertEqual(sum(x["overflow"] for x in counters), 256)
        self.assertEqual(sum(x["fallback_bytes"] for x in counters), 256*64)

    def test_p0_and_conventional_fetch_paths_both_retire_same_work(self):
        ops = [sim.Op(i, "INT", command_address=(i % 2048)*8) for i in range(1024)]
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(ops, 8)
        p0 = sim.simulate_multicore_streams(shards, p, 32, {"spm": True, "p0": True})
        conventional = sim.simulate_multicore_streams(shards, p, 32, {"spm": True, "p0": False})
        self.assertEqual(sum(x["retired"] for x in p0["cores"]), 1024)
        self.assertEqual(sum(x["retired"] for x in conventional["cores"]), 1024)
        p0_wait = sum(x["fetch"].wait_cycles for x in p0["cores"])
        conventional_wait = sum(x["fetch"].wait_cycles for x in conventional["cores"])
        self.assertLess(p0_wait, conventional_wait)

    def test_p0_capacity_and_refill_parameters_are_explicit(self):
        p0 = sim.CommandFetchModel(True)
        conventional = sim.CommandFetchModel(False)
        self.assertEqual(p0.lines.capacity, 8192 // 64)
        self.assertEqual(conventional.lines.capacity, 32768 // 64)
        self.assertEqual((p0.refill_latency, conventional.refill_latency), (8, 32))

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
