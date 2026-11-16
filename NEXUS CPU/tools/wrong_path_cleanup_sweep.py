#!/usr/bin/env python3
"""Sweep wrong-path queue cleanup and P0/P1 target-slot reuse.

This is a deliberately small control/occupancy model. Queue entries are
invalidated at branch resolution; the target refill may overlap resolution
only when its destination P0/P1 slot is not occupied by wrong-path work.
No byte-by-byte clearing is assumed: invalidation is metadata work.
"""
import argparse
import json
import math

from p0p1_branch_redirect_sim import simulate_integrated_redirect

OVERLAPS = (0, 64, 128, 256, 512, 630)
FLUSH_RATES = (1, 2, 4)  # queued pages invalidated per cycle
SLOT_INVALIDATE_CYCLES = (0, 1, 2, 4)


def run_cleanup_sweep(
    overlaps=OVERLAPS,
    flush_rates=FLUSH_RATES,
    slot_invalidate_cycles=SLOT_INVALIDATE_CYCLES,
    branch_penalty=8,
):
    if branch_penalty < 0:
        raise ValueError("branch_penalty must be nonnegative")
    base = simulate_integrated_redirect()
    resolution = base.target_ready_cycle - base.target_delivery_latency
    delivery = base.target_delivery_latency
    queued_pages = base.queued_wrong_path_pages_flushed
    rows = []
    for conflict in (False, True):
        for flush_rate in flush_rates:
            if flush_rate <= 0:
                raise ValueError("flush rate must be positive")
            flush_cycles = math.ceil(queued_pages / flush_rate)
            for invalidate_cycles in slot_invalidate_cycles:
                if invalidate_cycles < 0:
                    raise ValueError("slot invalidation latency must be nonnegative")
                # Queue flush and P0/P1 slot-tag invalidation use independent
                # control resources, so cleanup completes at the slower one.
                cleanup_cycles = max(flush_cycles, int(invalidate_cycles))
                slot_release = resolution + cleanup_cycles if conflict else None
                for overlap in overlaps:
                    if overlap < 0:
                        raise ValueError("overlap must be nonnegative")
                    requested_start = resolution - min(int(overlap), delivery)
                    # Without a destination-slot conflict, speculative fetch
                    # starts at its requested lead time. With a conflict, the
                    # occupied slot imposes a hard lower bound on fetch start.
                    fetch_start = (
                        max(requested_start, slot_release)
                        if conflict else requested_start
                    )
                    actual_overlap = min(delivery, max(0, resolution - fetch_start))
                    target_fetch_done = fetch_start + delivery
                    target_ready = max(
                        resolution + branch_penalty,
                        target_fetch_done,
                    )
                    rows.append({
                        "target_slot_conflict": conflict,
                        "requested_overlap_cycles": int(overlap),
                        "actual_overlap_cycles": actual_overlap,
                        "flush_pages_per_cycle": int(flush_rate),
                        "queued_wrong_path_pages": queued_pages,
                        "queue_flush_cycles": flush_cycles,
                        "slot_invalidate_cycles": int(invalidate_cycles),
                        "slot_cleanup_cycles": cleanup_cycles,
                        "slot_release_cycle": slot_release,
                        "target_fetch_start_cycle": fetch_start,
                        "target_ready_cycle": target_ready,
                        "remaining_target_wait_after_resolution": max(
                            0, target_ready - (resolution + branch_penalty)
                        ),
                        "wrong_path_block_bytes_invalidated":
                            base.p0p1_wrong_path_block_discarded_bytes,
                        "wrong_path_queued_bytes_invalidated":
                            base.queued_wrong_path_bytes_flushed,
                    })
    return {
        "experiment": "NEXSUS wrong-path cleanup and P0/P1 slot reuse",
        "branch_resolution_cycle": resolution,
        "branch_penalty_cycles": branch_penalty,
        "target_delivery_cycles": delivery,
        "cases": len(rows),
        "results": rows,
        "assumptions": (
            "Wrong-path queue entries and slot tags are invalidated starting at "
            "branch resolution. Queue flush and slot-tag invalidation are modeled "
            "as independent control work; slot reuse is blocked only when the "
            "target maps to the occupied wrong-path slot. No payload bytes are "
            "physically cleared. This isolates slot-conflict sensitivity; it does "
            "not model App RAM bandwidth contention, BTB lead-time errors, or "
            "partial refill cancellation. Architecture-level estimate, not RTL "
            "or silicon timing."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_cleanup_sweep()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("NEXSUS WRONG-PATH CLEANUP / SLOT REUSE SWEEP")
        for conflict in (False, True):
            selected = [r for r in result["results"]
                        if r["target_slot_conflict"] is conflict
                        and r["flush_pages_per_cycle"] == 2
                        and r["slot_invalidate_cycles"] == 1]
            for row in selected:
                print(
                    f"conflict={conflict} overlap={row['requested_overlap_cycles']} "
                    f"actual={row['actual_overlap_cycles']} "
                    f"cleanup={row['slot_cleanup_cycles']} "
                    f"ready={row['target_ready_cycle']}"
                )


if __name__ == "__main__":
    main()
