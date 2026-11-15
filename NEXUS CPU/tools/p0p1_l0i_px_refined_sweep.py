#!/usr/bin/env python3
"""Refine the P0/P1-to-C0 and EB-consume operating point.

Discrete-cycle model only; not RTL or silicon measurements. This models the
App RAM instruction path. Data RAM remains an independent path/controller.
"""
from __future__ import annotations

import argparse
import json

from p0p1_l0i_px_integrated_sim import Config, IntegratedFrontend


RATE_POINTS = (12, 14, 16, 18, 20)
APP_BANDWIDTHS = (32, 48, 64, 128)
QUEUE_DEPTHS = (1, 2, 4, 8)


def _row(label: str, cfg: Config, pages: int) -> dict:
    result = IntegratedFrontend(cfg).run(pages)
    return {
        "case": label,
        "config": {
            "app_bytes_per_cycle": cfg.app_bytes_per_cycle,
            "app_setup_cycles": cfg.app_setup_cycles,
            "p0p1_to_c0_bytes_per_cycle": cfg.p0p1_to_c0_bytes_per_cycle,
            "c0_to_cs_bytes_per_cycle": cfg.c0_to_cs_bytes_per_cycle,
            "cs_to_eb_bytes_per_cycle": cfg.cs_to_eb_bytes_per_cycle,
            "eb_consume_bytes_per_cycle": cfg.eb_consume_bytes_per_cycle,
            "queue_depth": cfg.queue_depth,
        },
        "cycles": result.cycles,
        "pages_retired": result.pages_retired,
        "app_refill_latency": result.app_refill_latency,
        "p0p1_to_c0_busy_cycles": result.p0p1_to_c0_busy_cycles,
        "eb_consume_busy_cycles": result.eb_consume_busy_cycles,
        "cpu_not_ready_stall_cycles": result.cpu_not_ready_stall_cycles,
        "boundary_stall_cycles": result.p0p1_boundary_stall_cycles,
        "queue_peaks": {
            "c0": result.c0_queue_peak,
            "cs": result.cs_queue_peak,
            "eb": result.eb_queue_peak,
        },
    }


def build_cases() -> list[tuple[str, Config]]:
    cases: list[tuple[str, Config]] = []

    # Fine-grained rate matrix around the observed 16 B/cycle knee.
    for p0_rate in RATE_POINTS:
        for eb_rate in RATE_POINTS:
            cases.append((
                f"rates_p0={p0_rate}_eb={eb_rate}",
                Config(
                    p0p1_to_c0_bytes_per_cycle=p0_rate,
                    eb_consume_bytes_per_cycle=eb_rate,
                    queue_depth=2,
                ),
            ))

    # App RAM bandwidth sensitivity with both downstream bottlenecks balanced.
    for app_rate in APP_BANDWIDTHS:
        cases.append((
            f"app_bandwidth={app_rate}_balanced16",
            Config(
                app_bytes_per_cycle=app_rate,
                p0p1_to_c0_bytes_per_cycle=16,
                eb_consume_bytes_per_cycle=16,
                queue_depth=2,
            ),
        ))

    # Queue depth sensitivity at the proposed balanced operating point.
    for depth in QUEUE_DEPTHS:
        cases.append((
            f"balanced16_queue={depth}",
            Config(
                p0p1_to_c0_bytes_per_cycle=16,
                eb_consume_bytes_per_cycle=16,
                queue_depth=depth,
            ),
        ))

    return cases


def run_sweep(pages: int = 32) -> dict:
    if pages <= 0:
        raise ValueError("pages must be positive")

    rows = [_row(label, cfg, pages) for label, cfg in build_cases()]
    baseline = _row(
        "baseline_8_8",
        Config(
            p0p1_to_c0_bytes_per_cycle=8,
            eb_consume_bytes_per_cycle=8,
            queue_depth=4,
        ),
        pages,
    )
    for row in [baseline, *rows]:
        row["cycle_delta_vs_baseline"] = row["cycles"] - baseline["cycles"]
        row["cycle_change_percent"] = round(
            100.0 * row["cycle_delta_vs_baseline"] / baseline["cycles"], 3
        )

    return {
        "experiment": "NEXSUS refined frontend operating-point sweep",
        "model_scope": "App RAM instruction path only; Data RAM is independent",
        "pages": pages,
        "cases": len(rows),
        "baseline_cycles": baseline["cycles"],
        "baseline": baseline,
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
            f'App refill={row["app_refill_latency"]}, '
            f'CPU-not-ready={row["cpu_not_ready_stall_cycles"]}, '
            f'queues={row["queue_peaks"]}'
        )


if __name__ == "__main__":
    main()
