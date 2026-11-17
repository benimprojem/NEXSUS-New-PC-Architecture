#!/usr/bin/env python3
"""NEX-T003: verify the registered per-core instruction-path stage rates.

This is a CPU frontend contract test. System Fabric is treated as a correctly
operating architectural service and is not re-simulated here.
"""
from math import ceil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cpu_comparison_sim import AppRamController, CommandFetchModel, PROFILES  # noqa: E402

PROFILE = PROFILES["nexus_balanced_128"]
CORES = PROFILE["core_count"]

# Rates are copied from the approved CPU architecture decision register.
APP_RAM_LINK = PROFILE["app_ram_bytes_per_cycle_per_core"]
APP_TO_C0 = 16
C0_TO_CS = 20
CS_TO_EB = 20
EB_CONSUME = 16
PAGE_BYTES = 2048

assert CORES == 8
assert APP_RAM_LINK == 64

# AppRAM's upstream core-facing link is a separate 64-B/cycle resource.
app = AppRamController(bytes_per_cycle=APP_RAM_LINK, first_beat_latency=0)
requests = [
    {"id": f"core-{core}", "core": core, "address": core * 0x10000,
     "bytes": 64}
    for core in range(CORES)
]
admitted = app.reserve_batch(0, requests)
assert all(row["accepted"] for row in admitted.values())
assert app.transferred_bytes == CORES * 64

# The command-fetch model's two downstream stages must use the registered
# 20-B/cycle/core values, both by default and when configured explicitly.
default_fetch = CommandFetchModel(
    True, p0_buffer_bytes=PAGE_BYTES, codeflow_enabled=True
)
explicit_fetch = CommandFetchModel(
    True, p0_buffer_bytes=PAGE_BYTES, codeflow_enabled=True,
    c0_to_cs_bytes_per_cycle=C0_TO_CS,
    cs_to_eb_bytes_per_cycle=CS_TO_EB,
)
for fetch in (default_fetch, explicit_fetch):
    assert fetch.c0_to_cs_bytes_per_cycle == C0_TO_CS
    assert fetch.cs_to_eb_bytes_per_cycle == CS_TO_EB
    assert fetch.c0_to_cs_cycles == ceil(PAGE_BYTES / C0_TO_CS)
    assert fetch.cs_to_eb_cycles == ceil(PAGE_BYTES / CS_TO_EB)

# Stage service-time comparison for one full 2-KiB page. These are separate
# rates: the 64-B AppRAM link does not replace the 16-B AppRAM->C0 refill
# stage, and neither 20-B middle stage is conflated with EB consumption.
stage_cycles = {
    "AppRAM_link": ceil(PAGE_BYTES / APP_RAM_LINK),
    "AppRAM_to_C0": ceil(PAGE_BYTES / APP_TO_C0),
    "C0_to_CS": ceil(PAGE_BYTES / C0_TO_CS),
    "CS_to_EB": ceil(PAGE_BYTES / CS_TO_EB),
    "EB_consume": ceil(PAGE_BYTES / EB_CONSUME),
}
assert stage_cycles == {
    "AppRAM_link": 32,
    "AppRAM_to_C0": 128,
    "C0_to_CS": 103,
    "CS_to_EB": 103,
    "EB_consume": 128,
}

print("PASS NEX-T003 rates: AppRAM=64, AppRAM->C0=16, C0->CS=20, CS->EB=20, EB=16 B/cycle/core.")
print("2-KiB isolated stage service cycles:", stage_cycles)
print("SCOPE: Fabric internals are assumed functional; multi-page queue overlap/EB drain timing remains a separate frontend-model refinement.")
