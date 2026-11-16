#!/usr/bin/env python3
"""Multi-core App RAM target/speculative arbitration and fairness sweep.

Discrete-cycle model using AppRamController; not RTL or silicon data.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from cpu_comparison_sim import AppRamController

POLICIES = ("equal", "target_first", "target_first_aging")
CORE_COUNT = 8
PAGE_BYTES = 2048
AGING_LIMIT = 128


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def _arrivals() -> dict[int, list[dict]]:
    events: dict[int, list[dict]] = defaultdict(list)
    # Each core has four correct-target page fetches and sixteen wrong-path
    # speculative page fetches. Both streams are finite and deterministic.
    for core in range(CORE_COUNT):
        for index, cycle in enumerate((0, 160, 320, 480)):
            events[cycle].append({
                "id": f"target-c{core}-p{index}", "core": core,
                "kind": "target", "arrival_cycle": cycle,
                "address": (core * 0x20000) + (index * PAGE_BYTES),
                "bytes": PAGE_BYTES,
            })
        for index in range(16):
            cycle = index * 32
            events[cycle].append({
                "id": f"spec-c{core}-p{index}", "core": core,
                "kind": "speculative", "arrival_cycle": cycle,
                "address": (core * 0x20000) + 0x10000 + (index * PAGE_BYTES),
                "bytes": PAGE_BYTES,
            })
    return dict(events)


def _priority(request: dict, cycle: int, policy: str) -> int:
    if policy == "equal":
        return 0
    if policy == "target_first":
        return 1 if request["kind"] == "target" else 0
    age = cycle - request["arrival_cycle"]
    if age >= AGING_LIMIT:
        return 2
    return 1 if request["kind"] == "target" else 0


def _run(policy: str) -> dict:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy: {policy}")
    controller = AppRamController(
        bank_count=8, beat_bytes=8, bytes_per_cycle=64,
        first_beat_latency=40, beat_interval=1, max_outstanding=8,
    )
    events = _arrivals()
    pending: list[dict] = []
    admitted: dict[str, dict] = {}
    cycle = 0
    max_cycles = 30000
    while cycle < max_cycles:
        pending.extend(events.get(cycle, []))
        batch = []
        for request in pending:
            item = dict(request)
            item["priority"] = _priority(request, cycle, policy)
            batch.append(item)
        outcomes = controller.reserve_batch(cycle, batch)
        next_pending = []
        for request in pending:
            outcome = outcomes.get(request["id"], {"accepted": False})
            if outcome["accepted"]:
                admitted[request["id"]] = {
                    "kind": request["kind"],
                    "core": request["core"],
                    "arrival_cycle": request["arrival_cycle"],
                    "admission_cycle": cycle,
                    "ready_cycle": outcome["ready_cycle"],
                    "admission_wait": cycle - request["arrival_cycle"],
                    "completion_latency": outcome["ready_cycle"] - request["arrival_cycle"],
                }
            else:
                next_pending.append(request)
        pending = next_pending
        controller.complete(cycle)
        future_events = any(event_cycle > cycle for event_cycle in events)
        if not future_events and not pending and not controller.inflight:
            break
        cycle += 1
    else:
        raise AssertionError(f"{policy}: simulation exceeded {max_cycles} cycles")

    expected = CORE_COUNT * (4 + 16)
    if len(admitted) != expected:
        raise AssertionError(f"{policy}: admitted {len(admitted)} of {expected} requests")
    per_core = {}
    for core in range(CORE_COUNT):
        core_rows = [row for row in admitted.values() if row["core"] == core]
        core_target = [row for row in core_rows if row["kind"] == "target"]
        core_speculative = [row for row in core_rows if row["kind"] == "speculative"]
        core_latencies = [row["completion_latency"] for row in core_rows]
        per_core[str(core)] = {
            "requests": len(core_rows),
            "target_requests": len(core_target),
            "speculative_requests": len(core_speculative),
            "bytes_transferred": len(core_rows) * PAGE_BYTES,
            "mean_completion_latency_cycles": round(
                sum(core_latencies) / len(core_latencies), 2
            ),
            "max_completion_latency_cycles": max(core_latencies),
        }

    core_bytes = [row["bytes_transferred"] for row in per_core.values()]
    core_mean_latencies = [
        row["mean_completion_latency_cycles"] for row in per_core.values()
    ]
    core_fairness = {
        "min_bytes_per_core": min(core_bytes),
        "max_bytes_per_core": max(core_bytes),
        "bytes_spread": max(core_bytes) - min(core_bytes),
        "min_mean_latency_cycles": min(core_mean_latencies),
        "max_mean_latency_cycles": max(core_mean_latencies),
        "mean_latency_spread_cycles": round(
            max(core_mean_latencies) - min(core_mean_latencies), 2
        ),
        "equal_bytes_across_cores": len(set(core_bytes)) == 1,
    }

    groups = {}
    for kind in ("target", "speculative"):
        rows = [row for row in admitted.values() if row["kind"] == kind]
        waits = [row["admission_wait"] for row in rows]
        latencies = [row["completion_latency"] for row in rows]
        groups[kind] = {
            "requests": len(rows),
            "mean_admission_wait_cycles": round(sum(waits) / len(waits), 2),
            "p95_admission_wait_cycles": _percentile(waits, 0.95),
            "max_admission_wait_cycles": max(waits),
            "mean_completion_latency_cycles": round(sum(latencies) / len(latencies), 2),
            "max_completion_latency_cycles": max(latencies),
        }
    return {
        "policy": policy,
        "cores": CORE_COUNT,
        "target_requests": CORE_COUNT * 4,
        "speculative_requests": CORE_COUNT * 16,
        "total_requests_admitted": len(admitted),
        "total_bytes_transferred": controller.transferred_bytes,
        "queue_full_retries": controller.rejected_queue_full,
        "bank_conflicts": controller.bank_conflicts,
        "last_completion_cycle": max(row["ready_cycle"] for row in admitted.values()),
        "per_core": per_core,
        "core_fairness": core_fairness,
        "by_request_class": groups,
    }


def run_sweep() -> dict:
    results = {policy: _run(policy) for policy in POLICIES}
    return {
        "experiment": "Eight-core App RAM target/speculative arbitration fairness",
        "policies": list(POLICIES),
        "workload": {
            "cores": CORE_COUNT, "page_bytes": PAGE_BYTES,
            "target_pages_per_core": 4, "speculative_pages_per_core": 16,
            "target_arrival_cycles": [0, 160, 320, 480],
            "speculative_arrival_interval_cycles": 32,
            "controller": {
                "banks": 8, "beat_bytes": 8, "per_core_bytes_per_cycle": 64,
                "core_count": CORE_COUNT,
                "aggregate_bytes_per_cycle": 64 * CORE_COUNT,
                "first_beat_latency_cycles": 40, "max_outstanding": 8,
            },
        },
        "aging_policy": {
            "description": "Target requests receive priority 1; speculative requests priority 0. Any request waiting at least 128 cycles is promoted to priority 2, allowing old work from either class to compete ahead of fresh work.",
            "age_threshold_cycles": AGING_LIMIT,
        },
        "results": results,
        "limitations": [
            "Finite synthetic eight-core request stream; not a full frontend/branch execution model.",
            "Each core has an independent 64-B/cycle port and local banks/queue; priority cannot preempt admitted work on that core.",
            "No coherence, cancellation timing, or actual branch-resolution feedback is modeled.",
            "App RAM is independent of Data RAM.",
            "All results are discrete-cycle simulator estimates, not hardware measurements.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_sweep()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["experiment"])
        for policy, row in result["results"].items():
            target = row["by_request_class"]["target"]
            spec = row["by_request_class"]["speculative"]
            print(
                f"{policy:20} cycles={row['last_completion_cycle']:>6} "
                f"target_wait={target['mean_admission_wait_cycles']:>8} "
                f"spec_wait={spec['mean_admission_wait_cycles']:>8} "
                f"spec_max={spec['max_admission_wait_cycles']:>6} "
                f"retries={row['queue_full_retries']}"
            )


if __name__ == "__main__":
    main()
