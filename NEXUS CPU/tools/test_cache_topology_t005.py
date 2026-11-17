"""NEX-T005: eight-core cache hierarchy capacity and sharing contract."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cpu_comparison_sim import PROFILES, profile_from_dict, build_cache_hierarchies


def build():
    profile = profile_from_dict(PROFILES["nexus_balanced_128"])
    return profile, build_cache_hierarchies(profile, 8)


def test_eight_private_l1_four_l2_two_l3_one_l4_groups():
    profile, caches = build()
    assert len(caches) == 8
    assert len({id(c.l1) for c in caches}) == 8
    assert len({id(c.l2) for c in caches}) == 4
    assert len({id(c.l3) for c in caches}) == 2
    assert len({id(c.l4) for c in caches}) == 1

    for i in range(8):
        assert caches[i].l2 is caches[i ^ 1].l2
        assert caches[i].l3 is caches[(i // 4) * 4].l3
        assert caches[i].l4 is caches[0].l4
    assert caches[0].l2 is not caches[2].l2
    assert caches[0].l3 is not caches[4].l3


def test_each_group_has_registered_capacity():
    profile, caches = build()
    line = profile.line_bytes
    assert all(c.l1.capacity * line == 1 * 1024 * 1024 for c in caches)
    assert len({id(c.l2) for c in caches}) == 4
    assert all(caches[i].l2.capacity * line == 2 * 1024 * 1024
               for i in (0, 2, 4, 6))
    assert all(caches[i].l3.capacity * line == 8 * 1024 * 1024
               for i in (0, 4))
    assert caches[0].l4.capacity * line == 64 * 1024 * 1024


def test_cross_l3_group_access_uses_shared_l4_without_private_l1_alias():
    profile, caches = build()
    address = 0x12345000
    line = address // profile.line_bytes
    # Put a line in the single L4 home; cores 0 and 4 belong to separate L3 groups.
    caches[0].l4.insert(line)
    assert caches[0].l3 is not caches[4].l3
    latency, level = caches[4].probe(address)
    assert (latency, level) == (profile.l4_lat, "L4")
    assert line not in caches[4].l1.lines


def test_private_l1_does_not_leak_to_sibling_core():
    profile, caches = build()
    address = 0x23456000
    line = address // profile.line_bytes
    caches[0].l1.insert(line)
    assert line not in caches[1].l1.lines
    # The line was deliberately placed only in core 0's private L1.
    latency, level = caches[1].probe(address)
    assert (latency, level) == (profile.dram_lat, "DRAM")


if __name__ == "__main__":
    test_eight_private_l1_four_l2_two_l3_one_l4_groups()
    test_each_group_has_registered_capacity()
    test_cross_l3_group_access_uses_shared_l4_without_private_l1_alias()
    test_private_l1_does_not_leak_to_sibling_core()
    print("PASS NEX-T005: 8xL1, 4xL2, 2xL3, 1xL4 capacities and sharing; cross-L3 L4 lookup and private L1 isolation.")
    print("SCOPE: topology/capacity and lookup visibility only; coherence protocol, ports and transfer bandwidth are not inferred.")
