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
    assert data_result["service_complete_cycle"] == 101
    assert app_result["ready_cycle"] > data_result["service_complete_cycle"]
    # DataRAM service is unchanged when AppRAM is busy: distinct controllers,
    # independent per-core byte timelines, no shared queue or bus cursor.
    data_again = DataRamController(bytes_per_cycle_per_core=64)
    isolated = data_again.reserve_batch(100, [{
        "id": "data-line", "core": 0, "address": 0x1000, "width": 64
    }])["data-line"]
    assert isolated["service_complete_cycle"] == data_result["service_complete_cycle"]


def test_eight_cores_have_eight_independent_data_ram_links():
    controller = DataRamController(bytes_per_cycle_per_core=64)
    requests = [{
        "id": f"core-{core}", "core": core,
        "address": core * 0x1000, "width": 64
    } for core in range(8)]
    results = controller.reserve_batch(25, requests)
    assert len(results) == 8
    assert all(row["service_complete_cycle"] == 26 for row in results.values())
    assert controller.transferred_bytes == 8 * 64
    assert controller.bytes_by_core == {core: 64 for core in range(8)}


def make_nexus_cache_group(core_count=8):
    from cpu_comparison_sim import LRU
    profile = profile_from_dict(PROFILES["nexus_balanced_128"])
    shared_l2 = {}
    shared_l3 = {}
    shared_l4 = LRU(profile.l4_kb * 1024, profile.line_bytes)
    caches = []
    for core in range(8):
        pair = core // 2
        quad = core // 4
        shared_l2.setdefault(pair, LRU(profile.l2_kb * 1024, profile.line_bytes))
        shared_l3.setdefault(quad, LRU(profile.l3_kb * 1024, profile.line_bytes))
        caches.append(CacheHierarchy(profile, shared_l2[pair], shared_l3[quad], shared_l4))
    return caches


def test_nexus_l4_distributes_directly_to_active_group_level():
    address = 0x123400
    line = address // 64

    # Eight active cores: L4 fans out to all eight private L1s at once.
    caches = make_nexus_cache_group(8)
    caches[0].fill(address, "DRAM", active_core_count=8, peer_caches=caches, core_id=0)
    assert all(cache.l1.lookup(line) for cache in caches)
    assert caches[0].l4.lookup(line)
    assert not any(cache.l2.lookup(line) for cache in caches)
    assert not any(cache.l3.lookup(line) for cache in caches)

    # Four active cores: one shared L3 receives the line directly.
    caches = make_nexus_cache_group(4)
    caches[0].fill(address, "DRAM", active_core_count=4, peer_caches=caches, core_id=0)
    assert all(caches[i].l3.lookup(line) for i in range(4))
    assert not any(cache.l1.lookup(line) for cache in caches)
    assert not any(cache.l2.lookup(line) for cache in caches)
    assert not caches[4].l3.lookup(line)

    # Two active cores: their shared L2 is the direct destination.
    caches = make_nexus_cache_group(2)
    caches[0].fill(address, "DRAM", active_core_count=2, peer_caches=caches, core_id=0)
    assert caches[0].l2.lookup(line) and caches[1].l2.lookup(line)
    assert not any(cache.l1.lookup(line) for cache in caches)
    assert not caches[2].l2.lookup(line)

    # One active core: direct L4-to-L1 placement.
    caches = make_nexus_cache_group(1)
    caches[0].fill(address, "DRAM", active_core_count=1, peer_caches=caches, core_id=0)
    assert caches[0].l1.lookup(line)
    assert not caches[1].l1.lookup(line)
    assert caches[0].l4.lookup(line)

    assert caches[0].l1.capacity == (1024 * 1024) // 64
    assert caches[0].l2.capacity == (2 * 1024 * 1024) // 64
    assert caches[0].l3.capacity == (8 * 1024 * 1024) // 64
    assert caches[0].l4.capacity == (64 * 1024 * 1024) // 64


if __name__ == "__main__":
    tests = [
        test_per_core_data_ram_rate_is_not_aggregate_dram_width,
        test_app_ram_and_data_ram_progress_independently,
        test_eight_cores_have_eight_independent_data_ram_links,
        test_nexus_l4_distributes_directly_to_active_group_level,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} T014 memory-path contract tests")
