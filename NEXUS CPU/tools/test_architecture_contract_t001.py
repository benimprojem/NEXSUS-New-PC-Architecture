#!/usr/bin/env python3
"""NEX-T001: verify the declared NEXSUS architecture contract in the active simulator profile.

This is a configuration-contract test only. It does not certify cycle-accurate
memory service, System Fabric arbitration, or physical MOSRAM implementation.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cpu_comparison_sim import PROFILES  # noqa: E402

PROFILE_ID = "nexus_balanced_128"
profile = PROFILES[PROFILE_ID]

# CPU block and per-core execution resources.
assert profile["core_count"] == 8
assert profile["units"]["ARITH"] == 8
assert profile["units"]["LOGIC"] == 8
assert profile["units"]["CMP"] == 8
assert profile["units"]["FP"] == 6
assert profile["units"]["VEC"] == 2
assert profile["units"]["ME512"] == 1
assert profile["units"]["FMA"] == 4
assert "FMA_LANES" not in profile["execution_topology"]

# Cache capacities and sharing topology for one eight-core block.
assert profile["l1_kb"] == 1024
assert profile["l2_kb"] == 2048
assert profile["l3_kb"] == 8192
assert profile["l4_kb"] == 65536
assert profile["cache_grouping"] == {
    "l1_cores_per_group": 1,
    "l2_cores_per_group": 2,
    "l3_cores_per_group": 4,
    "l4_cores_per_group": 8,
}

# Both memory systems expose independent 64 B/cycle/core connection contracts.
assert profile["app_ram_bytes_per_cycle_per_core"] == 64
assert profile["data_ram_bytes_per_cycle_per_core"] == 64
assert profile["core_count"] * profile["app_ram_bytes_per_cycle_per_core"] == 512
assert profile["core_count"] * profile["data_ram_bytes_per_cycle_per_core"] == 512

# Minimum physical bank-group baseline: eight 64-bit banks, not 64 banks.
assert profile["app_ram_bank_count_per_group"] == 8
assert profile["data_ram_bank_count_per_group"] == 8
assert profile["memory_bank_slice_bits"] == 64
assert profile["memory_bank_group_width_bits"] == 512
assert profile["app_ram_bank_count_per_group"] * profile["memory_bank_slice_bits"] == 512
assert profile["data_ram_bank_count_per_group"] * profile["memory_bank_slice_bits"] == 512
assert profile["memory_fabric_shared"] is True

print("PASS NEX-T001: explicit 8-core CPU, execution, cache, App/Data RAM and 8x64-bit bank-group contract.")
print("NOTE NEX-T001 validates profile declarations only; service behavior is tested separately by NEX-T002/T004.")
