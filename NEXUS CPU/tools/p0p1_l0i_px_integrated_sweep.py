#!/usr/bin/env python3
"""One-factor and targeted combined sweep for the integrated instruction frontend.

This is a discrete-cycle architecture model, not RTL or silicon measurement.
App RAM instruction fetch is modeled here; Data RAM remains independent.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from p0p1_l0i_px_integrated_sim import Config, IntegratedFrontend


BASELINE = Config()


def config_key(config: Config) -> tuple[int, ...]:
    return (
        config.app_bytes_per_cycle,
        config.app_setup_cycles,
        config.p0p1_to_c0_bytes_per_cycle,
        config.c0_to_cs_bytes_per_cycle,
        config.cs_to_eb_bytes_per_cycle,
        config.eb_consume_bytes_per_cycle,
        config.queue_depth,
    )


def build_cases() -> list[tuple[str, Config]]:
    """Build a compact one-factor-at-a-time sweep plus three interactions."""
    cases: list[tuple[str, Config]] = [("baseline", Config())]
    axes = [
        ("app_bandwidth", "app_bytes_per_cycle", [16, 32, 128]),
        ("app_setup", "app_setup_cycles", [0, 128, 256]),
        ("p0p1_to_c0", "p0p1_to_c0_bytes_per_cycle", [4, 16]),
        ("c0_to_cs", "c0_to_cs_bytes_per_cycle", [8, 32]),
        ("cs_to_eb", "cs_to_eb_bytes_per_cycle", [8, 32]),
        ("eb_consume", "eb_consume_bytes_per_cycle", [4, 16]),
        ("queue_depth", "queue_depth", [1, 2, 8]),
    ]
    seen = {config_key(BASELINE)}
    for label, field, values in axes:
        for value in values:
            config = Config(**{**asdict(BASELINE), field: value})
            key = config_key(config)
            if key not in seen:
                cases.append((f"{label}={value}", config))
                seen.add(key)

    interactions = [
        ("slow_app_and_narrow_downstream", {
            "app_bytes_per_cycle": 16,
            "app_setup_cycles": 128,
            "p0p1_to_c0_bytes_per_cycle": 4,
            "c0_to_cs_bytes_per_cycle": 8,
            "cs_to_eb_bytes_per_cycle": 8,
        }),
        ("slow_consumer_shallow_queues", {
            "eb_consume_bytes_per_cycle": 4,
            "queue_depth": 1,
        }),
        ("fast_frontend_and_deep_queues", {
            "app_bytes_per_cycle": 128,
            "app_setup_cycles": 0,
            "p0p1_to_c0_bytes_per_cycle": 16,
            "c0_to_cs_bytes_per_cycle": 32,
            "cs_to_eb_bytes_per_cycle": 32,
            "eb_consume_bytes_per_cycle": 16,
            "queue_depth": 8,
        }),
    ]
    for label, overrides in interactions:
        config = Config(**{**asdict(BASELINE), **overrides})
        key = config_key(config)
        if key not in seen:
            cases.append((label, config))
            seen.add(key)
    return cases


def summarize(label: str, config: Config, pages: int) -> dict:
    result = IntegratedFrontend(config).run(pages)
    return {
        "case": label,
        "config": {
            "app_bytes_per_cycle": config.app_bytes_per_cycle,
            "app_setup_cycles": config.app_setup_cycles,
            "p0p1_to_c0_bytes_per_cycle": config.p0p1_to_c0_bytes_per_cycle,
            "c0_to_cs_bytes_per_cycle": config.c0_to_cs_bytes_per_cycle,
            "cs_to_eb_bytes_per_cycle": config.cs_to_eb_bytes_per_cycle,
            "eb_consume_bytes_per_cycle": config.eb_consume_bytes_per_cycle,
            "queue_depth": config.queue_depth,
        },
        "cycles": result.cycles,
        "pages_requested": result.pages_requested,
        "pages_retired": result.pages_retired,
        "app_refill_latency": result.app_refill_latency,
        "p0p1_refills": result.p0p1_refills,
        "app_bytes_read": result.app_bytes_read,
        "cold_stall_cycles": result.p0p1_cold_stall_cycles,
        "boundary_stall_cycles": result.p0p1_boundary_stall_cycles,
        "p0p1_to_c0_busy_cycles": result.p0p1_to_c0_busy_cycles,
        "c0_to_cs_busy_cycles": result.c0_to_cs_busy_cycles,
        "cs_to_eb_busy_cycles": result.cs_to_eb_busy_cycles,
        "eb_consume_busy_cycles": result.eb_consume_busy_cycles,
        "cpu_not_ready_stall_cycles": result.cpu_not_ready_stall_cycles,
        "queue_peaks": {
            "c0": result.c0_queue_peak,
            "cs": result.cs_queue_peak,
            "eb": result.eb_queue_peak,
        },
    }


def run_sweep(pages: int = 32) -> dict:
    if pages <= 0:
        raise ValueError("pages must be positive")
    results = [summarize(label, config, pages) for label, config in build_cases()]
    baseline = next(row for row in results if row["case"] == "baseline")
    for row in results:
        row["cycle_delta_vs_baseline"] = row["cycles"] - baseline["cycles"]
        row["cycle_change_percent"] = round(
            100.0 * row["cycle_delta_vs_baseline"] / baseline["cycles"], 3
        )
    return {
        "experiment": "NEXSUS integrated P0/P1-L0I-CS-PX-EB instruction frontend sweep",
        "model_scope": "App RAM instruction path only; Data RAM is independent",
        "pages": pages,
        "cases": len(results),
        "baseline_cycles": baseline["cycles"],
        "results": results,
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
            f'({row["cycle_delta_vs_baseline"]:+d}, '
            f'{row["cycle_change_percent"]:+.3f}%), '
            f'CPU stalls={row["cpu_not_ready_stall_cycles"]}, '
            f'boundary stalls={row["boundary_stall_cycles"]}, '
            f'queues={row["queue_peaks"]}'
        )


if __name__ == "__main__":
    main()
