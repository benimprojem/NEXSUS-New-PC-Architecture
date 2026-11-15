#!/usr/bin/env python3
"""Focused rate-interaction sweep for the two apparent frontend bottlenecks.

Discrete-cycle model only; not RTL or silicon measurements. App RAM instruction
fetch is modeled here. Data RAM remains an independent path/controller.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from p0p1_l0i_px_integrated_sim import Config, IntegratedFrontend


FOCUSED_RATES = (8, 12, 16, 24, 32)


def build_cases() -> list[tuple[str, Config]]:
    cases: list[tuple[str, Config]] = []
    for p0_rate in FOCUSED_RATES:
        for eb_rate in FOCUSED_RATES:
            cfg = Config(
                p0p1_to_c0_bytes_per_cycle=p0_rate,
                eb_consume_bytes_per_cycle=eb_rate,
            )
            cases.append((f"p0p1={p0_rate},eb={eb_rate}", cfg))

    # Queue-depth sensitivity once both apparent bottlenecks are raised equally.
    for depth in (1, 2, 4, 8):
        cfg = Config(
            p0p1_to_c0_bytes_per_cycle=16,
            eb_consume_bytes_per_cycle=16,
            queue_depth=depth,
        )
        cases.append((f"balanced16_queue={depth}", cfg))

    return cases


def run_sweep(pages: int = 32) -> dict:
    if pages <= 0:
        raise ValueError("pages must be positive")

    rows = []
    for label, cfg in build_cases():
        result = IntegratedFrontend(cfg).run(pages)
        rows.append({
            "case": label,
            "config": {
                "p0p1_to_c0_bytes_per_cycle": cfg.p0p1_to_c0_bytes_per_cycle,
                "eb_consume_bytes_per_cycle": cfg.eb_consume_bytes_per_cycle,
                "queue_depth": cfg.queue_depth,
                "app_bytes_per_cycle": cfg.app_bytes_per_cycle,
                "app_setup_cycles": cfg.app_setup_cycles,
                "c0_to_cs_bytes_per_cycle": cfg.c0_to_cs_bytes_per_cycle,
                "cs_to_eb_bytes_per_cycle": cfg.cs_to_eb_bytes_per_cycle,
            },
            "cycles": result.cycles,
            "pages_retired": result.pages_retired,
            "p0p1_to_c0_busy_cycles": result.p0p1_to_c0_busy_cycles,
            "eb_consume_busy_cycles": result.eb_consume_busy_cycles,
            "cpu_not_ready_stall_cycles": result.cpu_not_ready_stall_cycles,
            "boundary_stall_cycles": result.p0p1_boundary_stall_cycles,
            "queue_peaks": {
                "c0": result.c0_queue_peak,
                "cs": result.cs_queue_peak,
                "eb": result.eb_queue_peak,
            },
        })

    baseline = next(row for row in rows if row["case"] == "p0p1=8,eb=8")
    for row in rows:
        row["cycle_delta_vs_baseline"] = row["cycles"] - baseline["cycles"]
        row["cycle_change_percent"] = round(
            100.0 * row["cycle_delta_vs_baseline"] / baseline["cycles"], 3
        )

    return {
        "experiment": "NEXSUS P0/P1-to-C0 and EB-consume interaction matrix",
        "model_scope": "App RAM instruction path only; Data RAM is independent",
        "pages": pages,
        "cases": len(rows),
        "baseline_cycles": baseline["cycles"],
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=32)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = run_sweep(args.pages)
    if args.json:
        print(json.dumps(data, indent=2))
        return

    print(f'{data["experiment"]}: {data["cases"]} cases, {data["pages"]} pages')
    print(f'Baseline: {data["baseline_cycles"]} cycles')
    for row in sorted(data["results"], key=lambda item: item["cycles"]):
        print(
            f'{row["case"]}: {row["cycles"]} cycles '
            f'({row["cycle_change_percent"]:+.3f}%), '
            f'CPU-not-ready={row["cpu_not_ready_stall_cycles"]}, '
            f'P0/P1-busy={row["p0p1_to_c0_busy_cycles"]}, '
            f'EB-busy={row["eb_consume_busy_cycles"]}, '
            f'queues={row["queue_peaks"]}'
        )


if __name__ == "__main__":
    main()
