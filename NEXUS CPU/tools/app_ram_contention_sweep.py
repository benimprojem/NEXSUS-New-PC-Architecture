#!/usr/bin/env python3
"""App RAM correct-target versus wrong-path request contention sweep.

Uses the existing AppRamController arbitration and bank/bus timing model.
This is a discrete-cycle architecture experiment, not RTL or silicon data.
"""
from __future__ import annotations

import argparse
import json

from cpu_comparison_sim import AppRamController


POLICIES = ("equal", "target_first", "speculative_first")


def _case(burst_bytes: int, relation: str, policy: str) -> dict:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy: {policy}")
    target_address = 0
    if relation == "same_banks":
        speculative_address = 0
    elif relation == "disjoint_banks":
        if burst_bytes > 32:
            raise ValueError("disjoint bank sets are only defined for bursts <= 32 bytes")
        speculative_address = burst_bytes
    elif relation == "all_banks":
        if burst_bytes < 64:
            raise ValueError("all_banks requires at least 64 bytes with the default geometry")
        speculative_address = 0
    else:
        raise ValueError(f"unknown bank relation: {relation}")

    target_priority = 1 if policy == "target_first" else 0
    speculative_priority = 1 if policy == "speculative_first" else 0
    controller = AppRamController(
        bank_count=8,
        beat_bytes=8,
        bytes_per_cycle=32,
        first_beat_latency=40,
        beat_interval=1,
        max_outstanding=8,
    )
    admitted = controller.reserve_batch(0, [
        {
            "id": "z-correct-target",
            "core": 0,
            "address": target_address,
            "bytes": burst_bytes,
            "priority": target_priority,
        },
        {
            "id": "a-wrong-path",
            "core": 0,
            "address": speculative_address,
            "bytes": burst_bytes,
            "priority": speculative_priority,
        },
    ])
    if not all(admitted[key]["accepted"] for key in admitted):
        raise AssertionError("two-request experiment unexpectedly rejected a request")
    target_ready = admitted["z-correct-target"]["ready_cycle"]
    speculative_ready = admitted["a-wrong-path"]["ready_cycle"]
    return {
        "burst_bytes": burst_bytes,
        "bank_relation": relation,
        "policy": policy,
        "target_ready_cycle": target_ready,
        "speculative_ready_cycle": speculative_ready,
        "target_delay_vs_first_service": target_ready - min(target_ready, speculative_ready),
        "target_priority": target_priority,
        "speculative_priority": speculative_priority,
        "bank_conflicts": controller.bank_conflicts,
        "transferred_bytes": controller.transferred_bytes,
        "requests_accepted": controller.accepted,
        "assumption": (
            "Same-cycle requests are admitted in priority order; each request "
            "reserves its bank beats and aggregate App RAM bus bytes."
        ),
    }


def run_contention_sweep() -> dict:
    cases = []
    for burst in (16, 32):
        for relation in ("same_banks", "disjoint_banks"):
            for policy in POLICIES:
                cases.append(_case(burst, relation, policy))
    for policy in POLICIES:
        cases.append(_case(2048, "all_banks", policy))
    return {
        "experiment": "App RAM correct-target / wrong-path contention",
        "cases": len(cases),
        "controller_geometry": {
            "banks": 8,
            "beat_bytes": 8,
            "aggregate_bytes_per_cycle": 32,
            "first_beat_latency_cycles": 40,
            "max_outstanding": 8,
        },
        "results": cases,
        "limitations": [
            "This isolates two same-cycle requests and does not model a full multi-core request arrival stream.",
            "The 2048-byte case represents a 2 KiB instruction-page transfer and touches all eight banks.",
            "Priority changes admission order; it does not preempt a request already admitted.",
            "App RAM remains independent of Data RAM.",
            "All timings are simulator estimates, not hardware measurements.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_contention_sweep()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["experiment"])
        for row in result["results"]:
            print(
                f'{row["burst_bytes"]:>4} B {row["bank_relation"]:<13} '
                f'{row["policy"]:<17} target={row["target_ready_cycle"]:>4} '
                f'speculative={row["speculative_ready_cycle"]:>4} '
                f'bank_conflicts={row["bank_conflicts"]}'
            )


if __name__ == "__main__":
    main()
