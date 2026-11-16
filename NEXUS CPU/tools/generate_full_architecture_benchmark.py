#!/usr/bin/env python3
"""Generate native-core and normalized-8-core comparison tables from the event/cycle model."""
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
LABELS = {
    "amd_9950x3d2": "AMD Ryzen 9 9950X3D2 / Zen 5",
    "intel_xeon_698x": "Intel Xeon 698X / Granite Rapids",
    "apple_m6": "Apple M6 / homogeneous 12-core approximation",
    "nexus_balanced_128": "NEXSUS Balanced 128",
}
NEXSUS_FEATURES = {
    "task_workspace": True, "code_slots": True, "codeflow": True,
    "p0_capacity_kb": 16, "p0_refill_latency": 48,
}

def run_mode(workloads, normalized):
    results = {}
    for arch in ARCHS:
        profile = SIM.PROFILES[arch]
        cores = 8 if normalized else profile["core_count"]
        features = NEXSUS_FEATURES if arch == "nexus_balanced_128" else None
        results[arch] = SIM.simulate_cpu(workloads, profile, cores, features)
    for kernel in workloads:
        counts = {results[a]["kernels"][kernel]["ops"] for a in ARCHS}
        if len(counts) != 1:
            raise AssertionError(f"Logical operation count mismatch for {kernel}: {counts}")
    return results

def make_row(mode, arch, result, kernel):
    item = result["kernels"][kernel]
    stalls = item["stall_counters"]
    return {
        "mode": mode, "architecture_id": arch, "architecture": LABELS[arch],
        "cores": result["cores_configured"], "clock_ghz_model": result["clock_ghz"],
        "kernel": kernel, "ops": item["ops"], "cycles": item["cycles"],
        "modeled_time_us": round(item["cycles"] / (result["clock_ghz"] * 1000.0), 6),
        "ipc": item["aggregate_ipc"], "dram_accesses": item["cache_accesses"]["DRAM"],
        "branch_mispredicts": item["branch_mispredicts"],
        "frontend_wait_cycles": item["codeflow_counters"]["wait_cycles"],
        "memory_latency_exposure_cycles": stalls["memory_latency_exposure_cycles"],
        "execution_unit_blocked_op_cycles": stalls["execution_unit_blocked_op_cycles"],
        "task_workspace_overflow": item["workspace_counters"]["overflow"],
    }

def render_report(data):
    lines = [
        "# NEXSUS CPU — Full Architecture Benchmark Results", "",
        f"- Simulator revision: {data['simulator_revision'] or 'not supplied'}",
        f"- Workload scale: {data['scale']}",
        f"- Kernel count: {len(data['kernel_names'])}",
        "- Result class: SIMULATED event/cycle model; not physical silicon measurements.",
        "- Correctness gate: identical logical operation count for every kernel across all four profiles.", "",
        "## Profile and fairness policy", "",
        "| Profile | Native modeled cores | Clock input | Native modeled strengths |",
        "|---|---:|---:|---|",
        "| AMD Ryzen 9 9950X3D2 / Zen 5 | 16 | 4.3 GHz | x86-64, AVX-512/FMA, large 3D V-Cache model |",
        "| Intel Xeon 698X / Granite Rapids | 86 | 2.0 GHz base | x86-64, AMX, 86 P-cores |",
        "| Apple M6 | 12 | 3.0 GHz assumption | ARM vector; homogeneous approximation of 2 super + 4 performance + 6 efficiency cores |",
        "| NEXSUS Balanced 128 | 8 | 3.0 GHz assumption | L1/L2/L3/L4, 512-bit VEC, ME512, Task Workspace, CodeFlow |", "",
        "The simulator allows each profile to use its configured execution resources. Clock, cache latency, issue width, and several vendor-private details are model assumptions. Apple core classes are not yet scheduled separately. NEXSUS values are proposals, not measured silicon limits.", "",
        "## Native core-count summary", "",
        "| Architecture | Cores | Clock | Sum cycles* | Sum modeled time (µs)* | Aggregate IPC* |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    native = data["modes"]["native"]
    for arch in ARCHS:
        r = native[arch]
        us = sum(k["cycles"] / (r["clock_ghz"] * 1000.0) for k in r["kernels"].values())
        lines.append(f"| {LABELS[arch]} | {r['cores_configured']} | {r['clock_ghz']:.2f} GHz | {r['total_cycles']:,} | {us:,.3f} | {r['aggregate_ipc']:.3f} |")
    lines += ["", "*Diagnostic sums across separate kernels, not a standardized overall score. Do not rank systems from this summary row alone.", ""]
    for mode_key, heading in (("native", "Per-kernel comparison — native core counts"),
                              ("normalized_8core", "Per-kernel comparison — normalized 8-core")):
        lines += [f"## {heading}", "",
                  "| Kernel | Logical ops | AMD cycles / µs | Intel cycles / µs | Apple cycles / µs | NEXSUS cycles / µs |",
                  "|---|---:|---:|---:|---:|---:|"]
        for kernel in data["kernel_names"]:
            cells, ops = [], None
            for arch in ARCHS:
                r = data["modes"][mode_key][arch]
                k = r["kernels"][kernel]
                ops = k["ops"]
                us = k["cycles"] / (r["clock_ghz"] * 1000.0)
                cells.append(f"{k['cycles']:,} / {us:.3f}")
            lines.append(f"| {kernel} | {ops:,} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += [
        "## Interpretation limits", "",
        "1. Same deterministic operation graph, inputs and per-kernel logical operation count across all profiles.",
        "2. Each profile maps operations to its configured native resources, including Intel AMX and NEXSUS ME512; no scalar-only handicap is imposed.",
        "3. Native mode compares package-scale modeled core counts. Normalized mode uses exactly eight active cores per profile.",
        "4. Modeled time is cycles divided by configured clock; it is not measured runtime.",
        "5. Cache coherence, vendor-private predictor details, Apple heterogeneous scheduling, and several physical timings remain approximate or open.",
        "6. A final silicon comparison requires running identical validated binaries and inputs on physical systems, with each vendor's optimizing compiler and documented flags.",
        "",
        "## External standardized validation", "",
        "Use SPEC CPU 2026 as the external real-hardware anchor. It contains 52 benchmarks across four suites: SPECspeed Integer, SPECspeed Floating Point, SPECrate Integer, and SPECrate Floating Point. Run the complete selected suite under official rules and preserve compiler versions/flags. The custom suite remains the architecture-diagnostic companion for NEXSUS-specific resources such as L4 sharing, Task Workspace, CodeFlow and ME512.",
        "",
    ]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark-output"))
    args = parser.parse_args()
    if args.scale < 1:
        parser.error("--scale must be >= 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    workloads = SIM.build_composite_workload(args.scale)
    data = {
        "simulator_revision": os.environ.get("GITHUB_SHA", ""),
        "scale": args.scale, "kernel_names": list(workloads),
        "modes": {
            "native": run_mode(workloads, False),
            "normalized_8core": run_mode(workloads, True),
        },
        "result_class": "simulated event/cycle model; not physical silicon measurements",
    }
    rows = []
    for mode in ("native", "normalized_8core"):
        for arch in ARCHS:
            result = data["modes"][mode][arch]
            for kernel in workloads:
                rows.append(make_row(mode, arch, result, kernel))
    (args.output_dir / "full-architecture-results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (args.output_dir / "full-architecture-results.md").write_text(render_report(data), encoding="utf-8")
    with (args.output_dir / "full-architecture-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"PASS: {len(workloads)} kernels x 4 profiles x 2 core policies.")
    print(f"PASS: {len(rows)} per-kernel result rows; operation counts identical.")
    print(f"Report: {args.output_dir / 'full-architecture-results.md'}")
    print(f"CSV: {args.output_dir / 'full-architecture-results.csv'}")

if __name__ == "__main__":
    main()
