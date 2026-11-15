#!/usr/bin/env python3
"""Isolate NEXSUS branch misprediction recovery latency on fixed workloads.

This sweeps only the frontend recovery penalty. Predictor behavior, workload,
execution resources, and memory parameters remain fixed. It is a discrete-cycle
architecture model, not RTL or silicon timing.
"""
import argparse
import json

from cpu_comparison_sim import PROFILES, build_composite_workload, simulate_cpu

DEFAULT_PENALTIES = (4, 6, 8, 10, 12, 16)
TARGET_KERNELS = ("scalar_control", "pointer_graph", "branch_stress")


def run_branch_latency_sweep(scale=1, penalties=DEFAULT_PENALTIES):
    workloads = build_composite_workload(scale)
    target = {name: workloads[name] for name in TARGET_KERNELS}
    rows = {}
    for penalty in penalties:
        if penalty <= 0:
            raise ValueError("branch recovery penalty must be positive")
        profile = dict(PROFILES["nexus_balanced_128"])
        profile["branch_penalty"] = int(penalty)
        profile["branch_predictor"] = "small_2bit"
        run = simulate_cpu(
            target,
            profile,
            profile.get("core_count", 8),
            {
                "task_workspace": True,
                "code_slots": True,
                "p0_capacity_kb": 16,
                "p0_refill_latency": 48,
                "spm0_kb": 4,
                "spm0_bank_kb": 2,
            },
        )
        rows[str(penalty)] = {}
        for name in TARGET_KERNELS:
            result = run["kernels"][name]
            rows[str(penalty)][name] = {
                "ops": result["ops"],
                "cycles": result["cycles"],
                "mispredicts": result["branch_mispredicts"],
                "branch_recovery_cycles": result["stall_counters"]["branch_recovery_cycles"],
                "ops_preserved": result["ops"] == len(target[name]),
            }
    return {
        "experiment": "NEXSUS branch misprediction recovery latency sweep",
        "predictor": "small_2bit",
        "penalties_cycles": [int(x) for x in penalties],
        "results": rows,
        "assumptions": (
            "Only the frontend recovery penalty changes. A deterministic "
            "workload-class predictor model is used; this is not a cycle-accurate "
            "predictor or physical branch-unit measurement."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_branch_latency_sweep(args.scale)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print("NEXSUS BRANCH RECOVERY LATENCY SWEEP")
    for penalty, kernels in result["results"].items():
        for name, row in kernels.items():
            print(
                f"{name}: penalty={penalty} cycles={row['cycles']} "
                f"mispredicts={row['mispredicts']} "
                f"recovery_stall={row['branch_recovery_cycles']}"
            )


if __name__ == "__main__":
    main()
