#!/usr/bin/env python3
"""Deterministic address-to-bank mapping model for the NEXSUS 8x64-bit baseline.

This is an architectural mapping model, not RTL, cycle-accurate timing, or a
physical MOSRAM simulator. It assumes one 64-bit request beat per bank per
service round and ignores queue, port-turnaround, ECC, and Fabric delays.
"""
from __future__ import annotations

import argparse
from collections import Counter

BANKS = 8
SLICE_BYTES = 8
DEFAULT_STRIDES = (8, 16, 32, 64, 128, 4096)


def bank_index(address: int, mapping: str) -> int:
    """Return the bank selected for an 8-byte word at physical byte address."""
    if address < 0:
        raise ValueError("address must be non-negative")
    low = (address >> 3) & 0b111
    if mapping == "low":
        return low
    if mapping == "folded":
        return (low ^ ((address >> 6) & 0b111)
                ^ ((address >> 9) & 0b111))
    raise ValueError(f"unknown mapping: {mapping}")


def analyze_stream(stride: int, requests: int = 8, base: int = 0,
                   mapping: str = "low") -> tuple[list[int], int, int]:
    """Analyze independent 64-bit requests; return counts, unique banks, rounds."""
    if stride <= 0 or requests <= 0:
        raise ValueError("stride and requests must be positive")
    counts = Counter(bank_index(base + i * stride, mapping)
                     for i in range(requests))
    per_bank = [counts.get(bank, 0) for bank in range(BANKS)]
    return per_bank, sum(value > 0 for value in per_bank), max(per_bank)


def format_counts(counts: list[int]) -> str:
    return "[" + ",".join(str(value) for value in counts) + "]"


def run_self_tests() -> None:
    expected = {
        8: (8, 1, 8, 1),
        16: (4, 2, 8, 1),
        32: (2, 4, 8, 1),
        64: (1, 8, 8, 1),
        128: (1, 8, 8, 1),
        4096: (1, 8, 1, 8),
    }
    for stride, (low_unique, low_rounds, fold_unique, fold_rounds) in expected.items():
        _, lu, lr = analyze_stream(stride, mapping="low")
        _, fu, fr = analyze_stream(stride, mapping="folded")
        assert (lu, lr, fu, fr) == (
            low_unique, low_rounds, fold_unique, fold_rounds
        ), f"unexpected result for stride={stride}"
    # Eight contiguous 64-bit words occupy all banks under both mappings.
    assert analyze_stream(8, mapping="low")[1:] == (8, 1)
    assert analyze_stream(8, mapping="folded")[1:] == (8, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--base", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--strides", type=lambda value: tuple(
        int(item, 0) for item in value.split(",")
    ), default=DEFAULT_STRIDES)
    args = parser.parse_args()

    run_self_tests()
    print("NEXSUS 8-bank address mapping model")
    print("Assumption: one 64-bit beat/bank/service round; no timing model.")
    print(f"requests={args.requests}, base=0x{args.base:x}")
    print("stride | mapping | per-bank request counts | unique | min rounds")
    for stride in args.strides:
        for mapping in ("low", "folded"):
            counts, unique, rounds = analyze_stream(
                stride, args.requests, args.base, mapping
            )
            print(f"{stride:>6} | {mapping:>7} | {format_counts(counts):<23}"
                  f" | {unique:>6} | {rounds:>10}")
    print("Self-tests: PASS")


if __name__ == "__main__":
    main()
