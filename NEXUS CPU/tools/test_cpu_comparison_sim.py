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
            "INT": 2, "FP": 2, "VEC": 2, "LOAD": 8,
            "STORE": 4, "BR": 2, "CTX": 1, "ATOM": 1, "ME512": 1, "IRQ": 1,
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
        self.assertGreater(p0_wait, 0)
        self.assertGreater(conventional_wait, 0)

    def test_p0_capacity_and_refill_parameters_are_explicit(self):
        p0 = sim.CommandFetchModel(True)
        conventional = sim.CommandFetchModel(False)
        self.assertEqual(p0.capacity_bytes, 16384)
        self.assertEqual(p0.p0_buffer_bytes, 2048)
        self.assertEqual(conventional.lines.capacity, 32768 // 64)
        self.assertEqual((p0.refill_latency, conventional.refill_latency), (48, 8))
    
    def test_spm2_reduces_dependent_hot_chain_latency(self):
        ops = []
        previous = None
        for i in range(256):
            previous = sim.add_op(ops, "LOAD", () if previous is None else (previous,),
                                  address=(i % 64)*64, width=64, label="SPM2: dependent")
        p = sim.profile_from_dict(sim.PROFILES["nexus_balanced_128"])
        shards = sim.partition_dependency_components(ops, 8)
        on = sim.simulate_multicore_streams(shards, p, 32, {"spm": True, "p0": True})
        off = sim.simulate_multicore_streams(shards, p, 32, {"spm": False, "p0": True})
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

    def test_spm0_ping_pong_prefetches_next_2k_page(self):
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

    def test_px_pool_has_eight_2k_slots_and_spm0_has_two_2k_banks(self):
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
                self.assertEqual(results[key]["kernels"]["same_algorithm"]["p0_counters"]["mode"],
                                 "conventional I-cache")
                self.assertGreater(results[key]["kernels"]["same_algorithm"]["p0_counters"]["refills"], 0)
        self.assertEqual({r["total_ops"] for r in results.values()}, {8})

    def test_p0_capacity_is_configurable_and_sweep_preserves_work(self):
        workloads = {"p0_small": [sim.Op(i, "INT", command_address=(i % 1024)*8)
                                  for i in range(256)]}
        sweep = sim.run_p0_capacity_sweep(workloads, sim.PROFILES["nexus_balanced_128"])
        self.assertEqual(set(sweep["results"]), {"4", "8", "16", "32"})
        self.assertEqual({r["total_ops"] for r in sweep["results"].values()}, {256})
        self.assertEqual({r["kernels"]["p0_small"]["ops"]
                          for r in sweep["results"].values()}, {256})

    def test_fetch_latency_sweep_preserves_same_command_workload(self):
        workloads = {"p0_starvation": [
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
        self.assertEqual(set(sweep["results"]["nexus_p0"]), {"64", "96", "128", "160"})
        self.assertTrue(all(row["ops"] == 128
                            for group in sweep["results"].values()
                            for row in group.values()))


class FourWayAblationTests(unittest.TestCase):
    def test_four_profiles_preserve_operation_count_and_report_interaction(self):
        ops = [sim.Op(i, "LOAD", address=(i % 8)*64, width=64,
                      label="SPM2: ablation") for i in range(64)]
        result = sim.run_nexus_ablation({"small_spm_kernel": ops},
                                        sim.PROFILES["nexus_balanced_128"])
        self.assertEqual(set(result["variants"]), {"N-FULL", "N-NO-SPM", "N-NO-P0", "N-BASE"})
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


class PXMetadataTests(unittest.TestCase):
    def test_full_pages_auto_continue_and_partial_final_uses_px_end(self):
        pages = [
            {"logical_page_id": 0, "valid_bytes": 2048},
            {"logical_page_id": 1, "valid_bytes": 2048},
            {"logical_page_id": 2, "valid_bytes": 704, "marker": "PX_END"},
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
            {"logical_page_id": 0, "valid_bytes": 1536, "marker": "PX_NEXT",
             "next_logical_page_id": 1},
            {"logical_page_id": 1, "valid_bytes": 512, "marker": "PX_END"},
        ]
        self.assertTrue(sim.validate_px_page_descriptors(pages))
        ops = [sim.Op(0, "INT"), sim.Op(1, "INT")]
        self.assertEqual(len(ops), 2)

    def test_spm0_fetch_uses_px_next_and_stops_prefetch_at_px_end(self):
        fetch = sim.CommandFetchModel(True, page_descriptors={
            0: {"valid_bytes": 1024, "marker": "PX_NEXT", "next_logical_page_id": 1},
            1: {"valid_bytes": 512, "marker": "PX_END"},
        })
        self.assertFalse(fetch.can_fetch(0, 0))
        fetch.complete(48)
        self.assertTrue(fetch.can_fetch(0, 48))
        self.assertEqual(fetch.p0_pending, (1, 96, 1))
        self.assertFalse(fetch.can_fetch(2048, 49))
        fetch.complete(96)
        self.assertTrue(fetch.can_fetch(2048, 96))
        self.assertIsNone(fetch.p0_pending)  # PX_END suppresses next-page prefetch.
        with self.assertRaises(ValueError):
            fetch.can_fetch(2048 + 512, 97)  # No padding fetch past valid_bytes.
        with self.assertRaises(ValueError):
            fetch.can_fetch(4096, 97)  # PX_END cannot continue sequentially.

    def test_partial_page_without_marker_is_rejected(self):
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1024},
            ])

    def test_px_end_cannot_have_a_following_page(self):
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1024, "marker": "PX_END"},
                {"logical_page_id": 1, "valid_bytes": 8, "marker": "PX_END"},
            ])

    def test_px_next_requires_valid_next_page_and_alignment(self):
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1024, "marker": "PX_NEXT",
                 "next_logical_page_id": 2},
                {"logical_page_id": 1, "valid_bytes": 8, "marker": "PX_END"},
            ])
        with self.assertRaises(ValueError):
            sim.validate_px_page_descriptors([
                {"logical_page_id": 0, "valid_bytes": 1025, "marker": "PX_END"},
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


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestNexusMemoryBandwidthRevision(unittest.TestCase):
    def test_nexus_has_double_reference_dram_bandwidth(self):
        self.assertEqual(sim.PROFILES["nexus_balanced_128"]["dram_bytes_per_cycle"], 64)
        for key, expected in (("amd_9950x3d2", 21), ("intel_xeon_698x", 160), ("apple_m6", 48)):
            self.assertEqual(sim.PROFILES[key]["dram_bytes_per_cycle"], expected)
