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


def simulate(workloads, core_count, bandwidth_policy="common_512_aggregate"):
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
            "reference_aggregate_memory_bytes_per_cycle": 512,
            "dram_latency": "architecture-specific native profile values retained",
            "nexus_data_ram": "independent 64 B/cycle/core DataRAM links; aggregate path capacity 64/128/256/512 B/cycle at 1/2/4/8 cores",
            "reference_memory": "512 B/cycle aggregate shared memory interface",
            "nexus_app_ram": "independent 64 B/cycle/core AppRAM links; aggregate path capacity 64/128/256/512 B/cycle at 1/2/4/8 cores; never shares the DataRAM path",
            "nexus_memory_domains": "AppRAM and DataRAM are separate physical memory domains/controllers; each can independently reach 512 B/cycle at 8 cores (up to 1024 B/cycle combined)",
            "cache_and_execution": "architecture-specific cache topology, capacity, latency, and execution resources retained",
            "result_class": "simulated event/cycle model; not physical silicon measurements",
        },
        "runs": {},
    }

    for policy in ("common_512_aggregate",):
        data["runs"][policy] = {}
        for cores in CORE_COUNTS:
            data["runs"][policy][str(cores)] = simulate(workloads, cores, policy)

    audit_rows = []
    for cores in CORE_COUNTS:
        for arch in ARCHS:
            profile = SIM.PROFILES[arch]
            nexus = arch == "nexus_balanced_128"
            audit_rows.append({
                "architecture_id": arch,
                "cores": cores,
                "clock_ghz": 3.0,
                "aggregate_dram_ceiling_bytes_per_cycle": 512,
                "dram_latency_cycles": profile["dram_lat"],
                "data_ram_bytes_per_cycle_per_core": 64 if nexus else "N/A",
                "data_ram_core_facing_aggregate_bytes_per_cycle": 64 * cores if nexus else "N/A",
                "app_ram_bytes_per_cycle_per_core": 64 if nexus else "N/A",
                "app_ram_aggregate_bytes_per_cycle": 64 * cores if nexus else "N/A",
                "l1_kib_per_core": profile["l1_kb"],
                "l2_kib_per_group": profile["l2_kb"],
                "l3_kib_per_group": profile["l3_kb"],
                "l4_kib_per_group": profile["l4_kb"],
                "l1_latency_cycles": profile["l1_lat"],
                "l2_latency_cycles": profile["l2_lat"],
                "l3_latency_cycles": profile["l3_lat"],
                "l4_latency_cycles": profile["l4_lat"],
            })

    data["configuration_audit"] = audit_rows
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
    with (args.output_dir / "core-scaling-configuration-audit.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

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
        "## Configuration audit",
        "",
        "| Architecture | Cores | Clock GHz | DRAM B/cycle | DRAM latency | DataRAM B/cycle/core | DataRAM aggregate | AppRAM B/cycle/core | AppRAM aggregate | L1 KiB | L2 KiB | L3 KiB | L4 KiB |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        *[f"| {row['architecture_id']} | {row['cores']} | {row['clock_ghz']:.1f} | {row['aggregate_dram_ceiling_bytes_per_cycle']} | {row['dram_latency_cycles']} | {row['data_ram_bytes_per_cycle_per_core']} | {row['data_ram_core_facing_aggregate_bytes_per_cycle']} | {row['app_ram_bytes_per_cycle_per_core']} | {row['app_ram_aggregate_bytes_per_cycle']} | {row['l1_kib_per_core']} | {row['l2_kib_per_group']} | {row['l3_kib_per_group']} | {row['l4_kib_per_group']} |" for row in audit_rows],
        "",
        "All four models use 3.0 GHz. Reference CPUs use a 512 B/cycle aggregate shared memory interface. NEXSUS has two independent memory domains: DataRAM and AppRAM each scale from 64 to 512 B/cycle across 1 to 8 cores. Native architecture-specific DRAM latency is retained. Results are simulated, not silicon measurements.",
        "",
        "Memory and cache settings checked by this run:",
        "- Reference CPU shared memory interface: 512 B/cycle aggregate.",
        "- NEXSUS DataRAM: 64 B/cycle/core (64/128/256/512 B/cycle at 1/2/4/8 cores).",
        "- NEXSUS AppRAM: physically separate 64 B/cycle/core path (64/128/256/512 B/cycle at 1/2/4/8 cores).",
        "- NEXSUS AppRAM and DataRAM can each independently reach 512 B/cycle; they do not share one 512 B/cycle bottleneck.",
        "- Native DRAM latency, cache sizes/topology/latencies and execution resources are retained.",
        "- The NEXSUS shared physical DRAM bank/arbitration stage remains a separately tracked integration item; this comparison verifies its configured 512 B/cycle ceiling, not its final physical timing.",
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
    print(f"PASS: {len(KERNELS)} kernels x 4 architectures x 4 core counts; reference shared memory is 512 B/cycle and NEXSUS AppRAM/DataRAM are independent paths.")
    print(f"PASS: {len(rows)} per-kernel scaling rows; logical operation counts match.")
    print(f"Report: {args.output_dir / 'core-scaling-results.md'}")
    print(f"CSV: {args.output_dir / 'core-scaling-results.csv'}")
    print(f"Configuration audit: {args.output_dir / 'core-scaling-configuration-audit.csv'}")


if __name__ == "__main__":
    main()
