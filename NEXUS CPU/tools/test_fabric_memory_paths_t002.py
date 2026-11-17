#!/usr/bin/env python3
"""NEX-T002: verify independent App/Data RAM core-facing Fabric link capacity.

This test validates the per-core interface contract, not physical bank-group
availability, Fabric QoS across external clients, or MOSRAM timing.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cpu_comparison_sim import (  # noqa: E402
    AppRamController, DataRamController, PROFILES,
)

PROFILE = PROFILES["nexus_balanced_128"]
CORES = PROFILE["core_count"]
APP_RATE = PROFILE["app_ram_bytes_per_cycle_per_core"]
DATA_RATE = PROFILE["data_ram_bytes_per_cycle_per_core"]
assert CORES == 8
assert APP_RATE == DATA_RATE == 64

# Every core transfers 64 B in the same cycle on each independent memory path.
app = AppRamController(bytes_per_cycle=APP_RATE, first_beat_latency=0)
data = DataRamController(bytes_per_cycle_per_core=DATA_RATE)
app_requests = [
    {"id": f"app-{core}", "core": core, "address": core * 0x1000, "bytes": 64}
    for core in range(CORES)
]
data_requests = [
    {"id": f"data-{core}", "core": core, "address": core * 0x2000, "width": 64}
    for core in range(CORES)
]

# Both controllers receive their requests at the same global cycle. Neither
# controller's byte timeline is shared with the other memory system.
app_result = app.reserve_batch(0, app_requests)
data_result = data.reserve_batch(0, data_requests)

assert all(item["accepted"] for item in app_result.values())
assert all(item["service_complete_cycle"] == 1 for item in data_result.values())
assert all(item["ready_cycle"] <= 1 for item in app_result.values())
assert app.transferred_bytes == data.transferred_bytes == CORES * 64
assert app.bytes_by_core == {core: 64 for core in range(CORES)}
assert data.bytes_by_core == {core: 64 for core in range(CORES)}
assert data.bytes_per_cycle_per_core * CORES == 512

# A second 64-B request on core 0 queues behind core 0's own transfer, but does
# not consume or delay the other seven cores' independent links.
second = data.reserve_batch(0, [
    {"id": "data-0-second", "core": 0, "address": 0x4000, "width": 64},
    {"id": "data-1-second", "core": 1, "address": 0x6000, "width": 64},
])
assert second["data-0-second"]["service_complete_cycle"] == 2
assert second["data-1-second"]["service_complete_cycle"] == 2

print("PASS NEX-T002: App RAM and Data RAM each sustain 8 x 64 B/cycle core-facing transfers concurrently.")
print("PASS NEX-T002: aggregate core-facing capacity is 512 B/cycle per memory system.")
print("SCOPE: physical shared bank-group count/placement and multi-client Fabric arbitration remain open for NEX-T004.")
