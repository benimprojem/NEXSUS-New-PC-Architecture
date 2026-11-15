#!/usr/bin/env python3
"""Sweep frontend workload length against balanced middle-stage rates.

Discrete-cycle App RAM instruction-path model only; not RTL or silicon timing.
"""
from __future__ import annotations

import argparse
import json

from p0p1_l0i_px_integrated_sim import Config, IntegratedFrontend


PAGE_COUNTS = (1, 2, 4, 8, 16, 32, 64)
MIDDLE_RATES = (16, 20, 32)


def run_sweep():
    rows = []
    for pages in PAGE_COUNTS:
        for rate in MIDDLE_RATES:
            config = Config(
                app_bytes_per_cycle=64,
                p0p1_to_c0_bytes_per_cycle=16,
                c0_to_cs_bytes_per_cycle=rate,
                cs_to_eb_bytes_per_cycle=rate,
                eb_consume_bytes_per_cycle=16,
                queue_depth=2,
            )
            result = IntegratedFrontend(config).run(pages)
            rows.append({
                "pages": pages,
                "middle_rate_bytes_per_cycle": rate,
                "cycles": result.cycles,
                "pages_requested": result.pages_requested,
                "pages_retired": result.pages_retired,
                "p0p1_refills": result.p0p1_refills,
                "app_bytes_read": result.app_bytes_read,
                "app_refill_latency": result.app_refill_latency,
                "cpu_not_ready_stall_cycles": result.cpu_not_ready_stall_cycles,
                "boundary_stall_cycles": result.p0p1_boundary_stall_cycles,
                "queue_peaks": {
                    "c0": result.c0_queue_peak,
                    "cs": result.cs_queue_peak,
                    "eb": result.eb_queue_peak,
                },
            })

    baseline_by_pages = {
        row["pages"]: row["cycles"]
        for row in rows if row["middle_rate_bytes_per_cycle"] == 16
    }
    for row in rows:
        baseline = baseline_by_pages[row["pages"]]
        row["cycle_delta_vs_16"] = row["cycles"] - baseline
        row["cycle_change_percent_vs_16"] = round(
            100.0 * row["cycle_delta_vs_16"] / baseline, 3
        )

    return {
        "experiment": "NEXSUS frontend workload-length sweep",
        "model_scope": "App RAM instruction path only; Data RAM is independent",
        "page_counts": list(PAGE_COUNTS),
        "middle_rates_bytes_per_cycle": list(MIDDLE_RATES),
        "cases": len(rows),
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = run_sweep()
    if args.json:
        print(json.dumps(data, indent=2))
        return
    print(f'{data["experiment"]}: {data["cases"]} cases')
    for row in data["results"]:
        print(
            f'{row["pages"]:>2} pages @ {row["middle_rate_bytes_per_cycle"]:>2} B/cycle: '
            f'{row["cycles"]:>6} cycles ({row["cycle_change_percent_vs_16"]:+.3f}%) '
            f'refills={row["p0p1_refills"]} stalls={row["cpu_not_ready_stall_cycles"]}'
        )


if __name__ == "__main__":
    main()
