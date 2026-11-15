#!/usr/bin/env python3
"""Small behavioral model of 8-KiB P0/P1 command ping-pong buffers.

This is an architecture-level timing model, not RTL or silicon timing.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import argparse
import json
import math


@dataclass
class Result:
    cycles: int
    blocks_consumed: int
    refill_count: int
    refill_bytes: int
    boundary_stalls: int
    overlap_cycles: int
    max_refill_wait: int


class P0P1:
    def __init__(self, block_bytes=8192, app_bytes_per_cycle=64,
                 setup_latency=40, consume_bytes_per_cycle=8):
        if min(block_bytes, app_bytes_per_cycle, consume_bytes_per_cycle) <= 0 or setup_latency < 0:
            raise ValueError("buffer/throughput values must be positive and setup latency nonnegative")
        if block_bytes % consume_bytes_per_cycle:
            raise ValueError("block size must be divisible by consumer width")
        self.block_bytes = block_bytes
        self.transfer_cycles = math.ceil(block_bytes / app_bytes_per_cycle)
        self.refill_latency = setup_latency + self.transfer_cycles
        self.consume_cycles = block_bytes // consume_bytes_per_cycle

    def run(self, blocks=16):
        if blocks <= 0:
            raise ValueError("blocks must be positive")
        ready = [None, None]  # logical block resident in each buffer
        pending = [None, None] # (logical block, ready cycle)
        active = 0
        cycle = 0
        consumed = 0
        refills = 0
        stalls = overlap = max_wait = 0

        def request(slot, block, now):
            nonlocal refills
            if pending[slot] is not None or ready[slot] is not None:
                raise RuntimeError("refill target is not free")
            pending[slot] = (block, now + self.refill_latency)
            refills += 1

        request(0, 0, cycle)
        while consumed < blocks:
            # Complete both refill engines at this cycle.
            for slot in range(2):
                if pending[slot] and pending[slot][1] <= cycle:
                    ready[slot] = pending[slot][0]
                    pending[slot] = None

            if ready[active] != consumed:
                stalls += 1
                wait_start = cycle
                cycle += 1
                max_wait = max(max_wait, cycle - wait_start)
                continue

            # Current block executes. Start next-block refill in inactive buffer.
            inactive = 1 - active
            nxt = consumed + 1
            if nxt < blocks and ready[inactive] is None and pending[inactive] is None:
                request(inactive, nxt, cycle)
            if pending[inactive] is not None:
                overlap += 1

            cycle += self.consume_cycles
            ready[active] = None
            consumed += 1
            active = inactive
            # If the next block was not prefetched, demand refill into active slot.
            if consumed < blocks and ready[active] != consumed and pending[active] is None:
                request(active, consumed, cycle)

        return Result(cycle, consumed, refills, refills * self.block_bytes,
                      stalls, overlap, max_wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, default=16)
    ap.add_argument("--buffer-kb", type=int, default=8)
    ap.add_argument("--app-bpc", type=int, default=64)
    ap.add_argument("--setup", type=int, default=40)
    ap.add_argument("--consume-bpc", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = asdict(P0P1(args.buffer_kb * 1024, args.app_bpc,
                          args.setup, args.consume_bpc).run(args.blocks))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
