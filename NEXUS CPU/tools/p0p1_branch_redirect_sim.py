#!/usr/bin/env python3
"""Simple P0/P1 branch redirect penalty model; not RTL or silicon timing."""
from dataclasses import dataclass, asdict
import argparse
import json
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


def simulate_redirect(block_kb=8, app_bpc=64, setup=40, consume_bpc=8,
                      branch_block=0, target_block=7):
    if branch_block < 0 or target_block <= branch_block + 1:
        raise ValueError("target must be at least two blocks beyond branch block")
    model = P0P1(block_kb * 1024, app_bpc, setup, consume_bpc)

    # Cycle zero starts the cold fetch. The branch is in the selected block;
    # all blocks through branch_block execute before redirect is resolved.
    branch_start = model.refill_latency + branch_block * model.consume_cycles
    branch_end = branch_start + model.consume_cycles
    redirect_start = branch_end

    # Redirect invalidates the sequential wrong-path block and requests target.
    target_ready = redirect_start + model.refill_latency
    stall = target_ready - redirect_start
    return RedirectResult(
        branch_block, target_block, model.refill_latency,
        block_kb * 1024, stall, 1, target_ready
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffer-kb", type=int, default=8)
    ap.add_argument("--app-bpc", type=int, default=64)
    ap.add_argument("--setup", type=int, default=40)
    ap.add_argument("--consume-bpc", type=int, default=8)
    ap.add_argument("--branch-block", type=int, default=0)
    ap.add_argument("--target-block", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    result = asdict(simulate_redirect(a.buffer_kb, a.app_bpc, a.setup,
                                      a.consume_bpc, a.branch_block, a.target_block))
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
