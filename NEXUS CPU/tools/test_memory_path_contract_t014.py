#!/usr/bin/env python3
"""T014: verify NEXSUS AppRAM/DataRAM independence and cache-fill topology."""
from cpu_comparison_sim import (
    PROFILES, AppRamController, DataRamController, CacheHierarchy, profile_from_dict
)


def test_per_core_data_ram_rate_is_not_aggregate_dram_width():
    profile = PROFILES["nexus_balanced_128"]
    assert profile["data_ram_bytes_per_cycle_per_core"] == 64
    assert profile["dram_bytes_per_cycle"] == 64
    assert profile["data_ram_bytes_per_cycle_per_core"] * 8 == 512
    assert profile["memory_bank_group_width_bits"] == 512


def test_app_ram_and_data_ram_progress_independently():
    app = AppRamController(bytes_per_cycle=64, first_beat_latency=40)
    data = DataRamController(bytes_per_cycle_per_core=64)
    app_result = app.reserve_batch(100, [{
        "id": "app-page", "core": 0, "address": 0, "bytes": 2048
    }])["app-page"]
    data_result = data.reserve_batch(100, [{
        "id": "data-line", "core": 0, "address": 0x1000, "width": 64
    }])["data-line"]
    assert app_result["accepted"]
    assert data_result["ready_cycle"] == 101
    assert app_result["ready_cycle"] > data_result["ready_cycle"]
    # DataRAM service is unchanged when AppRAM is busy: distinct controllers,
    # independent per-core byte timelines, no shared queue or bus cursor.
    data_again = DataRamController(bytes_per_cycle_per_core=64)
    isolated = data_again.reserve_batch(100, [{
        "id": "data-line", "core": 0, "address": 0x1000, "width": 64
    }])["data-line"]
    assert isolated["ready_cycle"] == data_result["ready_cycle"]


def test_eight_cores_have_eight_independent_data_ram_links():
    controller = DataRamController(bytes_per_cycle_per_core=64)
    requests = [{
        "id": f"core-{core}", "core": core,
        "address": core * 0x1000, "width": 64
    } for core in range(8)]
    results = controller.reserve_batch(25, requests)
    assert len(results) == 8
    assert all(row["ready_cycle"] == 26 for row in results.values())
    assert controller.transferred_bytes == 8 * 64
    assert controller.bytes_by_core == {core: 64 for core in range(8)}


def test_cache_fill_walks_l4_l3_l2_l1_with_fixed_grouping():
    profile = profile_from_dict(PROFILES["nexus_balanced_128"])
    shared_l4 = None
    shared_l3 = {}
    shared_l2 = {}
    caches = []
    for core in range(8):
        pair = core // 2
        quad = core // 4
        if pair not in shared_l2:
            from cpu_comparison_sim import LRU
            shared_l2[pair] = LRU(profile.l2_kb * 1024, profile.line_bytes)
        if quad not in shared_l3:
            from cpu_comparison_sim import LRU
            shared_l3[quad] = LRU(profile.l3_kb * 1024, profile.line_bytes)
        if shared_l4 is None:
            from cpu_comparison_sim import LRU
            shared_l4 = LRU(profile.l4_kb * 1024, profile.line_bytes)
        caches.append(CacheHierarchy(profile, shared_l2[pair], shared_l3[quad], shared_l4))

    address = 0x123400
    latency, level = caches[0].probe(address)
    assert level == "DRAM"
    caches[0].fill(address, level)
    assert caches[0].probe(address)[1] == "L1"
    assert caches[1].probe(address)[1] == "L2"  # same pair
    assert caches[2].probe(address)[1] == "L3"  # same four-core group
    assert caches[4].probe(address)[1] == "L4"  # other L3 group, same eight-core L4
    assert caches[0].l1.capacity == (1024 * 1024) // 64
    assert caches[0].l2.capacity == (2 * 1024 * 1024) // 64
    assert caches[0].l3.capacity == (8 * 1024 * 1024) // 64
    assert caches[0].l4.capacity == (64 * 1024 * 1024) // 64


if __name__ == "__main__":
    tests = [
        test_per_core_data_ram_rate_is_not_aggregate_dram_width,
        test_app_ram_and_data_ram_progress_independently,
        test_eight_cores_have_eight_independent_data_ram_links,
        test_cache_fill_walks_l4_l3_l2_l1_with_fixed_grouping,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} T014 memory-path contract tests")
