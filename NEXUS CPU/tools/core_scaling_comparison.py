#!/usr/bin/env python3
"""Controlled 1/2/4/8-core scaling comparison for four CPU architecture models."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cpu_comparison_sim", HERE / "cpu_comparison_sim.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load cpu_comparison_sim.py")
SIM = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SIM
SPEC.loader.exec_module(SIM)

ARCHS = ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128")
CORE_COUNTS = (1, 2, 4, 8)
KERNELS = (
    "scalar_control", "pointer_graph", "numeric_tile", "streaming",
    "parallel_tasks", "integer_throughput", "fp_throughput",
    "branch_stress", "tw_hot_workset", "cs_sequential",
)
NEXSUS_FEATURES = {
    "task_workspace": True, "code_slots": True, "codeflow": True,
    "p0_capacity_kb": 16, "p0_refill_latency": 48,
}


def simulate(workloads, core_count, bandwidth_policy):
    results = {}
    for arch in ARCHS:
        profile = dict(SIM.PROFILES[arch])
        profile["frequency_ghz"] = 3.0
        # Keep each architecture's native DRAM latency. Normalize only the
        # aggregate CPU-facing data-memory budget to 512 B/cycle.
        profile["dram_bytes_per_cycle"] = 512
        if arch == "nexus_balanced_128":
            profile["data_ram_bytes_per_cycle_per_core"] = 64
        features = NEXSUS_FEATURES if arch == "nexus_balanced_128" else None
        results[arch] = SIM.simulate_cpu(workloads, profile, core_count, features)

    for kernel in workloads:
        counts = {results[arch]["kernels"][kernel]["ops"] for arch in ARCHS}
        if len(counts) != 1:
            raise AssertionError(f"logical operation mismatch for {kernel}: {counts}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("core-scaling-output"))
    args = parser.parse_args()
    if args.scale < 1:
        parser.error("--scale must be >= 1")

    all_workloads = SIM.build_composite_workload(args.scale)
    missing = sorted(set(KERNELS) - set(all_workloads))
    if missing:
        raise AssertionError(f"missing scaling kernels: {missing}")
    workloads = {name: all_workloads[name] for name in KERNELS}

    data = {
        "simulator_revision": os.environ.get("GITHUB_SHA", ""),
        "scale": args.scale,
        "core_counts": list(CORE_COUNTS),
        "kernel_names": list(KERNELS),
        "architectures": list(ARCHS),
        "controls": {
            "clock_ghz": 3.0,
            "aggregate_dram_bytes_per_cycle": 512,
            "dram_latency": "architecture-specific native profile values retained",
            "nexus_data_ram": "64 B/cycle/core independent links; 64/128/256/512 B/cycle aggregate core-facing capacity at 1/2/4/8 cores; 512 B/cycle aggregate DRAM ceiling retained",
            "reference_memory": "512 B/cycle aggregate shared memory interface",
            "nexus_app_ram": "independent 64 B/cycle/core AppRAM paths retained; AppRAM is not DataRAM",
            "cache_and_execution": "architecture-specific cache topology, capacity, latency, and execution resources retained",
            "result_class": "simulated event/cycle model; not physical silicon measurements",
        },
        "runs": {},
    }

    for policy in ("common_512_aggregate",):
        data["runs"][policy] = {}
        for cores in CORE_COUNTS:
            data["runs"][policy][str(cores)] = simulate(workloads, cores, policy)

    rows = []
    for policy in data["runs"]:
        for arch in ARCHS:
            for kernel in KERNELS:
                baseline = data["runs"][policy]["1"][arch]["kernels"][kernel]
                baseline_time = baseline["cycles"] / (3.0 * 1000.0)
                for cores in CORE_COUNTS:
                    result = data["runs"][policy][str(cores)][arch]
                    item = result["kernels"][kernel]
                    time_us = item["cycles"] / (3.0 * 1000.0)
                    speedup = baseline_time / time_us if time_us else 0.0
                    rows.append({
                        "bandwidth_policy": policy,
                        "architecture_id": arch,
                        "cores": cores,
                        "kernel": kernel,
                        "ops": item["ops"],
                        "cycles": item["cycles"],
                        "modeled_time_us": round(time_us, 6),
                        "aggregate_ipc": item["aggregate_ipc"],
                        "speedup_vs_1core": round(speedup, 6),
                        "parallel_efficiency": round(speedup / cores, 6),
                        "dram_bytes_per_cycle": result["aggregate_dram_bytes_per_cycle"],
                        "app_ram_aggregate_bytes_per_cycle": (
                            item["app_ram_controller"]["aggregate_bytes_per_cycle"]
                            if item["app_ram_controller"] else None
                        ),
                    })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "core-scaling-results.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    with (args.output_dir / "core-scaling-results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 1/2/4/8-core scaling comparison",
        "",
        "All four models use 3.0 GHz and 120-cycle DRAM latency. Results are simulated, not silicon measurements.",
        "",
        "Two distinct memory controls are reported:",
        "- fixed_system_32: fixed 32 B/cycle aggregate DRAM bandwidth at every core count.",
        "- scaled_4_per_core: 4 B/cycle/core equivalent aggregate budget, scaling 4/8/16/32 B/cycle.",
        "- Both use one shared, work-conserving DRAM bus without static per-core quotas.",
        "- NEXSUS AppRAM remains a separate 64 B/cycle/core path; it is not counted as DRAM bandwidth.",
        "",
        "Lower modeled time/cycles is better. Higher IPC, speedup and parallel efficiency are better.",
        "Efficiency is speedup divided by core count. Inspect each kernel separately; do not rank CPUs by summing unrelated kernel times.",
        "",
    ]
    for policy in data["runs"]:
        lines += [f"## {policy}", "",
                  "| Kernel | Architecture | 1 core µs | 2 cores µs | 4 cores µs | 8 cores µs | 8-core speedup | 8-core efficiency |",
                  "|---|---|---:|---:|---:|---:|---:|---:|"]
        for kernel in KERNELS:
            for arch in ARCHS:
                times = []
                for cores in CORE_COUNTS:
                    cycles = data["runs"][policy][str(cores)][arch]["kernels"][kernel]["cycles"]
                    times.append(cycles / 3000.0)
                speedup = times[0] / times[-1] if times[-1] else 0.0
                lines.append(
                    f"| {kernel} | {arch} | {times[0]:.3f} | {times[1]:.3f} | "
                    f"{times[2]:.3f} | {times[3]:.3f} | {speedup:.3f}x | "
                    f"{speedup/8:.3f} |"
                )
        lines.append("")
    (args.output_dir / "core-scaling-results.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"PASS: {len(KERNELS)} kernels x 4 architectures x 4 core counts x 2 memory policies.")
    print(f"PASS: {len(rows)} per-kernel scaling rows; logical operation counts match.")
    print(f"Report: {args.output_dir / 'core-scaling-results.md'}")
    print(f"CSV: {args.output_dir / 'core-scaling-results.csv'}")


if __name__ == "__main__":
    main()
