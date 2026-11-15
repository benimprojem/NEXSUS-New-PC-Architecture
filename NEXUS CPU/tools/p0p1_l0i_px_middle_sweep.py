#!/usr/bin/env python3
"""Sweep the two middle instruction-front-end transfer stages.

This is a discrete-cycle architecture model, not RTL or silicon measurement.
App RAM and Data RAM remain independent; only the App RAM instruction path is
modeled. P0/P1->C0 and EB consumption are held at 16 B/cycle.
"""
from __future__ import annotations

import argparse
import json

from p0p1_l0i_px_integrated_sim import Config, IntegratedFrontend


RATES = (12, 16, 20, 24, 32)


def build_cases():
    cases = []
    for c0_cs in RATES:
        for cs_eb in RATES:
            cases.append((
                f"c0_cs={c0_cs}_cs_eb={cs_eb}",
                Config(
                    app_bytes_per_cycle=64,
                    p0p1_to_c0_bytes_per_cycle=16,
                    c0_to_cs_bytes_per_cycle=c0_cs,
                    cs_to_eb_bytes_per_cycle=cs_eb,
                    eb_consume_bytes_per_cycle=16,
                    queue_depth=2,
                ),
            ))
    return cases


def run_sweep(pages=32):
    if pages <= 0:
        raise ValueError("pages must be positive")
    rows = []
    for name, config in build_cases():
        result = IntegratedFrontend(config).run(pages)
        rows.append({
            "case": name,
            "config": {
                "app_bytes_per_cycle": config.app_bytes_per_cycle,
                "p0p1_to_c0_bytes_per_cycle": config.p0p1_to_c0_bytes_per_cycle,
                "c0_to_cs_bytes_per_cycle": config.c0_to_cs_bytes_per_cycle,
                "cs_to_eb_bytes_per_cycle": config.cs_to_eb_bytes_per_cycle,
                "eb_consume_bytes_per_cycle": config.eb_consume_bytes_per_cycle,
                "queue_depth": config.queue_depth,
            },
            "cycles": result.cycles,
            "pages_retired": result.pages_retired,
            "app_refill_latency": result.app_refill_latency,
            "p0p1_busy_cycles": result.p0p1_to_c0_busy_cycles,
            "eb_consume_busy_cycles": result.eb_consume_busy_cycles,
            "cpu_not_ready_stall_cycles": result.cpu_not_ready_stall_cycles,
            "boundary_stall_cycles": result.p0p1_boundary_stall_cycles,
            "queue_peaks": {
                "c0": result.c0_queue_peak,
                "cs": result.cs_queue_peak,
                "eb": result.eb_queue_peak,
            },
        })
    baseline = next(row for row in rows if row["case"] == "c0_cs=16_cs_eb=16")
    for row in rows:
        row["cycle_delta_vs_16_16"] = row["cycles"] - baseline["cycles"]
        row["cycle_change_percent_vs_16_16"] = round(
            100.0 * row["cycle_delta_vs_16_16"] / baseline["cycles"], 3
        )
    return {
        "experiment": "NEXSUS middle frontend-stage rate sweep",
        "model_scope": "App RAM instruction path only; Data RAM is independent",
        "pages": pages,
        "cases": len(rows),
        "baseline_cycles": baseline["cycles"],
        "baseline": baseline,
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=32)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = run_sweep(args.pages)
    if args.json:
        print(json.dumps(data, indent=2))
        return
    print(f'{data["experiment"]}: {data["cases"]} cases, {data["pages"]} pages')
    print(f'16/16 baseline: {data["baseline_cycles"]} cycles')
    for row in sorted(data["results"], key=lambda item: item["cycles"]):
        print(f'{row["case"]}: {row["cycles"]} cycles '
              f'({row["cycle_change_percent_vs_16_16"]:+.3f}%) '
              f'stalls={row["cpu_not_ready_stall_cycles"]} '
              f'queues={row["queue_peaks"]}')


if __name__ == "__main__":
    main()
