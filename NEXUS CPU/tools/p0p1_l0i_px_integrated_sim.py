#!/usr/bin/env python3
"""Integrated P0/P1 -> C0/L0I -> CS/PX -> EB code-stream model.

Architecture-level discrete-cycle model only; not RTL or silicon measurements.
One sequential instruction stream is modeled. A P0/P1 block is 8 KiB (four
2 KiB L0I pages). App RAM and Data RAM are intentionally separate: this model
contains only the App RAM instruction-fetch path; Data RAM is not routed here.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import argparse
import json
import math


@dataclass
class Config:
    block_bytes: int = 8192
    page_bytes: int = 2048
    app_bytes_per_cycle: int = 64
    app_setup_cycles: int = 40
    p0p1_to_c0_bytes_per_cycle: int = 8
    c0_to_cs_bytes_per_cycle: int = 16
    cs_to_eb_bytes_per_cycle: int = 16
    eb_consume_bytes_per_cycle: int = 8
    queue_depth: int = 4
    max_cycles: int = 10_000_000


@dataclass
class Result:
    cycles: int
    pages_requested: int
    pages_retired: int
    p0p1_refills: int
    app_bytes_read: int
    app_refill_latency: int
    p0p1_cold_stall_cycles: int
    p0p1_boundary_stall_cycles: int
    p0p1_to_c0_busy_cycles: int
    c0_to_cs_busy_cycles: int
    cs_to_eb_busy_cycles: int
    eb_consume_busy_cycles: int
    cpu_not_ready_stall_cycles: int
    c0_queue_peak: int
    cs_queue_peak: int
    eb_queue_peak: int
    timeline: list[dict]


class IntegratedFrontend:
    def __init__(self, config: Config = Config()):
        self.c = config
        self._validate()

    def _validate(self):
        c = self.c
        if min(c.block_bytes, c.page_bytes, c.app_bytes_per_cycle,
               c.p0p1_to_c0_bytes_per_cycle, c.c0_to_cs_bytes_per_cycle,
               c.cs_to_eb_bytes_per_cycle, c.eb_consume_bytes_per_cycle,
               c.queue_depth, c.max_cycles) <= 0 or c.app_setup_cycles < 0:
            raise ValueError("sizes, rates, queue depth and max_cycles must be positive; setup must be nonnegative")
        if c.block_bytes % c.page_bytes:
            raise ValueError("P0/P1 block size must be divisible by L0I page size")
        if c.page_bytes % 8 or c.block_bytes % 8:
            raise ValueError("instruction page and block sizes must be 8-byte aligned")

    def run(self, pages_requested: int = 32) -> Result:
        if pages_requested <= 0:
            raise ValueError("pages_requested must be positive")
        c = self.c
        pages_per_block = c.block_bytes // c.page_bytes
        blocks_total = math.ceil(pages_requested / pages_per_block)
        refill_transfer = math.ceil(c.block_bytes / c.app_bytes_per_cycle)
        refill_latency = c.app_setup_cycles + refill_transfer

        # P0/P1 ping-pong slots contain whole command blocks.
        p0p1 = [None, None]  # block index or None
        app_active = None   # (block index, target slot, completion cycle)
        next_refill = 0
        current_page = 0
        p0_active = None    # (page index, completion cycle)
        c0_q, cs_q, eb_q = [], [], []
        c0_active = None
        cs_active = None
        eb_active = None
        eb_banks = [None, None]  # (page index, ready cycle); CPU consumes sequentially
        cpu_active = None        # (page index, completion cycle)
        retired = 0
        timeline = []
        metrics = dict(p0p1_refills=0, app_bytes_read=0,
            p0p1_cold_stall_cycles=0, p0p1_boundary_stall_cycles=0,
            p0p1_to_c0_busy_cycles=0, c0_to_cs_busy_cycles=0,
            cs_to_eb_busy_cycles=0, eb_consume_busy_cycles=0,
            cpu_not_ready_stall_cycles=0, c0_queue_peak=0,
            cs_queue_peak=0, eb_queue_peak=0)

        def duration(nbytes, rate):
            return math.ceil(nbytes / rate)

        for cycle in range(c.max_cycles):
            # CPU consumes the oldest ready EB page, one page at a time.
            if cpu_active is not None and cycle >= cpu_active[1]:
                page = cpu_active[0]
                timeline.append({"cycle": cycle, "event": "PAGE_RETIRED", "page": page})
                retired += 1
                cpu_active = None
            if cpu_active is None and retired < pages_requested:
                ready = [(i, item) for i, item in enumerate(eb_banks)
                         if item is not None and item[0] == retired]
                if ready:
                    slot, item = ready[0]
                    eb_banks[slot] = None
                    cpu_active = (item[0], cycle + duration(c.page_bytes, c.eb_consume_bytes_per_cycle))
                    metrics["eb_consume_busy_cycles"] += duration(c.page_bytes, c.eb_consume_bytes_per_cycle)
                    timeline.append({"cycle": cycle, "event": "EB_CONSUME_START", "page": item[0], "bank": slot})
                else:
                    metrics["cpu_not_ready_stall_cycles"] += 1

            # CS/PX -> EB stage.
            if eb_active is not None and cycle >= eb_active[1]:
                page = eb_active[0]
                free = next((i for i, item in enumerate(eb_banks) if item is None), None)
                if free is not None:
                    eb_banks[free] = (page, cycle)
                    timeline.append({"cycle": cycle, "event": "EB_READY", "page": page, "bank": free})
                    eb_active = None
            if eb_active is None and eb_q:
                free = next((i for i, item in enumerate(eb_banks) if item is None), None)
                if free is not None:
                    page = eb_q.pop(0)
                    d = duration(c.page_bytes, c.cs_to_eb_bytes_per_cycle)
                    eb_active = (page, cycle + d)
                    metrics["cs_to_eb_busy_cycles"] += d
                    timeline.append({"cycle": cycle, "event": "CS_EB_START", "page": page})

            # C0/L0I -> CS/PX stage.
            if cs_active is not None and cycle >= cs_active[1] and len(eb_q) < c.queue_depth:
                page = cs_active[0]
                eb_q.append(page)
                timeline.append({"cycle": cycle, "event": "CS_READY", "page": page})
                cs_active = None
            if cs_active is None and cs_q and len(eb_q) < c.queue_depth:
                page = cs_q.pop(0)
                d = duration(c.page_bytes, c.c0_to_cs_bytes_per_cycle)
                cs_active = (page, cycle + d)
                metrics["c0_to_cs_busy_cycles"] += d
                timeline.append({"cycle": cycle, "event": "C0_CS_START", "page": page})

            # App RAM -> inactive P0/P1 slot. Refill can overlap page consumption.
            if app_active is not None and cycle >= app_active[2]:
                block, slot, _ = app_active
                p0p1[slot] = block
                timeline.append({"cycle": cycle, "event": "P0P1_BLOCK_READY", "block": block, "slot": slot})
                app_active = None

            # P0/P1 -> C0/L0I page transfer.
            if p0_active is not None and cycle >= p0_active[1] and len(c0_q) < c.queue_depth:
                page = p0_active[0]
                c0_q.append(page)
                timeline.append({"cycle": cycle, "event": "C0_READY", "page": page})
                p0_active = None
                if (page + 1) % pages_per_block == 0 or page + 1 == pages_requested:
                    block = page // pages_per_block
                    slot = block % 2
                    if p0p1[slot] == block:
                        p0p1[slot] = None
                        timeline.append({"cycle": cycle, "event": "P0P1_SLOT_RELEASE", "block": block, "slot": slot})
            if p0_active is None and current_page < pages_requested and len(c0_q) < c.queue_depth:
                block = current_page // pages_per_block
                slot = block % 2
                if p0p1[slot] == block:
                    d = duration(c.page_bytes, c.p0p1_to_c0_bytes_per_cycle)
                    p0_active = (current_page, cycle + d)
                    metrics["p0p1_to_c0_busy_cycles"] += d
                    timeline.append({"cycle": cycle, "event": "P0P1_C0_START", "page": current_page, "block": block})
                    current_page += 1
                else:
                    if cycle < refill_latency and block == 0:
                        metrics["p0p1_cold_stall_cycles"] += 1
                    else:
                        metrics["p0p1_boundary_stall_cycles"] += 1

            if app_active is None and next_refill < blocks_total:
                slot = next_refill % 2
                if p0p1[slot] is None:
                    block = next_refill
                    app_active = (block, slot, cycle + refill_latency)
                    next_refill += 1
                    metrics["p0p1_refills"] += 1
                    metrics["app_bytes_read"] += c.block_bytes
                    timeline.append({"cycle": cycle, "event": "APP_P0P1_REFILL_START", "block": block, "slot": slot})

            metrics["c0_queue_peak"] = max(metrics["c0_queue_peak"], len(c0_q))
            metrics["cs_queue_peak"] = max(metrics["cs_queue_peak"], len(cs_q))
            metrics["eb_queue_peak"] = max(metrics["eb_queue_peak"], len(eb_q))

            if retired >= pages_requested:
                return Result(cycle + 1, pages_requested, retired,
                    metrics["p0p1_refills"], metrics["app_bytes_read"], refill_latency,
                    metrics["p0p1_cold_stall_cycles"], metrics["p0p1_boundary_stall_cycles"],
                    metrics["p0p1_to_c0_busy_cycles"], metrics["c0_to_cs_busy_cycles"],
                    metrics["cs_to_eb_busy_cycles"], metrics["eb_consume_busy_cycles"],
                    metrics["cpu_not_ready_stall_cycles"], metrics["c0_queue_peak"],
                    metrics["cs_queue_peak"], metrics["eb_queue_peak"], timeline)

        raise TimeoutError(f"frontend did not retire {pages_requested} pages in {c.max_cycles} cycles")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=32)
    ap.add_argument("--app-bpc", type=int, default=64)
    ap.add_argument("--setup", type=int, default=40)
    ap.add_argument("--p0p1-c0-rate", type=int, default=8)
    ap.add_argument("--c0-cs-rate", type=int, default=16)
    ap.add_argument("--cs-eb-rate", type=int, default=16)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    cfg = Config(app_bytes_per_cycle=a.app_bpc, app_setup_cycles=a.setup,
        p0p1_to_c0_bytes_per_cycle=a.p0p1_c0_rate,
        c0_to_cs_bytes_per_cycle=a.c0_cs_rate,
        cs_to_eb_bytes_per_cycle=a.cs_eb_rate)
    result = asdict(IntegratedFrontend(cfg).run(a.pages))
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        for key, value in result.items():
            if key != "timeline":
                print(f"{key}: {value}")
        print(f"timeline events: {len(result['timeline'])}")


if __name__ == "__main__":
    main()
