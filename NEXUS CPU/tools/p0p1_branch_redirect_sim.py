#!/usr/bin/env python3
"""P0/P1 branch redirect models.

The legacy function preserves the original isolated-refill estimate. The
integrated estimate adds serialized target-path delivery latency using the
selected frontend operating point. Both are architecture-level models, not
RTL or silicon timing.
"""
from dataclasses import dataclass, asdict
import argparse
import json
import math

from p0p1_command_buffer_sim import P0P1


@dataclass
class RedirectResult:
    branch_block: int
    target_block: int
    refill_latency: int
    wrong_path_bytes_discarded: int
    redirect_stall_cycles: int
    redirect_refill_count: int
    target_ready_cycle: int


@dataclass
class IntegratedRedirectResult:
    branch_block: int
    target_block: int
    app_refill_cycles: int
    p0p1_to_c0_cycles: int
    c0_to_cs_cycles: int
    cs_to_eb_cycles: int
    eb_delivery_cycles: int
    target_delivery_latency: int
    p0p1_wrong_path_block_discarded_bytes: int
    queued_wrong_path_pages_flushed: int
    queued_wrong_path_bytes_flushed: int
    target_ready_cycle: int


def simulate_redirect(block_kb=8, app_bpc=64, setup=40, consume_bpc=8,
                      branch_block=0, target_block=7):
    if branch_block < 0 or target_block <= branch_block + 1:
        raise ValueError("target must be at least two blocks beyond branch block")
    model = P0P1(block_kb * 1024, app_bpc, setup, consume_bpc)
    branch_start = model.refill_latency + branch_block * model.consume_cycles
    branch_end = branch_start + model.consume_cycles
    redirect_start = branch_end
    target_ready = redirect_start + model.refill_latency
    stall = target_ready - redirect_start
    return RedirectResult(
        branch_block, target_block, model.refill_latency,
        block_kb * 1024, stall, 1, target_ready
    )


def simulate_integrated_redirect(
    branch_block=0,
    target_block=7,
    app_bpc=64,
    app_setup=40,
    block_bytes=8192,
    page_bytes=2048,
    p0p1_to_c0_bpc=16,
    c0_to_cs_bpc=20,
    cs_to_eb_bpc=20,
    eb_consume_bpc=16,
    queued_wrong_path_pages=2,
):
    if branch_block < 0 or target_block <= branch_block + 1:
        raise ValueError("target must be at least two blocks beyond branch block")
    if queued_wrong_path_pages < 0:
        raise ValueError("queued_wrong_path_pages must be nonnegative")
    rates = (app_bpc, p0p1_to_c0_bpc, c0_to_cs_bpc, cs_to_eb_bpc, eb_consume_bpc)
    if min(rates) <= 0 or min(block_bytes, page_bytes) <= 0 or app_setup < 0:
        raise ValueError("sizes and rates must be positive; setup must be nonnegative")
    if block_bytes % page_bytes:
        raise ValueError("P0/P1 block size must be divisible by page size")
    if page_bytes % 8:
        raise ValueError("page size must be 8-byte aligned")

    app_refill = app_setup + math.ceil(block_bytes / app_bpc)
    p0_to_c0 = math.ceil(page_bytes / p0p1_to_c0_bpc)
    c0_to_cs = math.ceil(page_bytes / c0_to_cs_bpc)
    cs_to_eb = math.ceil(page_bytes / cs_to_eb_bpc)
    eb_delivery = math.ceil(page_bytes / eb_consume_bpc)
    latency = app_refill + p0_to_c0 + c0_to_cs + cs_to_eb + eb_delivery

    # Branch resolves at the end of its block. This conservative model
    # serializes target refill and first-page delivery; it does not assume
    # speculative target fetch or overlap with a partially completed refill.
    branch_resolution = app_refill + (branch_block + 1) * math.ceil(
        block_bytes / p0p1_to_c0_bpc
    )
    return IntegratedRedirectResult(
        branch_block=branch_block,
        target_block=target_block,
        app_refill_cycles=app_refill,
        p0p1_to_c0_cycles=p0_to_c0,
        c0_to_cs_cycles=c0_to_cs,
        cs_to_eb_cycles=cs_to_eb,
        eb_delivery_cycles=eb_delivery,
        target_delivery_latency=latency,
        p0p1_wrong_path_block_discarded_bytes=block_bytes,
        queued_wrong_path_pages_flushed=queued_wrong_path_pages,
        queued_wrong_path_bytes_flushed=queued_wrong_path_pages * page_bytes,
        target_ready_cycle=branch_resolution + latency,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffer-kb", type=int, default=8)
    ap.add_argument("--app-bpc", type=int, default=64)
    ap.add_argument("--setup", type=int, default=40)
    ap.add_argument("--consume-bpc", type=int, default=8)
    ap.add_argument("--branch-block", type=int, default=0)
    ap.add_argument("--target-block", type=int, default=7)
    ap.add_argument("--integrated", action="store_true")
    ap.add_argument("--queued-wrong-path-pages", type=int, default=2)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.integrated:
        result = asdict(simulate_integrated_redirect(
            branch_block=a.branch_block,
            target_block=a.target_block,
            app_bpc=a.app_bpc,
            app_setup=a.setup,
            queued_wrong_path_pages=a.queued_wrong_path_pages,
        ))
    else:
        result = asdict(simulate_redirect(
            a.buffer_kb, a.app_bpc, a.setup, a.consume_bpc,
            a.branch_block, a.target_block
        ))
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
