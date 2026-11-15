#!/usr/bin/env python3
"""Sweep speculative target-page prefetch overlap for a branch redirect.

The model exposes overlap as an explicit assumption; it does not claim that
the predictor/BTB or memory system physically achieves the selected lead time.
"""
import argparse
import json

from p0p1_branch_redirect_sim import simulate_integrated_redirect

OVERLAP_CYCLES = (0, 64, 128, 256, 512, 630)


def run_target_prefetch_sweep(overlaps=OVERLAP_CYCLES, branch_penalty=8):
    if branch_penalty < 0:
        raise ValueError("branch_penalty must be nonnegative")
    base = simulate_integrated_redirect()
    resolution = base.target_ready_cycle - base.target_delivery_latency
    rows = {}
    for overlap in overlaps:
        if overlap < 0:
            raise ValueError("prefetch overlap must be nonnegative")
        hidden = min(int(overlap), base.target_delivery_latency)
        target_wait = base.target_delivery_latency - hidden
        ready = resolution + branch_penalty + target_wait
        rows[str(overlap)] = {
            "overlap_cycles": int(overlap),
            "hidden_delivery_cycles": hidden,
            "remaining_target_wait_cycles": target_wait,
            "branch_resolution_cycle": resolution,
            "branch_penalty_cycles": branch_penalty,
            "target_ready_cycle": ready,
            "cycles_saved_vs_no_prefetch": (
                resolution + branch_penalty + base.target_delivery_latency - ready
            ),
            "wrong_path_block_bytes_discarded": base.p0p1_wrong_path_block_discarded_bytes,
            "wrong_path_queued_bytes_flushed": base.queued_wrong_path_bytes_flushed,
        }
    return {
        "experiment": "NEXSUS speculative target-page prefetch overlap",
        "serialized_target_delivery_cycles": base.target_delivery_latency,
        "branch_penalty_cycles": branch_penalty,
        "branch_resolution_cycle": resolution,
        "results": rows,
        "assumptions": (
            "Target address is assumed known early enough to start a speculative "
            "fetch. overlap_cycles is an explicit idealized amount of target-path "
            "work hidden before branch resolution; wrong-path cancellation cost, "
            "bandwidth contention, and partial-refill cancellation are not modeled. "
            "Architecture-level estimate, not RTL or silicon timing."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_target_prefetch_sweep()
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print("NEXSUS TARGET PREFETCH OVERLAP SWEEP")
    for overlap, row in result["results"].items():
        print(
            f"overlap={overlap}: target-ready={row['target_ready_cycle']} "
            f"saved={row['cycles_saved_vs_no_prefetch']}"
        )


if __name__ == "__main__":
    main()
