#!/usr/bin/env python3
"""Sweep P0/P1 command-buffer refill and consumption parameters (behavioral model)."""
from __future__ import annotations
import json
from itertools import product
from p0p1_command_buffer_sim import P0P1


def run_sweep():
    rows = []
    for kb, app_bpc, setup, consume_bpc in product(
            (4, 8, 16), (8, 16, 32, 64), (0, 40, 80, 128, 256), (8, 16, 32)):
        # Keep configurations divisible so block consumption is integral.
        if kb * 1024 % consume_bpc:
            continue
        model = P0P1(kb * 1024, app_bpc, setup, consume_bpc)
        result = model.run(16)
        rows.append({
            "buffer_kb": kb, "app_bytes_per_cycle": app_bpc,
            "setup_cycles": setup, "consume_bytes_per_cycle": consume_bpc,
            "transfer_cycles": model.transfer_cycles,
            "refill_latency_cycles": model.refill_latency,
            "block_consume_cycles": model.consume_cycles,
            "boundary_stalls": result.boundary_stalls,
            "overlap_cycles": result.overlap_cycles,
            "refills": result.refill_count,
            "refill_bytes": result.refill_bytes,
            "cycles": result.cycles,
            "starvation_after_cold_fill": result.boundary_stalls > model.refill_latency,
        })
    return {"experiment": "P0/P1 refill latency and throughput sweep",
            "blocks": 16, "cases": len(rows), "results": rows}


if __name__ == "__main__":
    print(json.dumps(run_sweep(), indent=2))
