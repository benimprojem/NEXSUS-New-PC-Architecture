#!/usr/bin/env python3
"""Assertions for the generated 1/2/4/8-core scaling comparison."""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("core-scaling-output/core-scaling-results.json")
data = json.loads(path.read_text(encoding="utf-8"))
archs = {"amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"}
cores = (1, 2, 4, 8)
policies = {"common_512_aggregate"}

assert set(data["architectures"]) == archs
assert tuple(data["core_counts"]) == cores
assert set(data["runs"]) == policies
assert len(data["kernel_names"]) == 10

for policy in policies:
    for count in cores:
        run = data["runs"][policy][str(count)]
        assert set(run) == archs
        assert {row["cores_configured"] for row in run.values()} == {count}
        assert {row["aggregate_dram_bytes_per_cycle"] for row in run.values()} == {512}
        assert len({row["dram_latency_cycles"] for row in run.values()}) == 4
        for kernel in data["kernel_names"]:
            ops = {run[arch]["kernels"][kernel]["ops"] for arch in archs}
            assert len(ops) == 1, (policy, count, kernel, ops)

        nexus = run["nexus_balanced_128"]
        for kernel in data["kernel_names"]:
            controller = nexus["kernels"][kernel]["app_ram_controller"]
            assert controller is not None
            assert controller["per_core_bytes_per_cycle"] == 64
            active_cores = controller["active_core_count"]
            assert 1 <= active_cores <= count
            assert controller["aggregate_bytes_per_cycle"] == 64 * active_cores
            data_controller = nexus["kernels"][data["kernel_names"][0]]["memory_controller"]
            assert data_controller["per_core_bytes_per_cycle"] == 64
            assert data_controller["aggregate_core_facing_capacity_bytes_per_cycle"] == 64 * count
            # These kernels distribute work across every configured core.
            # Scalar/pointer-graph/hot-workset controls intentionally remain single-core.
            if kernel not in {"scalar_control", "pointer_graph", "tw_hot_workset"}:
                assert active_cores == count, (count, kernel, active_cores)

print("PASS: 1/2/4/8-core scaling, four architectures, ten identical logical workloads.")
print("PASS: 512 B/cycle DRAM ceiling; native latency retained; NEXSUS DataRAM/AppRAM links remain 64 B/cycle/core.")
