#!/usr/bin/env python3
"""Paired NEXSUS scheduler-window sweep with ROB fixed at 512 entries."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cpu_comparison_sim", HERE / "cpu_comparison_sim.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load cpu_comparison_sim.py")
SIM = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SIM
SPEC.loader.exec_module(SIM)

ROB_ENTRIES = 512
SCHEDULER_ENTRIES = (64, 128)
CORE_COUNTS = (1, 2, 4, 8)
KERNELS = (
    "scalar_control", "pointer_graph", "numeric_tile", "streaming",
    "parallel_tasks", "integer_throughput", "integer128_throughput",
    "fp_throughput", "branch_stress", "tw_hot_workset", "cs_sequential",
    "vector_throughput", "fma_throughput",
)


def run_sweep(scale: int = 1) -> dict:
    if scale < 1:
        raise ValueError("scale must be >= 1")
    all_workloads = SIM.build_composite_workload(scale)
    missing = sorted(set(KERNELS) - set(all_workloads))
    if missing:
        raise AssertionError(f"missing sweep kernels: {missing}")

    rows = []
    for scheduler_entries in SCHEDULER_ENTRIES:
        for cores in CORE_COUNTS:
            profile = dict(SIM.PROFILES["nexus_balanced_128"])
            profile["rob"] = ROB_ENTRIES
            profile["scheduler_entries"] = scheduler_entries
            profile["frequency_ghz"] = 3.0
            for kernel in KERNELS:
                result = SIM.simulate_cpu(
                    {kernel: all_workloads[kernel]}, profile, cores,
                    {"task_workspace": True, "code_slots": True, "codeflow": False,
                     "p0_capacity_kb": 16, "p0_refill_latency": 48,
                     "execution_only": True},
                )
                item = result["kernels"][kernel]
                rows.append({
                    "scheduler_entries": scheduler_entries,
                    "rob_entries": result["rob_entries"],
                    "cores": cores,
                    "kernel": kernel,
                    "ops": item["ops"],
                    "cycles": item["cycles"],
                    "aggregate_ipc": item["aggregate_ipc"],
                    "max_rob_occupancy": item["max_rob_occupancy"],
                    "max_scheduler_occupancy": item["max_scheduler_occupancy"],
                    "scheduler_full_cycles": item["stall_counters"]["scheduler_full_cycles"],
                    "rob_full_cycles": item["stall_counters"]["rob_full_cycles"],
                    "dependency_blocked_op_cycles": item["stall_counters"]["dependency_blocked_op_cycles"],
                    "issue_width_blocked_op_cycles": item["stall_counters"]["issue_width_blocked_op_cycles"],
                    "execution_unit_blocked_op_cycles": item["stall_counters"]["execution_unit_blocked_op_cycles"],
                    "frontend_limited_cycles": item["stall_counters"]["frontend_limited_cycles"],
                    "memory_latency_exposure_cycles": item["stall_counters"]["memory_latency_exposure_cycles"],
                })

    paired = {}
    for cores in CORE_COUNTS:
        for kernel in KERNELS:
            candidates = {row["scheduler_entries"]: row for row in rows
                          if row["cores"] == cores and row["kernel"] == kernel}
            if set(candidates) != set(SCHEDULER_ENTRIES):
                raise AssertionError(f"unpaired result: {cores} cores / {kernel}")
            a, b = candidates[64], candidates[128]
            if a["ops"] != b["ops"] or a["rob_entries"] != ROB_ENTRIES or b["rob_entries"] != ROB_ENTRIES:
                raise AssertionError(f"configuration/work mismatch: {cores} cores / {kernel}")
            paired[f"{cores}:{kernel}"] = {
                "cycles_64": a["cycles"], "cycles_128": b["cycles"],
                "winner": 64 if a["cycles"] < b["cycles"] else (128 if b["cycles"] < a["cycles"] else "tie"),
                "cycle_delta_128_vs_64": b["cycles"] - a["cycles"],
            }
    return {
        "experiment": "NEXSUS scheduler capacity comparison",
        "scale": scale,
        "cores": list(CORE_COUNTS),
        "scheduler_entries_tested": list(SCHEDULER_ENTRIES),
        "rob_entries_fixed": ROB_ENTRIES,
        "clock_ghz": 3.0,
        "dispatch_per_cycle": 8,
        "issue_per_cycle": 10,
        "retire_per_cycle": 8,
        "execution_only": True,
        "kernels": list(KERNELS),
        "row_count": len(rows),
        "rows": rows,
        "paired_comparison": paired,
        "decision": "No scheduler capacity selected automatically; inspect per-kernel results and stall counters.",
        "model_limitations": [
            "This is a cycle-level simulator experiment, not RTL or silicon measurement.",
            "The scheduler is modeled as one unified per-core queue; separate INT/FP/LOAD reservation queues are not modeled.",
            "ROB and scheduler occupancy are independent: issued operations leave the scheduler but remain in the ROB until in-order retirement.",
            "Execution-only mode isolates backend scheduling from CodeFlow instruction-fetch supply."
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path("scheduler-rob-output"))
    args = parser.parse_args()
    data = run_sweep(args.scale)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "scheduler-rob-results.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    with (args.output_dir / "scheduler-rob-results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data["rows"][0]))
        writer.writeheader()
        writer.writerows(data["rows"])

    lines = [
        "# NEXSUS scheduler capacity comparison",
        "",
        f"- ROB fixed: **{ROB_ENTRIES} entries per core**",
        "- Scheduler candidates: **64 vs 128 entries per core**",
        "- Dispatch / issue / retire: **8 / 10 / 8 per cycle**",
        "- Clock: **3.0 GHz**",
        "- Execution-only mode: instruction-fetch supply excluded from this experiment",
        "",
        "## Paired results",
        "",
        "| Cores | Kernel | 64-entry cycles | 128-entry cycles | Better result | 64 scheduler-full cycles | 128 scheduler-full cycles |",
        "|---:|---|---:|---:|---|---:|---:|",
    ]
    for cores in CORE_COUNTS:
        for kernel in KERNELS:
            a = next(row for row in data["rows"] if row["cores"] == cores and row["kernel"] == kernel and row["scheduler_entries"] == 64)
            b = next(row for row in data["rows"] if row["cores"] == cores and row["kernel"] == kernel and row["scheduler_entries"] == 128)
            winner = "Tie" if a["cycles"] == b["cycles"] else ("64" if a["cycles"] < b["cycles"] else "128")
            lines.append(f"| {cores} | {kernel} | {a['cycles']} | {b['cycles']} | {winner} | {a['scheduler_full_cycles']} | {b['scheduler_full_cycles']} |")
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- The scheduler is modeled as one unified per-core queue; separate INT/FP/LOAD reservation queues are not modeled.",
        "- Issued operations leave the scheduler but remain in the ROB until in-order retirement.",
        "- This experiment isolates backend scheduling from CodeFlow instruction-fetch supply; it does not select a final hardware value automatically.",
        "- Results are simulated cycle-model outputs, not silicon measurements.",
        "",
    ]
    (args.output_dir / "scheduler-rob-results.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"PASS: {data['row_count']} paired rows; ROB={ROB_ENTRIES}; scheduler=64/128; 1/2/4/8 cores.")
    print(f"Results: {args.output_dir / 'scheduler-rob-results.md'}")


if __name__ == "__main__":
    main()
