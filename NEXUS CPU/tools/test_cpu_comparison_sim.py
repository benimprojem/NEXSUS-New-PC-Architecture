#!/usr/bin/env python3
"""Focused regression tests for the NEXSUS CPU comparison simulator."""
import unittest

import cpu_comparison_sim as sim


class DataRamMSHRTests(unittest.TestCase):
    def test_capacity_sweep_preserves_all_cold_loads_and_bounds_occupancy(self):
        result = sim.run_data_mshr_sweep(
            sim.PROFILES["nexus_balanced_128"], capacities=(1, 2, 4, 8, 16, 32, 64, 128),
            ops_per_core=32,
        )
        self.assertEqual(set(result["results"]), {"1", "2", "4", "8", "16", "32", "64", "128"})
        for capacity, row in result["results"].items():
            with self.subTest(capacity=capacity):
                self.assertEqual(row["ops_retired"], 8 * 32)
                self.assertEqual(row["data_ram_requests"], 8 * 32)
                self.assertTrue(all(value <= int(capacity)
                                    for value in row["max_outstanding_per_core"]))
                self.assertIsNone(row["app_ram_controller"])
                self.assertEqual(row["total_full_cycles"], sum(row["full_cycles_per_core"]))
                self.assertLessEqual(row["total_full_cycles"], row["total_blocked_request_attempts"])
        self.assertGreater(result["results"]["1"]["total_blocked_request_attempts"], 0)
        self.assertGreater(result["results"]["1"]["total_full_cycles"], 0)
        self.assertEqual(result["results"]["128"]["total_full_cycles"], 0)
        self.assertGreaterEqual(
            result["results"]["1"]["cycles"], result["results"]["2"]["cycles"]
        )
        self.assertEqual(result["mixed_workload"]["pattern"],
                         "1 independent cold LOAD followed by 3 independent INT operations")
        self.assertEqual(set(result["mixed_results"]), set(result["results"]))
        for capacity, row in result["mixed_results"].items():
            with self.subTest(mixed_capacity=capacity):
                self.assertEqual(row["ops_retired"], 8 * 32 * 4)
                self.assertEqual(row["data_ram_requests"], 8 * 32)
                self.assertIsNone(row["app_ram_controller"])
                self.assertTrue(all(value <= int(capacity)
                                    for value in row["max_outstanding_per_core"]))
                self.assertEqual(row["total_full_cycles"], sum(row["full_cycles_per_core"]))
                self.assertLessEqual(row["total_full_cycles"], row["total_blocked_request_attempts"])
        self.assertGreater(result["mixed_results"]["1"]["total_full_cycles"], 0)
        self.assertEqual(result["mixed_results"]["128"]["total_full_cycles"], 0)

    def test_dependent_load_chain_does_not_need_extra_mshrs(self):
        shards = []
        for core_id in range(8):
            shard = []
            for seq in range(24):
                shard.append(sim.Op(
                    seq, "LOAD", deps=((seq - 1,) if seq else ()),
                    address=0x30000000 + core_id * 0x10000 + seq * 64,
                    width=8, label="dependent cold load chain",
                ))
            shards.append(shard)
        profile = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        one = sim.simulate_multicore_streams(
            shards, profile, 64,
            {"task_workspace": False, "code_slots": False, "data_mshr_entries": 1},
        )
        many = sim.simulate_multicore_streams(
            shards, profile, 64,
            {"task_workspace": False, "code_slots": False, "data_mshr_entries": 8},
        )
        self.assertEqual([core["retired"] for core in one["cores"]], [24] * 8)
        self.assertEqual(one["cycles"], many["cycles"])
        self.assertEqual(one["data_mshr"]["max_outstanding_per_core"], [1] * 8)
        self.assertEqual(one["data_mshr"]["total_full_cycles"], 0)

    def test_app_and_data_ram_traffic_progress_on_independent_controllers(self):
        shards = []
        for core_id in range(8):
            shard = []
            for seq in range(260):
                if seq % 2 == 0:
                    shard.append(sim.Op(
                        seq, "LOAD",
                        address=0x40000000 + core_id * 0x100000 + (seq // 2) * 64,
                        width=8, command_address=seq * 8,
                        label="concurrent App RAM and Data RAM traffic",
                    ))
                else:
                    shard.append(sim.Op(
                        seq, "INT", command_address=seq * 8,
                        label="interleaved compute",
                    ))
            shards.append(shard)
        profile = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        run = sim.simulate_multicore_streams(
            shards, profile, 64,
            {"task_workspace": True, "code_slots": True, "codeflow": True,
             "app_max_outstanding": 16, "data_mshr_entries": 8},
        )
        self.assertEqual([core["retired"] for core in run["cores"]], [260] * 8)
        app = run["app_controller"]
        data = run["controller"]
        self.assertIsNotNone(app)
        self.assertGreater(app["accepted"], 8)
        self.assertGreater(app["transferred_bytes"], 0)
        self.assertGreater(len(data["request_events"]), 0)
        overlap_cycles = set(app["request_cycles"]) & set(data["request_cycles"])
        self.assertTrue(overlap_cycles, "App RAM and Data RAM requests did not overlap")

    def test_per_core_mshrs_are_not_a_shared_global_pool(self):
        # Each core owns a local sequence beginning at zero. Addresses
        # are unique so every core issues one independent cold DRAM miss.
        shards = [[
            sim.Op(0, "LOAD", address=0x20000000 + core_id * 64, width=8,
                   label="independent core MSHR")
        ] for core_id in range(8)]
        profile = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        run = sim.simulate_multicore_streams(
            shards, profile, 64,
            {"task_workspace": False, "code_slots": False, "data_mshr_entries": 1},
        )
        self.assertEqual([core["retired"] for core in run["cores"]], [1] * 8)
        self.assertEqual(run["data_mshr"]["max_outstanding_per_core"], [1] * 8)
        self.assertEqual(run["data_mshr"]["total_full_events"], 0)
        self.assertEqual(len(run["controller"]["request_events"]), 8)


class BandwidthPolicyTests(unittest.TestCase):
    def test_bandwidth_is_shared_without_static_per_core_quota(self):
        profile = sim.PROFILES["nexus_balanced_128"]
        for cores in (8, 16, 32, 64):
            with self.subTest(cores=cores):
                result = sim.simulate_cpu({"tiny": [sim.Op(0, "INT")]}, profile, cores)
                self.assertEqual(result["aggregate_dram_bytes_per_cycle"], 64)
                self.assertIsNone(result["per_core_dram_bytes_per_cycle"])
                self.assertEqual(
                    result["dram_bandwidth_policy"],
                    "shared lockstep controller; work-conserving aggregate bus; no static per-core quota",
                )

    def test_vendor_profiles_use_same_chip_wide_bandwidth_ceiling(self):
        expected = {"amd_9950x3d2": 21, "intel_xeon_698x": 160,
                    "apple_m6": 48, "nexus_balanced_128": 64}
        for key, bandwidth in expected.items():
            with self.subTest(profile=key):
                self.assertEqual(sim.PROFILES[key]["dram_bytes_per_cycle"], bandwidth)


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
        self.assertEqual(separate_result["a"]["service_complete_cycle"], 1)
        self.assertEqual(separate_result["b"]["service_complete_cycle"], 1)

    def test_unrelated_busy_bank_does_not_delay_independent_request(self):
        controller = sim.SharedMemoryController(
            bank_count=8, beat_bytes=8, aggregate_bytes_per_cycle=32
        )
        result = controller.reserve_batch(0, [
            {"id": "bank0-a", "core": 0, "address": 0, "width": 8},
            {"id": "bank0-b", "core": 1, "address": 64, "width": 8},
            {"id": "bank1", "core": 2, "address": 8, "width": 8},
        ], bank_hash="low")
        self.assertEqual(result["bank0-a"]["service_complete_cycle"], 1)
        self.assertEqual(result["bank0-b"]["service_complete_cycle"], 2)
        self.assertEqual(result["bank1"]["bank_wait"], 0)
        self.assertEqual(result["bank1"]["service_complete_cycle"], 1)

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
        self.assertEqual(result["cores"][0]["ready_at"][0], 168)
        self.assertEqual(result["cores"][1]["ready_at"][0], 169)

    def test_lockstep_cores_use_independent_banks_in_parallel(self):
        profile_data = dict(sim.PROFILES["nexus_balanced_128"])
        profile_data["bank_hash"] = "low"
        profile = sim.profile_from_dict(profile_data)
        shards = [
            [sim.Op(0, "LOAD", address=0, width=8)],
            [sim.Op(0, "LOAD", address=8, width=8)],
        ]
        result = sim.simulate_multicore_streams(shards, profile, 32)
        self.assertEqual(result["cores"][0]["ready_at"][0], 168)
        self.assertEqual(result["cores"][1]["ready_at"][0], 168)


class SelectedNexusProfileTests(unittest.TestCase):
    def test_only_selected_nexus_profile_is_exposed(self):
        self.assertEqual([k for k in sim.PROFILES if k.startswith("nexus_")], ["nexus_balanced_128"])

    def test_balanced_128_matches_selected_architecture(self):
        p = sim.PROFILES["nexus_balanced_128"]
        self.assertEqual((p["frontend"], p["dispatch"], p["issue"], p["retire"], p["rob"]),
                         (8, 8, 10, 8, 128))
        self.assertEqual(p["units"], {
            "INT": 8, "FP": 6, "VEC": 2, "LOAD": 8,
            "STORE": 4, "BR": 2, "CTX": 1, "ATOM": 1, "ME512": 1, "IRQ": 1,
        })
        self.assertEqual(p["execution_topology"]["INT128_PAIRS"], [[0, 1], [2, 3]])
        self.assertEqual(p["execution_topology"]["FMA_LANES"], 4)
        self.assertLessEqual(p["execution_topology"]["FMA_LANES"], p["units"]["FP"])


class CachePortContentionTests(unittest.TestCase):
    def test_shared_l2_port_serializes_pair_but_other_group_is_independent(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        # L2 is shared by cores 0/1; core 2 belongs to another L2 object.
        self.assertEqual(caches[0].reserve("L2", 0, 64), 0)
        self.assertEqual(caches[1].reserve("L2", 0, 64), 1)
        self.assertEqual(caches[2].reserve("L2", 0, 64), 0)

    def test_l1_ports_are_private_and_multiple_ports_are_parameterized(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        self.assertEqual(caches[0].reserve("L1", 0, 64), 0)
        self.assertEqual(caches[1].reserve("L1", 0, 64), 0)
        port = sim.CachePort(ports=2, lines_per_port_cycle=1)
        self.assertEqual([port.reserve(0, 64) for _ in range(3)], [0, 0, 1])
        self.assertEqual(port.requests, 3)
        self.assertEqual(port.wait_cycles, 1)

    def test_wide_request_occupies_port_for_multiple_cycles(self):
        port = sim.CachePort(ports=1, lines_per_port_cycle=1)
        self.assertEqual(port.reserve(0, 128, 64), 0)
        self.assertEqual(port.reserve(0, 64, 64), 2)
        self.assertEqual(port.reserve(3, 64, 64), 0)


class NEXSUSCacheTopologyTests(unittest.TestCase):
    def test_eight_core_block_has_8_l1_4_l2_2_l3_1_l4_instances(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        self.assertEqual(len({id(c.l1) for c in caches}), 8)
        self.assertEqual(len({id(c.l2) for c in caches}), 4)
        self.assertEqual(len({id(c.l3) for c in caches}), 2)
        self.assertEqual(len({id(c.l4) for c in caches}), 1)

    def test_distinct_l3_groups_exchange_shared_lines_through_l4(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        address = 0xD000
        caches[0].prefill(address, "L4")
        self.assertIsNot(caches[0].l3, caches[4].l3)
        self.assertIsNot(caches[0].l2, caches[4].l2)
        self.assertIs(caches[0].l4, caches[4].l4)
        self.assertEqual(caches[4].probe(address)[1], "L4")

    def test_shared_l3_and_l4_port_contention_matches_topology(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        caches = sim.build_cache_hierarchies(p, 8)
        self.assertEqual(caches[0].reserve("L3", 0, 64), 0)
        self.assertEqual(caches[3].reserve("L3", 0, 64), 1)
        self.assertEqual(caches[4].reserve("L3", 0, 64), 0)
        self.assertEqual(caches[0].reserve("L4", 0, 64), 0)
        self.assertEqual(caches[4].reserve("L4", 0, 64), 1)
        self.assertEqual(caches[7].reserve("L4", 0, 64), 2)


class SharedCacheGroupTests(unittest.TestCase):
    def test_working_set_prefill_uses_the_collaboration_scope_home_level(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        cases = (
            ("L1", 0, 0, 1),
            ("L2", 0, 1, 2),
            ("L3", 0, 3, 4),
            ("L4", 0, 7, 8),
        )
        for level, owner, peer, outside in cases:
            with self.subTest(level=level):
                caches = sim.build_cache_hierarchies(p, 16)
                address = 0x700000 + (len(level) * 64)
                caches[owner].prefill(address, level)
                self.assertEqual(caches[peer].probe(address)[1], level)
                self.assertEqual(caches[outside].probe(address)[1], "DRAM")

    def test_l4_home_prefill_obeys_capacity_and_does_not_spill_down(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        p.l4_kb = 1  # 16 lines at the profile's 64-byte line size
        cache = sim.CacheHierarchy(p)
        cache.prefill(0x10000, "L4")
        cache.prefill(0x10040, "L4")
        self.assertEqual(cache.probe(0x10000)[1], "L4")
        self.assertFalse(cache.l3.lookup(0x10000 // cache.line))
        # Fill beyond L4 capacity; oldest prefilled line must be evicted.
        for i in range(16):
            cache.prefill(0x20000 + i * cache.line, "L4")
        self.assertEqual(cache.probe(0x10000)[1], "DRAM")
        self.assertEqual(cache.probe(0x10040)[1], "DRAM")
        self.assertEqual(cache.probe(0x20000 + 15 * cache.line)[1], "L4")

    def test_cache_probe_reports_each_level_latency_without_implicit_fill(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        cache = sim.CacheHierarchy(p)
        address = 0xA000
        line = address // cache.line
        levels = (
            ("L1", cache.l1, p.l1_lat),
            ("L2", cache.l2, p.l2_lat),
            ("L3", cache.l3, p.l3_lat),
            ("L4", cache.l4, p.l4_lat),
        )
        for level, target, expected_latency in levels:
            with self.subTest(level=level):
                target.insert(line)
                latency, observed = cache.probe(address)
                self.assertEqual((latency, observed), (expected_latency, level))
                # Probe is lookup-only: it must not allocate in a nearer cache.
                self.assertFalse(cache.l1.lookup(line) if level != "L1" else False)
                target.lines.clear()

        latency, observed = cache.probe(address)
        self.assertEqual((latency, observed), (p.dram_lat, "DRAM"))

    def test_l1_is_private_but_l2_is_shared_by_pair(self):
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        self.assertEqual((p.l1_kb, p.l2_kb, p.l3_kb, p.l4_kb),
                         (1024, 2048, 8192, 65536))
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



class ReferenceCacheTopologyTests(unittest.TestCase):
    def test_amd_and_intel_xeon_share_llc_but_keep_private_l2(self):
        for key in ("amd_9950x3d2", "intel_xeon_698x"):
            p = sim.profile_from_dict(sim.PROFILES[key])
            caches = sim.build_cache_hierarchies(p, 8)
            with self.subTest(profile=key):
                self.assertIsNot(caches[0].l1, caches[1].l1)
                self.assertIsNot(caches[0].l2, caches[1].l2)
                self.assertIs(caches[0].l3, caches[7].l3)
                caches[0].fill(0x5000, "DRAM")
                self.assertEqual(caches[7].probe(0x5000)[1], "L3")

    def test_arm_m6_profile_has_private_l2_and_shared_llc(self):
        p = sim.profile_from_dict(sim.PROFILES["apple_m6"])
        caches = sim.build_cache_hierarchies(p, 12)
        self.assertIsNot(caches[0].l2, caches[1].l2)
        self.assertIs(caches[0].l3, caches[11].l3)
        caches[0].fill(0x6000, "DRAM")
        self.assertEqual(caches[1].probe(0x6000)[1], "L3")


class WorkspaceCodeSlotModelTests(unittest.TestCase):
    def test_tw2_enabled_hits_local_store_and_preserves_work(self):
        workloads = {"hot": [sim.Op(i, "LOAD", address=(i % 32)*64, width=64,
                                     label="TW: hot") for i in range(256)]}
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(workloads["hot"], 8)
        full = sim.simulate_multicore_streams(shards, p, 32, {"task_workspace": True, "code_slots": True})
        off = sim.simulate_multicore_streams(shards, p, 32, {"task_workspace": False, "code_slots": True})
        self.assertEqual(sum(len(x) for x in shards), 256)
        self.assertEqual(sum(x["spm"]["accesses"] for x in full["cores"]), 256)
        self.assertEqual(sum(x["spm"]["fallback_bytes"] for x in off["cores"]), 256*64)

    def test_tw2_capacity_overflow_falls_back_without_dropping_accesses(self):
        ops = [sim.Op(i, "LOAD", address=(i % 256)*64, width=64,
                      label="TW: capacity") for i in range(512)]
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(ops, 8)
        result = sim.simulate_multicore_streams(shards, p, 32, {"task_workspace": True, "code_slots": True})
        counters = [x["spm"] for x in result["cores"]]
        self.assertEqual(sum(x["spm"]["accesses"] for x in result["cores"]), 256)
        self.assertEqual(sum(x["overflow"] for x in counters), 256)
        self.assertEqual(sum(x["fallback_bytes"] for x in counters), 256*64)

    def test_cs_and_conventional_fetch_paths_both_retire_same_work(self):
        ops = [sim.Op(i, "INT", command_address=(i % 2048)*8) for i in range(1024)]
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(ops, 8)
        p0 = sim.simulate_multicore_streams(shards, p, 32, {"task_workspace": True, "code_slots": True})
        conventional = sim.simulate_multicore_streams(shards, p, 32, {"task_workspace": True, "code_slots": False})
        self.assertEqual(sum(x["retired"] for x in p0["cores"]), 1024)
        self.assertEqual(sum(x["retired"] for x in conventional["cores"]), 1024)
        p0_wait = sum(x["fetch"].wait_cycles for x in p0["cores"])
        conventional_wait = sum(x["fetch"].wait_cycles for x in conventional["cores"])
        self.assertGreater(p0_wait, 0)
        self.assertGreater(conventional_wait, 0)

    def test_cs_capacity_and_refill_parameters_are_explicit(self):
        p0 = sim.CommandFetchModel(True)
        conventional = sim.CommandFetchModel(False)
        self.assertEqual(p0.capacity_bytes, 16384)
        self.assertEqual(p0.p0_buffer_bytes, 2048)
        self.assertEqual(conventional.lines.capacity, 32768 // 64)
        self.assertEqual((p0.refill_latency, conventional.refill_latency), (48, 8))
    
    def test_tw2_reduces_dependent_hot_chain_latency(self):
        ops = []
        previous = None
        for i in range(256):
            previous = sim.add_op(ops, "LOAD", () if previous is None else (previous,),
                                  address=(i % 64)*64, width=64, label="TW: dependent")
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(ops, 8)
        on = sim.simulate_multicore_streams(shards, p, 32, {"task_workspace": True, "code_slots": True})
        off = sim.simulate_multicore_streams(shards, p, 32, {"task_workspace": False, "code_slots": True})
        self.assertLess(on["cycles"], off["cycles"])
        self.assertEqual(sum(x["retired"] for x in on["cores"]), 256)
        self.assertEqual(sum(x["retired"] for x in off["cores"]), 256)

    def test_conventional_i_cache_prefetches_multiple_lines(self):
        fetch = sim.CommandFetchModel(False)
        self.assertFalse(fetch.can_fetch(0, 0))
        self.assertEqual(len(fetch.pending), 16)
        fetch.complete(8)
        self.assertTrue(fetch.can_fetch(0, 8))
        self.assertTrue(fetch.lines.lookup(1))
        self.assertEqual(fetch.refill_bytes, 17*64)

    def test_tw0_ping_pong_prefetches_next_2k_page(self):
        fetch = sim.CommandFetchModel(True)
        self.assertFalse(fetch.can_fetch(0, 0))
        fetch.complete(48)
        self.assertTrue(fetch.can_fetch(0, 48))
        self.assertEqual(fetch.p0_buffers[0], 0)
        self.assertEqual(fetch.p0_pending, (1, 96, 1))
        self.assertFalse(fetch.can_fetch(2048, 49))
        fetch.complete(96)
        self.assertTrue(fetch.can_fetch(2048, 96))
        self.assertEqual(fetch.p0_buffers, [0, 1])
        self.assertEqual(fetch.p0_pending, (2, 144, 0))
        self.assertEqual(fetch.prefetches, 3)

    def test_nonsequential_branch_redirect_can_reuse_active_bank_safely(self):
        fetch = sim.CommandFetchModel(True)
        self.assertFalse(fetch.can_fetch(0, 0))
        fetch.complete(48)
        self.assertTrue(fetch.can_fetch(0, 48))
        self.assertFalse(fetch.can_fetch(2048, 49))
        fetch.complete(96)
        self.assertTrue(fetch.can_fetch(2048, 96))
        fetch.complete(144)  # sequential prefetch of logical page 2
        # A branch target to page 3 reuses the currently active B bank.
        self.assertFalse(fetch.can_fetch(6144, 144, sequential=False))
        self.assertEqual(fetch.p0_pending, (3, 192, 1))
        fetch.complete(192)
        self.assertTrue(fetch.can_fetch(6144, 192))
        self.assertEqual(fetch.active_block, 3)

    def test_code_slots_and_execution_buffer_have_expected_capacity(self):
        p0 = sim.CommandFetchModel(True)
        conventional = sim.CommandFetchModel(False)
        self.assertEqual(p0.capacity_bytes, 16 * 1024)
        self.assertEqual(p0.capacity_bytes // p0.p0_buffer_bytes, 8)
        self.assertEqual(p0.p0_buffer_bytes, 2 * 1024)
        self.assertEqual(len(p0.p0_buffers), 2)
        self.assertEqual(conventional.capacity_bytes, 32 * 1024)
        self.assertEqual(conventional.lines.capacity, 512)

    def test_partition_builds_local_sequential_command_streams(self):
        workload = []
        for _ in range(32):
            sim.add_op(workload, "INT")
        shards = sim.partition_dependency_components(workload, 8)
        for shard in shards:
            self.assertEqual([op.command_address for op in shard],
                             [i*8 for i in range(len(shard))])

class CrossArchitectureComparisonTests(unittest.TestCase):
    def test_all_architectures_retire_the_same_logical_work_on_eight_cores(self):
        workloads = {
            "same_algorithm": [
                sim.Op(0, "LOAD", address=0x1000, width=64),
                sim.Op(1, "INT", deps=(0,)),
                sim.Op(2, "FP", deps=(1,)),
                sim.Op(3, "STORE", deps=(2,), address=0x2000, width=64),
                sim.Op(4, "BR", deps=(3,)),
                sim.Op(5, "INT"),
                sim.Op(6, "VEC"),
                sim.Op(7, "ATOM"),
            ]
        }
        results = {}
        expected_cores = {"amd_9950x3d2": 16, "intel_xeon_698x": 86,
                          "apple_m6": 12, "nexus_balanced_128": 8}
        for key, core_count in expected_cores.items():
            results[key] = sim.simulate_cpu(workloads, sim.PROFILES[key])
            self.assertEqual(results[key]["cores_configured"], core_count)
            if key == "nexus_balanced_128":
                arch = results[key]["register_architecture"]
                self.assertEqual(arch["selector_bits"], 5)
                self.assertEqual(arch["total_physical_bytes"], 1792)
                self.assertEqual({bank["count"] for bank in
                                  (arch["RA"], arch["FA"], arch["DA"], arch["MA"])}, {32})
            self.assertEqual(results[key]["kernels"]["same_algorithm"]["ops"], 8)
            if key != "nexus_balanced_128":
                self.assertEqual(results[key]["kernels"]["same_algorithm"]["codeflow_counters"]["mode"],
                                 "conventional I-cache")
                self.assertGreater(results[key]["kernels"]["same_algorithm"]["codeflow_counters"]["refills"], 0)
        self.assertEqual({r["total_ops"] for r in results.values()}, {8})

    def test_cs_starvation_stream_is_sequential_64kib_code(self):
        workload = sim.build_composite_workload(scale=1)["cs_starvation"]
        self.assertEqual(len(workload), 8192)
        self.assertEqual(workload[0].command_address, 0)
        self.assertEqual(workload[-1].command_address, (8192 - 1) * 8)
        self.assertTrue(all(workload[i].command_address + 8 == workload[i+1].command_address
                            for i in range(len(workload)-1)))

    def test_cs_starvation_partition_keeps_sequential_local_code_addresses(self):
        workload = sim.build_composite_workload(scale=1)["cs_starvation"]
        shards = sim.partition_dependency_components(workload, 1)
        addresses = [op.command_address for op in shards[0]]
        self.assertEqual(len(addresses), 8192)
        self.assertEqual(addresses[0], 0)
        self.assertEqual(addresses[-1], 8191*8)
        self.assertTrue(all(addresses[i] + 8 == addresses[i+1]
                            for i in range(len(addresses)-1)))

    def test_cs_capacity_is_configurable_and_sweep_preserves_work(self):
        workloads = {"cs_starvation": [sim.Op(i, "INT", command_address=i*8)
                                       for i in range(2048)]}
        sweep = sim.run_p0_capacity_sweep(workloads, sim.PROFILES["nexus_balanced_128"])
        self.assertEqual(set(sweep["results"]), {"4", "8", "16", "32", "64"})
        self.assertEqual({r["total_ops"] for r in sweep["results"].values()}, {2048})
        self.assertEqual({r["kernels"]["cs_starvation"]["ops"]
                          for r in sweep["results"].values()}, {2048})
        self.assertGreater(len({r["total_cycles"] for r in sweep["results"].values()}), 1)
        misses = [sweep["results"][k]["kernels"]["cs_starvation"]["code_slots"]["pool_misses"]
                  for k in ("4", "8", "16", "32", "64")]
        self.assertTrue(all(misses[i] >= misses[i+1] for i in range(len(misses)-1)))
        self.assertGreater(misses[0], misses[-1])

    def test_fetch_latency_sweep_preserves_same_command_workload(self):
        workloads = {"cs_starvation": [
            sim.Op(i, "INT", label="P0 starvation", command_address=(i % 2048)*8)
            for i in range(128)
        ]}
        sweep = sim.run_fetch_latency_sweep(workloads)
        self.assertEqual(sweep["operations_per_run"], 128)
        self.assertEqual(set(sweep["results"]), {
            "amd_9950x3d2", "intel_xeon_698x", "apple_m6",
            "nexus_conventional", "nexus_p0",
        })
        self.assertEqual(set(sweep["results"]["nexus_conventional"]), {"8", "16", "24", "32"})
        self.assertEqual(set(sweep["results"]["nexus_p0"]), {"32", "34", "48", "64", "96"})
        self.assertTrue(all(row["ops"] == 128
                            for group in sweep["results"].values()
                            for row in group.values()))


class FourWayAblationTests(unittest.TestCase):
    def test_four_profiles_preserve_operation_count_and_report_interaction(self):
        ops = [sim.Op(i, "LOAD", address=(i % 8)*64, width=64,
                      label="TW: ablation") for i in range(64)]
        result = sim.run_nexus_ablation({"small_spm_kernel": ops},
                                        sim.PROFILES["nexus_balanced_128"])
        self.assertEqual(set(result["variants"]), {"N-FULL", "N-NO-TW", "N-NO-CS", "N-BASE"})
        row = result["kernels"]["small_spm_kernel"]
        self.assertTrue(row["ops_preserved"])
        self.assertEqual(row["ops"], 64)
        self.assertIn("interaction_cycles", row)
        self.assertEqual({v["total_ops"] for v in result["variants"].values()}, {64})



class BranchPredictionTests(unittest.TestCase):
    def test_compact_predictor_reduces_predictable_control_branch_misses(self):
        ops = [sim.Op(i, "BR", label="control branch") for i in range(1000)]
        no_predictor = sum(sim.branch_mispredict(op, i + 1, "none") for i, op in enumerate(ops))
        compact = sum(sim.branch_mispredict(op, i + 1, "small_2bit") for i, op in enumerate(ops))
        self.assertLess(compact, no_predictor)

    def test_unpredictable_branch_stream_does_not_get_artificial_predictor_gain(self):
        ops = [sim.Op(i, "BR", label="independent branch stress") for i in range(1000)]
        no_predictor = sum(sim.branch_mispredict(op, i + 1, "none") for i, op in enumerate(ops))
        compact = sum(sim.branch_mispredict(op, i + 1, "small_2bit") for i, op in enumerate(ops))
        self.assertEqual(compact, no_predictor)

    def test_nexus_profile_selects_compact_predictor_candidate(self):
        self.assertEqual(sim.PROFILES["nexus_balanced_128"]["branch_predictor"], "small_2bit")


class VectorArithmeticWorkloadTests(unittest.TestCase):
    def test_execution_only_mode_bypasses_fetch_but_preserves_backend_work(self):
        workload = {"vec_add": [sim.Op(i, "VEC_ADD", exec_width_bits=512)
                                for i in range(32)]}
        normal = sim.simulate_cpu(
            workload, sim.PROFILES["nexus_balanced_128"], 8,
            {"task_workspace": True, "code_slots": True, "codeflow": True},
        )
        isolated = sim.simulate_cpu(
            workload, sim.PROFILES["nexus_balanced_128"], 8,
            {"execution_only": True},
        )
        normal_row = normal["kernels"]["vec_add"]
        isolated_row = isolated["kernels"]["vec_add"]
        self.assertEqual(normal_row["ops"], isolated_row["ops"])
        self.assertGreater(normal_row["codeflow_counters"]["wait_cycles"], 0)
        self.assertEqual(isolated_row["codeflow_counters"]["wait_cycles"], 0)
        self.assertLess(isolated_row["cycles"], normal_row["cycles"])
        self.assertEqual(isolated_row["codeflow_counters"]["mode"],
                         "execution-only backend isolation")



    def test_vector_arithmetic_opcodes_share_the_vector_issue_resource(self):
        workload = {
            "vector_arithmetic": [
                sim.Op(0, "VEC_ADD", exec_width_bits=512),
                sim.Op(1, "VEC_SUB", exec_width_bits=512),
                sim.Op(2, "VEC_MUL", exec_width_bits=512),
                sim.Op(3, "VEC_FMA", exec_width_bits=512),
                sim.Op(4, "VEC_PERMUTE", exec_width_bits=512),
                sim.Op(5, "VEC_REDUCE", exec_width_bits=512),
            ]
        }
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"):
            with self.subTest(profile=key):
                result = sim.simulate_cpu(workload, sim.PROFILES[key])
                row = result["kernels"]["vector_arithmetic"]
                self.assertEqual(row["ops"], 6)
                self.assertGreater(row["cycles"], 0)
        self.assertEqual(sim.execution_resource_kind("VEC_ADD", "ME512"), "VEC")
        self.assertEqual(sim.execution_resource_kind("VEC_SUB", "ME512"), "VEC")
        self.assertEqual(sim.execution_resource_kind("VEC_MUL", "ME512"), "VEC")
        self.assertEqual(sim.execution_resource_kind("VEC_FMA", "ME512"), "VEC")
        self.assertEqual(sim.execution_resource_kind("VEC_PERMUTE", "ME512"), "VEC")
        self.assertEqual(sim.execution_resource_kind("VEC_REDUCE", "ME512"), "VEC")

    def test_vector_workload_contains_all_arithmetic_classes(self):
        workload = sim.build_composite_workload(scale=1)
        for name in ("vec_add", "vec_sub", "vec_mul", "vec_fma", "vec_permute", "vec_reduce"):
            with self.subTest(kernel=name):
                self.assertEqual(len(workload[name]), 128)
                self.assertTrue(all(op.exec_width_bits == 512 for op in workload[name]))

    def test_vector_dependency_kernels_are_serial_and_memory_free(self):
        workload = sim.build_composite_workload(scale=1)
        for name in (
            "vec_add_dependency_chain", "vec_sub_dependency_chain",
            "vec_mul_dependency_chain", "vec_fma_dependency_chain",
            "vec_permute_dependency_chain", "vec_reduce_dependency_chain",
        ):
            with self.subTest(kernel=name):
                ops = workload[name]
                self.assertEqual(len(ops), 64)
                self.assertEqual(ops[0].deps, ())
                self.assertTrue(all(ops[i].deps == (i - 1,) for i in range(1, len(ops))))
                self.assertTrue(all(op.exec_width_bits == 512 for op in ops))
                self.assertTrue(all(op.kind.startswith("VEC_") for op in ops))


class ME512WorkloadTests(unittest.TestCase):
    def test_me512_workload_retires_on_all_architectures(self):
        workload = {"me512": [
            sim.Op(0, "LOAD", address=0x1000, width=64),
            sim.Op(1, "LOAD", address=0x2000, width=64),
            sim.Op(2, "ME512", deps=(0, 1), label="ME512 512-bit tile operation"),
            sim.Op(3, "STORE", deps=(2,), address=0x3000, width=64),
        ]}
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"):
            with self.subTest(profile=key):
                result = sim.simulate_cpu(workload, sim.PROFILES[key])
                self.assertEqual(result["kernels"]["me512"]["ops"], 4)
                self.assertEqual(result["kernels"]["me512"]["cycles"] > 0, True)
        self.assertIn("ME512", sim.PROFILES["nexus_balanced_128"]["units"])
        self.assertEqual(sim.PROFILES["nexus_balanced_128"]["matrix_unit"], "ME512")
        self.assertEqual(sim.PROFILES["intel_xeon_698x"]["matrix_unit"], "AMX")
        self.assertEqual(sim.PROFILES["amd_9950x3d2"]["matrix_unit"], "VEC")
        self.assertEqual(sim.PROFILES["apple_m6"]["vector_bits"], 128)
        self.assertEqual(sim.PROFILES["amd_9950x3d2"]["vector_bits"], 512)

    def test_me512_kernel_is_a_tiled_accumulate_workload_not_one_opaque_op(self):
        workload = sim.build_composite_workload(scale=1)["me512_matrix"]
        mac_ops = [op for op in workload if op.kind == "ME512"]
        loads = [op for op in workload if op.kind == "LOAD"]
        stores = [op for op in workload if op.kind == "STORE"]
        self.assertEqual(len(mac_ops), 16 * 8)
        self.assertEqual(len(loads), 16 * 8 * 2)
        self.assertEqual(len(stores), 16)
        self.assertTrue(all(op.exec_width_bits == 512 for op in mac_ops))
        self.assertTrue(all(len(op.deps) == 3 for op in mac_ops if op.deps and
                            any(workload[d].kind == "ME512" for d in op.deps)))

    def test_me512_operand_resident_throughput_and_dependency_kernels(self):
        workloads = sim.build_composite_workload(scale=1)
        independent = workloads["me512_independent_throughput"]
        chain = workloads["me512_dependency_chain"]
        self.assertEqual(len(independent), 128)
        self.assertTrue(all(op.kind == "ME512" and not op.deps for op in independent))
        self.assertEqual(len(chain), 128)
        self.assertEqual(chain[0].deps, ())
        self.assertTrue(all(chain[i].deps == (i - 1,) for i in range(1, len(chain))))
        self.assertTrue(all(op.exec_width_bits == 512 for op in independent + chain))
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"):
            for name in ("me512_independent_throughput", "me512_dependency_chain"):
                with self.subTest(profile=key, kernel=name):
                    result = sim.simulate_cpu({name: workloads[name]}, sim.PROFILES[key], 8,
                                              {"execution_only": True})
                    self.assertEqual(result["kernels"][name]["ops"], 128)
                    self.assertGreater(result["kernels"][name]["cycles"], 0)

    def test_mixed_vec_me512_and_memory_stream_preserves_work_and_overlaps(self):
        ops = sim.build_composite_workload(scale=1)["vec_me512_memory_overlap"]
        self.assertEqual(len(ops), 128 * 3 + 64)
        self.assertEqual(sum(op.kind == "VEC_ADD" for op in ops), 128)
        self.assertEqual(sum(op.kind == "ME512" for op in ops), 128)
        self.assertEqual(sum(op.kind == "LOAD" for op in ops), 128)
        self.assertEqual(sum(op.kind == "STORE" for op in ops), 64)
        by_seq = {op.seq: op for op in ops}
        for op in ops:
            if op.kind in ("VEC_ADD", "ME512"):
                self.assertEqual(len(op.deps), 1)
                self.assertEqual(by_seq[op.deps[0]].kind, "LOAD")
            elif op.kind == "STORE":
                self.assertEqual(len(op.deps), 2)
                self.assertEqual(
                    {by_seq[dep].kind for dep in op.deps},
                    {"VEC_ADD", "ME512"},
                )
        result = sim.simulate_cpu(
            {"vec_me512_memory_overlap": ops},
            sim.PROFILES["nexus_balanced_128"], 8,
            {"execution_only": True},
        )["kernels"]["vec_me512_memory_overlap"]
        self.assertEqual(result["ops"], len(ops))
        self.assertGreater(result["issue_span_cycles"], 0)
        self.assertGreater(result["cache_accesses"]["DRAM"], 0)
        self.assertGreater(result["stall_counters"]["memory_latency_exposure_cycles"], 0)

        # Same logical kernel, but its data set is already resident before
        # timing starts. The eight-core working set is homed in shared L4;
        # lower levels may be populated naturally as demand accesses complete.
        warm_addresses = sorted({
            op.address for op in ops if op.kind in ("LOAD", "STORE", "ATOM")
        })
        warm = sim.simulate_cpu(
            {"vec_me512_memory_overlap": ops},
            sim.PROFILES["nexus_balanced_128"], 8,
            {"execution_only": True,
             "cache_prefill_addresses": warm_addresses,
             "cache_prefill_level": "L4"},
        )["kernels"]["vec_me512_memory_overlap"]
        self.assertEqual(warm["ops"], len(ops))
        self.assertEqual(
            sum(warm["cache_accesses"][level]
                for level in ("L1", "L2", "L3", "L4", "DRAM")),
            192,
        )
        self.assertEqual(warm["cache_accesses"]["DRAM"], 0)
        self.assertGreater(warm["cache_accesses"]["L4"], 0)

    def test_me512_tiled_workload_retires_on_all_architectures(self):
        workload = {"me512_matrix": sim.build_composite_workload(scale=1)["me512_matrix"]}
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"):
            with self.subTest(profile=key):
                result = sim.simulate_cpu(workload, sim.PROFILES[key])
                row = result["kernels"]["me512_matrix"]
                self.assertEqual(row["ops"], len(workload["me512_matrix"]))
                self.assertGreater(row["cycles"], 0)


class BranchSweepIntegrationTests(unittest.TestCase):
    def test_branch_sweep_preserves_work_and_separates_predictable_from_random(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_branch_predictor_sweep(workloads, sim.PROFILES["nexus_balanced_128"])
        for row in result["kernels"].values():
            self.assertTrue(row["ops_preserved"])
        self.assertLess(
            result["kernels"]["scalar_control"]["mispredicts_compact_predictor"],
            result["kernels"]["scalar_control"]["mispredicts_predictor_off"],
        )
        self.assertEqual(
            result["kernels"]["branch_stress"]["mispredicts_compact_predictor"],
            result["kernels"]["branch_stress"]["mispredicts_predictor_off"],
        )



class AtomicWorkloadTests(unittest.TestCase):
    def test_atomic_operations_use_memory_path_and_preserve_work(self):
        ops = [sim.Op(i, "ATOM", address=0x9000000 + (i % 4)*8, width=8,
                      label="atomic contention") for i in range(128)]
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"):
            with self.subTest(profile=key):
                result = sim.simulate_cpu({"atomic": ops}, sim.PROFILES[key])
                row = result["kernels"]["atomic"]
                self.assertEqual(row["ops"], 128)
                self.assertEqual(sum(row["cache_accesses"].values()), 128)


class IRQWorkloadTests(unittest.TestCase):
    def test_irq_exception_service_proxy_retires_on_all_architectures(self):
        ops = [
            sim.Op(0, "INT"),
            sim.Op(1, "IRQ", deps=(0,), label="IRQ/exception entry service"),
            sim.Op(2, "CTX", deps=(1,), label="interrupt context frame"),
            sim.Op(3, "INT", deps=(2,)),
        ]
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"):
            with self.subTest(profile=key):
                result = sim.simulate_cpu({"irq": ops}, sim.PROFILES[key])
                self.assertEqual(result["kernels"]["irq"]["ops"], 4)
        self.assertIn("IRQ", sim.PROFILES["nexus_balanced_128"]["units"])


class CodeFlowMetadataTests(unittest.TestCase):
    def test_full_pages_auto_continue_and_partial_final_uses_px_end(self):
        pages = [
            {"logical_page_id": 0, "valid_bytes": 2048},
            {"logical_page_id": 1, "valid_bytes": 2048},
            {"logical_page_id": 2, "valid_bytes": 704, "marker": "CF_END"},
        ]
        self.assertTrue(sim.validate_px_page_descriptors(pages))

    def test_exact_full_final_page_uses_region_end_metadata_not_px_end(self):
        pages = [
            {"logical_page_id": 0, "valid_bytes": 2048, "stream_end": True},
        ]
        self.assertTrue(sim.validate_px_page_descriptors(pages))
        fetch = sim.CommandFetchModel(True, page_descriptors={0: pages[0]})
        self.assertFalse(fetch.can_fetch(0, 0))
        fetch.complete(48)
        self.assertTrue(fetch.can_fetch(0, 48))
        self.assertIsNone(fetch.p0_pending)

    def test_partial_intermediate_page_uses_px_next_without_instruction_slot(self):
        pages = [
            {"logical_page_id": 0, "valid_bytes": 1536, "marker": "CF_NEXT",
             "next_logical_page_id": 1},
            {"logical_page_id": 1, "valid_bytes": 512, "marker": "CF_END"},
        ]
        self.assertTrue(sim.validate_px_page_descriptors(pages))
        ops = [sim.Op(0, "INT"), sim.Op(1, "INT")]
        self.assertEqual(len(ops), 2)

    def test_eb_ping_pong_uses_codeflow_next_and_stops_prefetch_at_px_end(self):
        fetch = sim.CommandFetchModel(True, page_descriptors={
            0: {"valid_bytes": 1024, "marker": "CF_NEXT", "next_logical_page_id": 1},
            1: {"valid_bytes": 512, "marker": "CF_END"},
        })
        self.assertFalse(fetch.can_fetch(0, 0))
        fetch.complete(48)
        self.assertTrue(fetch.can_fetch(0, 48))
        self.assertEqual(fetch.p0_pending, (1, 96, 1))
        self.assertFalse(fetch.can_fetch(2048, 49))
        fetch.complete(96)
        self.assertTrue(fetch.can_fetch(2048, 96))
        self.assertIsNone(fetch.p0_pending)  # CF_END suppresses next-page prefetch.
        with self.assertRaises(ValueError):
            fetch.can_fetch(2048 + 512, 97)  # No padding fetch past valid_bytes.
        with self.assertRaises(ValueError):
            fetch.can_fetch(4096, 97)  # CF_END cannot continue sequentially.

    def test_partial_page_without_marker_is_rejected(self):
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1024},
            ])

    def test_codeflow_end_cannot_have_a_following_page(self):
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1024, "marker": "CF_END"},
                {"logical_page_id": 1, "valid_bytes": 8, "marker": "CF_END"},
            ])

    def test_codeflow_next_requires_valid_next_page_and_alignment(self):
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1024, "marker": "CF_NEXT",
                 "next_logical_page_id": 2},
                {"logical_page_id": 1, "valid_bytes": 8, "marker": "CF_END"},
            ])
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1025, "marker": "CF_END"},
            ])

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


class IntegratedCodeFlowTests(unittest.TestCase):
    def test_c0_miss_waits_for_app_ram_and_two_transfer_stages(self):
        fetch = sim.CommandFetchModel(True, codeflow_enabled=True)
        self.assertFalse(fetch.can_fetch(0, 0))
        # 2 KiB / 8-byte lane = 256 beats; 40-cycle first beat + 255 intervals + final beat.
        app_cycles = 40 + 255 * 1 + 1
        ready = 48 + app_cycles + 128 + 128
        fetch.complete(ready - 1)
        self.assertFalse(fetch.can_fetch(0, ready - 1))
        fetch.complete(ready)
        self.assertTrue(fetch.can_fetch(0, ready))
        self.assertEqual(fetch.app_beats, 512)  # requested page plus one-page lookahead
        self.assertEqual(fetch.app_bytes, 4096)  # cold page + lookahead
        self.assertEqual(fetch.c0_misses, 2)  # cold page + next-page lookahead
        self.assertEqual(fetch.code_slot_cycles, 256)  # demand + lookahead
        self.assertEqual(fetch.code_stream_cycles, 256)  # demand + lookahead

    def test_codeflow_beat_interval_changes_ready_cycle(self):
        ready_cycles = []
        for interval in (1, 4):
            fetch = sim.CommandFetchModel(True, codeflow_enabled=True, app_beat_interval=interval)
            fetch.can_fetch(0, 0)
            ready = 48 + 40 + 255 * interval + 1 + 128 + 128
            fetch.complete(ready)
            self.assertTrue(fetch.can_fetch(0, ready))
            ready_cycles.append(ready)
        self.assertEqual(ready_cycles, [600, 1365])

    def test_nexus_execution_report_exposes_codeflow_stage_counters(self):
        result = sim.simulate_cpu({"code": [sim.Op(0, "INT", command_address=0)]},
                                  sim.PROFILES["nexus_balanced_128"], 1, {"codeflow": True})
        counters = result["kernels"]["code"]["codeflow_counters"]
        for key in ("code_cache_misses", "app_ram_beats", "app_ram_bytes",
                    "app_source_cycles", "code_slot_transfer_cycles",
                    "code_stream_transfer_cycles"):
            self.assertIn(key, counters)
        self.assertEqual(counters["app_ram_beats"], 512)  # demand page + lookahead
        self.assertEqual(counters["app_ram_bytes"], 4096)  # demand page + lookahead
        # Integrated App RAM service overlaps the later C0->CS->EB stages;
        # retain a lower-bound check without assuming serialized stage latency.
        self.assertGreater(result["kernels"]["code"]["cycles"], 300)



class TestNexusMemoryBandwidthRevision(unittest.TestCase):
    def test_nexus_has_double_reference_dram_bandwidth(self):
        self.assertEqual(sim.PROFILES["nexus_balanced_128"]["dram_bytes_per_cycle"], 64)
        for key, expected in (("amd_9950x3d2", 21), ("intel_xeon_698x", 160), ("apple_m6", 48)):
            self.assertEqual(sim.PROFILES[key]["dram_bytes_per_cycle"], expected)



class MixedWidthExecutionTopologyTests(unittest.TestCase):
    def test_nexus_profile_exposes_two_128_capable_int_pairs_and_six_fp64_lanes(self):
        profile = sim.PROFILES["nexus_balanced_128"]
        self.assertEqual(profile["units"]["INT"], 8)
        self.assertEqual(profile["units"]["FP"], 6)
        self.assertEqual(profile["execution_topology"]["INT128_PAIRS"], [[0, 1], [2, 3]])

    def test_partition_preserves_128_bit_operation_width(self):
        ops = [sim.Op(0, "INT", exec_width_bits=128)]
        shards = sim.partition_dependency_components(ops, 1)
        self.assertEqual(shards[0][0].exec_width_bits, 128)

    def test_128_bit_int_reserves_two_64_bit_lanes(self):
        profile = dict(sim.PROFILES["nexus_balanced_128"])
        profile["units"] = {**profile["units"], "INT": 2, "FP": 2}
        profile["execution_topology"] = {"INT128_PAIRS": [[0, 1]]}
        workloads = {
            "mixed": [
                sim.Op(0, "INT", exec_width_bits=128),
                sim.Op(1, "INT", exec_width_bits=64),
                sim.Op(2, "INT", exec_width_bits=64),
            ]
        }
        result = sim.simulate_cpu(workloads, profile, 1)
        self.assertEqual(result["kernels"]["mixed"]["ops"], 3)
        # The 128-bit op occupies both lanes; neither 64-bit op can issue beside it.
        self.assertGreaterEqual(
            result["kernels"]["mixed"]["stall_counters"]["execution_unit_blocked_op_cycles"],
            2,
        )

    def test_execution_sweep_preserves_work_and_reports_both_widths(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_execution_topology_sweep(workloads, sim.PROFILES["nexus_balanced_128"])
        self.assertEqual(result["experiment"], "NEXSUS mixed-width INT and six-lane FP execution topology")
        for name in ("integer_throughput", "integer128_throughput", "fp_throughput"):
            self.assertTrue(result["kernels"][name]["ops_preserved"], name)
            self.assertGreater(result["kernels"][name]["ops"], 0)
        self.assertEqual(result["kernels"]["integer128_throughput"]["ops"], 256)


class ExecutionResourceCountSweepTests(unittest.TestCase):
    def test_resource_sweep_preserves_work_and_reports_all_unit_counts(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_execution_resource_count_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            int_counts=(2, 4, 8), fp_counts=(2, 4, 6),
        )
        self.assertEqual(len(result["results"]), 9)
        for variant in result["results"].values():
            self.assertEqual(variant["total_ops"], sum(result["same_logical_workload"].values()))
            for name, row in variant["kernels"].items():
                self.assertTrue(row["ops_preserved"], name)

    def test_more_int_lanes_do_not_reduce_independent_int_throughput(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_execution_resource_count_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            int_counts=(2, 4, 6, 8), fp_counts=(2,),
        )
        cycles = [result["results"][f"INT{count}_FP2"]["kernels"]["integer_throughput"]["cycles"]
                  for count in (2, 4, 6, 8)]
        self.assertTrue(all(cycles[i] >= cycles[i+1] for i in range(len(cycles)-1)), cycles)

    def test_more_fp_lanes_do_not_reduce_independent_fp_throughput(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_execution_resource_count_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            int_counts=(2,), fp_counts=(2, 4, 6, 8),
        )
        cycles = [result["results"][f"INT2_FP{count}"]["kernels"]["fp_throughput"]["cycles"]
                  for count in (2, 4, 6, 8)]
        self.assertTrue(all(cycles[i] >= cycles[i+1] for i in range(len(cycles)-1)), cycles)


class FMAResourceSweepTests(unittest.TestCase):
    def test_fma_sweep_preserves_work_for_all_fp_topologies(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_fma_resource_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            fp_counts=(6, 8), fma_counts=(2, 4),
        )
        self.assertEqual(set(result["results"]), {
            "FP6_FMA2", "FP6_FMA4", "FP8_FMA2", "FP8_FMA4",
        })
        for variant in result["results"].values():
            for name, row in variant["kernels"].items():
                self.assertTrue(row["ops_preserved"], name)
        self.assertEqual(result["results"]["FP6_FMA2"]["kernels"]["fma_throughput"]["ops"], 512)

    def test_more_fma_lanes_do_not_reduce_fma_throughput(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_fma_resource_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            fp_counts=(6,), fma_counts=(2, 4),
        )
        two = result["results"]["FP6_FMA2"]["kernels"]["fma_throughput"]["cycles"]
        four = result["results"]["FP6_FMA4"]["kernels"]["fma_throughput"]["cycles"]
        self.assertGreaterEqual(two, four)

    def test_fma_dependency_chain_preserves_work_and_latency_result(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_fma_resource_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            fp_counts=(6,), fma_counts=(2, 4),
        )
        two = result["results"]["FP6_FMA2"]["kernels"]["fma_dependency_chain"]
        four = result["results"]["FP6_FMA4"]["kernels"]["fma_dependency_chain"]
        self.assertEqual(two["ops"], 256)
        self.assertEqual(four["ops"], 256)
        self.assertTrue(two["ops_preserved"])
        self.assertTrue(four["ops_preserved"])
        self.assertGreater(two["cycles"], 0)
        self.assertGreater(four["cycles"], 0)

    def test_mixed_fp_fma_stream_preserves_work_and_reports_contention(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_fma_resource_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            fp_counts=(6,), fma_counts=(2, 4),
        )
        two = result["results"]["FP6_FMA2"]["kernels"]["fp_fma_mixed"]
        four = result["results"]["FP6_FMA4"]["kernels"]["fp_fma_mixed"]
        self.assertEqual(two["ops"], 512)
        self.assertEqual(four["ops"], 512)
        self.assertTrue(two["ops_preserved"])
        self.assertTrue(four["ops_preserved"])
        self.assertGreater(two["cycles"], 0)
        self.assertGreater(four["cycles"], 0)
        # Mixed throughput is recorded independently of isolated FP/FMA tests.
        self.assertIn("execution_unit_blocked_op_cycles", two)
        self.assertIn("execution_unit_blocked_op_cycles", four)

    def test_fma_lanes_are_subset_of_fp_lanes(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_fma_resource_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            fp_counts=(6,), fma_counts=(2, 4),
        )
        for row in result["results"].values():
            self.assertLessEqual(row["fma_lanes_per_core"], row["fp64_lanes_per_core"])

    def test_fma_latency_changes_dependency_chain_not_issue_throughput(self):
        workloads = sim.build_composite_workload(scale=1)
        result = sim.run_fma_latency_sweep(
            workloads, sim.PROFILES["nexus_balanced_128"],
            latencies=(3, 4, 5, 6), fp_count=6, fma_count=4,
        )
        self.assertEqual(set(result["results"]), {"3", "4", "5", "6"})
        chain_cycles = []
        fma_issue_spans = []
        fp_issue_spans = []
        fp_cycles = []
        for row in result["results"].values():
            self.assertEqual(row["kernels"]["fma_dependency_chain"]["ops"], 256)
            self.assertEqual(row["kernels"]["fma_throughput"]["ops"], 512)
            self.assertEqual(row["kernels"]["fp_throughput"]["ops"], 512)
            self.assertTrue(all(x["ops_preserved"] for x in row["kernels"].values()))
            chain_cycles.append(row["kernels"]["fma_dependency_chain"]["cycles"])
            fma_issue_spans.append(row["kernels"]["fma_throughput"]["issue_span_cycles"])
            fp_issue_spans.append(row["kernels"]["fp_throughput"]["issue_span_cycles"])
            fp_cycles.append(row["kernels"]["fp_throughput"]["cycles"])
        self.assertEqual(chain_cycles, sorted(chain_cycles))
        self.assertEqual(len(set(chain_cycles)), 4)
        # Total completion includes the final result-latency drain. Compare
        # issue spans to verify that independent FMA throughput is unchanged.
        self.assertEqual(len(set(fma_issue_spans)), 1)
        self.assertEqual(len(set(fp_issue_spans)), 1)
        self.assertEqual(len(set(fp_cycles)), 1)



class AppRamControllerTests(unittest.TestCase):
    def test_app_ram_controller_has_independent_bounded_queue(self):
        ctrl = sim.AppRamController(first_beat_latency=10, max_outstanding=1)
        first = ctrl.reserve_batch(0, [
            {"id": "code0", "core": 0, "address": 0x1000, "bytes": 8},
        ])
        second = ctrl.reserve_batch(0, [
            {"id": "code1", "core": 1, "address": 0x2000, "bytes": 8},
        ])
        self.assertTrue(first["code0"]["accepted"])
        self.assertFalse(second["code1"]["accepted"])
        self.assertEqual(second["code1"]["reason"], "queue_full")
        self.assertEqual((ctrl.accepted, ctrl.rejected_queue_full), (1, 1))

    def test_app_ram_independent_banks_do_not_conflict(self):
        ctrl = sim.AppRamController(bytes_per_cycle=64, first_beat_latency=4)
        result = ctrl.reserve_batch(0, [
            {"id": "bank0", "core": 0, "address": 0x0000, "bytes": 8},
            {"id": "bank1", "core": 1, "address": 0x0008, "bytes": 8},
        ])
        self.assertTrue(result["bank0"]["accepted"])
        self.assertTrue(result["bank1"]["accepted"])
        self.assertEqual(ctrl.bank_conflicts, 0)
        self.assertEqual(result["bank0"]["ready_cycle"], result["bank1"]["ready_cycle"])

    def test_app_ram_same_bank_conflict_is_local(self):
        ctrl = sim.AppRamController(bytes_per_cycle=64, first_beat_latency=4)
        result = ctrl.reserve_batch(0, [
            {"id": "same0", "core": 0, "address": 0x0000, "bytes": 8},
            {"id": "same1", "core": 1, "address": 0x0040, "bytes": 8},
        ])
        self.assertTrue(result["same0"]["accepted"])
        self.assertTrue(result["same1"]["accepted"])
        self.assertGreaterEqual(ctrl.bank_conflicts, 1)
        self.assertGreater(result["same1"]["ready_cycle"], result["same0"]["ready_cycle"])

    def test_app_ram_completion_releases_queue_slot(self):
        ctrl = sim.AppRamController(first_beat_latency=5, max_outstanding=1)
        first = ctrl.reserve_batch(0, [
            {"id": "first", "core": 0, "address": 0, "bytes": 8},
        ])
        ready = first["first"]["ready_cycle"]
        ctrl.complete(ready - 1)
        blocked = ctrl.reserve_batch(ready - 1, [
            {"id": "blocked", "core": 1, "address": 8, "bytes": 8},
        ])
        self.assertFalse(blocked["blocked"]["accepted"])
        ctrl.complete(ready)
        admitted = ctrl.reserve_batch(ready, [
            {"id": "next", "core": 1, "address": 8, "bytes": 8},
        ])
        self.assertTrue(admitted["next"]["accepted"])


class SharedAppRamIntegrationTests(unittest.TestCase):
    def test_two_cores_share_one_app_ram_queue(self):
        controller = sim.AppRamController(
            bank_count=8, bytes_per_cycle=32,
            first_beat_latency=5, max_outstanding=1,
        )
        core0 = sim.CommandFetchModel(
            True, codeflow_enabled=True, app_ram_controller=controller, core_id=0,
            app_first_beat_latency=5,
        )
        core1 = sim.CommandFetchModel(
            True, codeflow_enabled=True, app_ram_controller=controller, core_id=1,
            app_first_beat_latency=5,
        )
        self.assertFalse(core0.can_fetch(0, 0))
        self.assertFalse(core1.can_fetch(0, 0))
        self.assertEqual(controller.accepted, 1)
        self.assertEqual(controller.rejected_queue_full, 1)
        ready = core0.p0_pending[1]
        self.assertIsNotNone(core0.p0_pending)
        self.assertIsNone(core1.p0_pending)
        app_ready = controller.inflight["core0:page0"]
        self.assertLess(app_ready, ready)  # App RAM source completes before the EB page is ready.
        self.assertFalse(core1.can_fetch(0, app_ready - 1))
        self.assertIsNone(core1.p0_pending)
        self.assertFalse(core1.can_fetch(0, app_ready))
        self.assertEqual(controller.accepted, 2)
        self.assertIsNotNone(core1.p0_pending)

    def test_rejected_app_ram_request_does_not_poison_pool_residency(self):
        controller = sim.AppRamController(first_beat_latency=5, max_outstanding=1)
        blocker = controller.reserve_batch(0, [
            {"id": "blocker", "core": 1, "address": 0x4000, "bytes": 8},
        ])["blocker"]
        fetch = sim.CommandFetchModel(
            True, codeflow_enabled=True, app_ram_controller=controller,
            core_id=0, app_first_beat_latency=5,
        )
        self.assertFalse(fetch.can_fetch(0, 0))
        self.assertIsNone(fetch.p0_pending)
        self.assertNotIn(0, fetch.pool_pages)
        self.assertEqual(fetch.pool_misses, 0)
        self.assertEqual(fetch.c0_misses, 0)

        fetch.can_fetch(0, blocker["ready_cycle"])
        self.assertIsNotNone(fetch.p0_pending)
        self.assertEqual(controller.accepted, 2)
        self.assertEqual(fetch.pool_misses, 1)
        self.assertEqual(fetch.c0_misses, 1)
        self.assertEqual(fetch.app_bytes, fetch.p0_buffer_bytes)

    def test_app_ram_metrics_are_separate_from_data_ram_metrics(self):
        workload = {"code_and_data": [sim.Op(0, "INT", command_address=0)]}
        features = {"task_workspace": True, "code_slots": True, "codeflow": True,
                    "app_max_outstanding": 2}
        result = sim.simulate_cpu(workload, sim.PROFILES["nexus_balanced_128"], 2, features)
        kernel = result["kernels"]["code_and_data"]
        self.assertIsNotNone(kernel["app_ram_controller"])
        self.assertIn("memory_controller", kernel)
        self.assertEqual(kernel["app_ram_controller"]["max_outstanding"], 2)


class EightCoreArchitectureScalingTests(unittest.TestCase):
    @staticmethod
    def _workload():
        # Identical logical instruction/data trace for every architecture.
        kinds = ("LOAD", "INT", "FP", "STORE", "VEC", "INT", "LOAD", "BR")
        return [
            sim.Op(i, kinds[i % len(kinds)],
                   address=((i * 13) % 256) * 64,
                   width=8 if i % 4 else 64,
                   command_address=i * 8)
            for i in range(1024)
        ]

    def test_all_architectures_run_the_same_workload_on_eight_cores(self):
        workload = self._workload()
        expected = {
            "amd_9950x3d2": 16,
            "intel_xeon_698x": 86,
            "apple_m6": 12,
            "nexus_balanced_128": 8,
        }
        rows = {}
        for key in expected:
            profile = sim.profile_from_dict(sim.PROFILES[key])
            shards = sim.partition_dependency_components(workload, 8)
            features = ({"task_workspace": True, "code_slots": True,
                         "codeflow": True, "app_max_outstanding": 8}
                        if key == "nexus_balanced_128" else
                        {"task_workspace": False, "code_slots": False,
                         "codeflow": False})
            result = sim.simulate_multicore_streams(
                shards, profile, int(sim.PROFILES[key]["dram_bytes_per_cycle"]),
                features,
            )
            rows[key] = result
            self.assertEqual(len(result["cores"]), 8)
            self.assertEqual(sum(core["retired"] for core in result["cores"]), 1024)
            self.assertGreater(result["cycles"], 0)
            self.assertEqual(expected[key], sim.PROFILES[key]["core_count"])
        # All architectures complete exactly the same 1,024 operations.
        self.assertEqual(
            {sum(core["retired"] for core in row["cores"]) for row in rows.values()},
            {1024},
        )
        self.assertIsNotNone(rows["nexus_balanced_128"]["app_controller"])
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6"):
            self.assertIsNone(rows[key]["app_controller"])

    def test_nexus_eight_core_app_ram_queue_depth_sweep_is_lossless(self):
        workload = self._workload()
        shards = sim.partition_dependency_components(workload, 8)
        profile = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        rows = {}
        data_request_signatures = {}
        for depth in (1, 2, 4, 8, 16, 32):
            result = sim.simulate_multicore_streams(
                shards, profile, 64,
                {"task_workspace": True, "code_slots": True,
                 "codeflow": True, "app_max_outstanding": depth},
            )
            app = result["app_controller"]
            data = result["controller"]
            rows[depth] = result
            data_request_signatures[depth] = sorted(
                (event["core"], event["address"], event["width"])
                for event in data["request_events"]
            )
            self.assertEqual(len(app["request_events"]), app["accepted"])
            self.assertTrue(all(
                event["request_cycle"] <= event["ready_cycle"]
                and event["bytes"] > 0
                for event in app["request_events"]
            ), depth)
            self.assertEqual(sum(core["retired"] for core in result["cores"]), 1024)
            self.assertEqual(app["max_outstanding"], depth)
            self.assertGreaterEqual(app["accepted"], 8)
        # More queue slots must not cause lost/duplicated work or longer runtime
        # solely from queue admission; exact cycles remain model-derived.
        self.assertEqual(
            {sum(core["retired"] for core in row["cores"]) for row in rows.values()},
            {1024},
        )
        # App RAM queue depth may shift global timing, but it must not alter
        # which Data RAM misses the identical workload generates.
        self.assertEqual(
            {tuple(signature) for signature in data_request_signatures.values()},
            {tuple(data_request_signatures[1])},
        )
        self.assertGreater(rows[1]["app_controller"]["queue_rejections"], 0)
        self.assertEqual(rows[32]["app_controller"]["queue_rejections"], 0)
        for depth, result in rows.items():
            data = result["controller"]
            dram_hits = sum(core["hits"]["DRAM"] for core in result["cores"])
            self.assertEqual(len(data["request_events"]), dram_hits, depth)
            self.assertTrue(all(
                event["request_cycle"] <= event["service_complete_cycle"]
                for event in data["request_events"]
            ), depth)

    def test_app_ram_and_data_ram_controllers_progress_independently(self):
        app = sim.AppRamController(
            bank_count=4, beat_bytes=8, bytes_per_cycle=16,
            first_beat_latency=5, beat_interval=1, max_outstanding=1,
        )
        data = sim.SharedMemoryController(
            bank_count=4, beat_bytes=8, aggregate_bytes_per_cycle=16,
        )

        app_first = app.reserve_batch(0, [
            {"id": "instruction-page-0", "core": 0,
             "address": 0x1000, "bytes": 64},
        ])["instruction-page-0"]
        data_first = data.reserve_batch(0, [
            {"id": "data-load-0", "core": 0,
             "address": 0x8000, "width": 64},
        ])["data-load-0"]

        self.assertTrue(app_first["accepted"])
        self.assertIn("service_complete_cycle", data_first)
        app_ready = app_first["ready_cycle"]
        data_ready = data_first["service_complete_cycle"]
        app_bus_after_first = app.bus_next_byte
        data_bus_after_first = data.bus_next_byte

        # App RAM is full, but that must not block an independent Data RAM miss.
        app_rejected = app.reserve_batch(1, [
            {"id": "instruction-page-1", "core": 1,
             "address": 0x2000, "bytes": 64},
        ])["instruction-page-1"]
        data_second = data.reserve_batch(1, [
            {"id": "data-load-1", "core": 1,
             "address": 0x9000, "width": 64},
        ])["data-load-1"]
        self.assertFalse(app_rejected["accepted"])
        self.assertIn("service_complete_cycle", data_second)
        self.assertEqual(app.bus_next_byte, app_bus_after_first)
        self.assertEqual(app.transferred_bytes, 64)
        self.assertGreater(data.bus_next_byte, data_bus_after_first)

        # Replaying only the same Data RAM requests must produce identical
        # service reservations: App RAM traffic cannot perturb its controller.
        reference_data = sim.SharedMemoryController(
            bank_count=4, beat_bytes=8, aggregate_bytes_per_cycle=16,
        )
        reference_first = reference_data.reserve_batch(0, [
            {"id": "data-load-0", "core": 0,
             "address": 0x8000, "width": 64},
        ])
        reference_second = reference_data.reserve_batch(1, [
            {"id": "data-load-1", "core": 1,
             "address": 0x9000, "width": 64},
        ])
        self.assertEqual(data_first, reference_first["data-load-0"])
        self.assertEqual(data_second, reference_second["data-load-1"])

        # Data RAM traffic must not consume App RAM queue slots or bus capacity.
        self.assertEqual(len(app.inflight), 1)
        self.assertEqual(app.inflight["instruction-page-0"], app_ready)
        self.assertGreaterEqual(data_second["service_complete_cycle"], data_ready)
        self.assertEqual(app.rejected_queue_full, 1)

    def test_integrated_app_and_data_ram_requests_overlap_on_global_timeline(self):
        # Each core crosses a 2-KiB command-page boundary while issuing
        # independent, cache-cold data loads. Both paths must make progress
        # during at least one common global cycle.
        shards = []
        for core_id in range(8):
            shard = []
            for seq in range(260):
                is_load = (seq % 2 == 0)
                shard.append(sim.Op(
                    seq,
                    "LOAD" if is_load else "INT",
                    address=(core_id * 0x100000) + (seq * 4096),
                    width=8,
                    label="App/Data overlap",
                    command_address=seq * 8,
                ))
            shards.append(shard)

        profile = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        result = sim.simulate_multicore_streams(
            shards, profile, 64,
            {"task_workspace": True, "code_slots": True,
             "codeflow": True, "app_max_outstanding": 16},
        )

        app = result["app_controller"]
        data = result["controller"]
        self.assertEqual(sum(core["retired"] for core in result["cores"]), 8 * 260)
        self.assertGreater(app["accepted"], 8)
        self.assertGreater(app["transferred_bytes"], 0)
        self.assertGreater(data["bus_next_cycle"], 0)
        dram_hits = sum(core["hits"]["DRAM"] for core in result["cores"])
        self.assertGreater(dram_hits, 0)
        self.assertEqual(len(data["request_events"]), dram_hits)
        self.assertTrue(all(
            event["request_cycle"] <= event["service_complete_cycle"]
            and event["bank_wait"] >= 0
            and event["bus_wait"] >= 0
            and event["width"] > 0
            for event in data["request_events"]
        ))

        overlap_cycles = (
            set(app["request_cycles"]) & set(data["request_cycles"])
        )
        self.assertTrue(
            overlap_cycles,
            "App RAM instruction fetch and Data RAM misses never overlapped",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
