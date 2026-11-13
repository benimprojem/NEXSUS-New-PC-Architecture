#!/usr/bin/env python3
"""NEXSUS 8x64-bit bank mapping and conflict model.

Architectural address-mapping model only: not RTL, cycle-accurate timing,
MOSRAM SPICE/TCAD, or a complete memory-controller simulation.
"""
from __future__ import annotations

import argparse
import random
from collections import Counter
from dataclasses import dataclass

BANKS = 8
SLICE_BYTES = 8
DEFAULT_STRIDES = (8, 16, 32, 64, 128, 4096)
DEFAULT_WIDTHS = (8, 16, 32, 64, 128, 256, 512)


@dataclass(frozen=True)
class Request:
    address: int
    width_bits: int
    name: str = "request"

    def __post_init__(self) -> None:
        if self.address < 0:
            raise ValueError("address must be non-negative")
        if self.width_bits <= 0 or self.width_bits % 8:
            raise ValueError("width_bits must be a positive multiple of 8")


def bank_index(address: int, mapping: str) -> int:
    """Map an 8-byte word's physical/domain-relative address to one bank."""
    if address < 0:
        raise ValueError("address must be non-negative")
    low = (address >> 3) & 0b111
    if mapping == "low":
        return low
    if mapping == "folded":
        return (low ^ ((address >> 6) & 0b111)
                ^ ((address >> 9) & 0b111)) & 0b111
    raise ValueError(f"unknown mapping: {mapping}")


def request_bank_beats(request: Request, mapping: str) -> Counter[int]:
    """Count 64-bit bank slices touched by one byte-range request.

    Every intersected 8-byte word contributes one bank beat. A request may
    touch a bank more than once when it crosses an interleave stripe.
    Alignment legality is deliberately not decided here; ISA rules govern it.
    """
    byte_count = request.width_bits // 8
    first_word = request.address // SLICE_BYTES
    last_word = (request.address + byte_count - 1) // SLICE_BYTES
    return Counter(bank_index(word * SLICE_BYTES, mapping)
                   for word in range(first_word, last_word + 1))


def analyze_batch(requests: list[Request], mapping: str) -> dict:
    """Aggregate bank demand for a simultaneous batch of architectural requests."""
    demand: Counter[int] = Counter()
    request_sets: dict[str, list[int]] = {}
    for index, request in enumerate(requests):
        beats = request_bank_beats(request, mapping)
        demand.update(beats)
        request_sets[f"{request.name}:{index}"] = sorted(beats)
    counts = [demand.get(bank, 0) for bank in range(BANKS)]
    return {
        "counts": counts,
        "unique": sum(value > 0 for value in counts),
        "rounds": max(counts, default=0),
        "request_banks": request_sets,
        "total_bank_beats": sum(counts),
    }


def multi_stream_batch(streams: int, stride: int, base: int,
                       stream_spacing: int, width_bits: int) -> list[Request]:
    """One simultaneous request from each stream, at distinct stream offsets."""
    if streams <= 0 or stride <= 0 or stream_spacing < 0:
        raise ValueError("streams/stride must be positive; spacing non-negative")
    return [
        Request(base + stream * stream_spacing, width_bits, f"s{stream}")
        for stream in range(streams)
    ]


def format_counts(counts: list[int]) -> str:
    return "[" + ",".join(str(value) for value in counts) + "]"


def run_self_tests() -> None:
    # Legacy eight-stream scalar-stride results.
    expected = {
        8: (8, 1, 8, 1),
        16: (4, 2, 8, 1),
        32: (2, 4, 8, 1),
        64: (1, 8, 8, 1),
        128: (1, 8, 8, 1),
        4096: (1, 8, 1, 8),
    }
    for stride, (lu, lr, fu, fr) in expected.items():
        reqs = [Request(i * stride, 64, f"r{i}") for i in range(8)]
        low = analyze_batch(reqs, "low")
        folded = analyze_batch(reqs, "folded")
        assert (low["unique"], low["rounds"],
                folded["unique"], folded["rounds"]) == (lu, lr, fu, fr)

    # Aligned widths consume 1/2/4/8 distinct slices.
    for width, expected_banks in ((64, 1), (128, 2), (256, 4), (512, 8)):
        result = analyze_batch([Request(0, width)], "low")
        assert result["unique"] == expected_banks
        assert result["rounds"] == 1

    # A 512-bit request shifted by one 64-bit slice touches nine words;
    # one bank is demanded twice in this simple striping model.
    misaligned = analyze_batch([Request(8, 512)], "low")
    assert misaligned["total_bank_beats"] == 9
    assert misaligned["rounds"] == 2

    # Two independent physical memory paths can progress concurrently:
    # their service-round counts are separate, not summed into one bank pool.
    app = analyze_batch([Request(0, 512, "fetch")], "folded")
    data = analyze_batch([Request(0, 64, "load")], "folded")
    assert app["rounds"] == data["rounds"] == 1


def run_stride_table(requests: int, base: int, strides: tuple[int, ...],
                     width_bits: int) -> None:
    print(f"\n{requests} simultaneous requests, width={width_bits} bit, base=0x{base:x}")
    print("stride | mapping | per-bank beats | unique | min rounds")
    for stride in strides:
        batch = [Request(base + i * stride, width_bits, f"r{i}")
                 for i in range(requests)]
        for mapping in ("low", "folded"):
            result = analyze_batch(batch, mapping)
            print(f"{stride:>6} | {mapping:>7} | "
                  f"{format_counts(result['counts']):<23} | "
                  f"{result['unique']:>6} | {result['rounds']:>10}")


def run_width_table(base: int, widths: tuple[int, ...]) -> None:
    print(f"\nSingle request width sweep, base=0x{base:x}")
    print("width | alignment offset | mapping | bank beats | unique | min rounds")
    for width in widths:
        for offset in (0, 8):
            request = Request(base + offset, width, f"w{width}")
            for mapping in ("low", "folded"):
                result = analyze_batch([request], mapping)
                print(f"{width:>5} | {offset:>16} | {mapping:>7} | "
                      f"{result['total_bank_beats']:>10} | "
                      f"{result['unique']:>6} | {result['rounds']:>10}")


def run_random_sweep(seed: int, samples: int, streams: int,
                     width_bits: int) -> None:
    rng = random.Random(seed)
    requests_per_batch = streams
    totals = {name: {"rounds": 0, "conflict_batches": 0,
                     "max_rounds": 0, "bank_beats": 0}
              for name in ("low", "folded")}
    for _ in range(samples):
        # 64-byte aligned region base plus independent offsets in 8-byte units.
        batch = [
            Request(rng.randrange(0, 1 << 20) // 8 * 8,
                    width_bits, f"rnd{i}")
            for i in range(requests_per_batch)
        ]
        for mapping in totals:
            result = analyze_batch(batch, mapping)
            stats = totals[mapping]
            stats["rounds"] += result["rounds"]
            stats["conflict_batches"] += result["rounds"] > 1
            stats["max_rounds"] = max(stats["max_rounds"], result["rounds"])
            stats["bank_beats"] += result["total_bank_beats"]
    print(f"\nDeterministic random sweep: seed={seed}, batches={samples}, "
          f"streams={streams}, width={width_bits} bit")
    print("mapping | avg min rounds | conflict batches | max rounds | total bank beats")
    for mapping, stats in totals.items():
        average = stats["rounds"] / samples if samples else 0
        print(f"{mapping:>7} | {average:>15.3f} | "
              f"{stats['conflict_batches']:>16} | "
              f"{stats['max_rounds']:>10} | {stats['bank_beats']:>16}")


def run_app_data_example() -> None:
    # Distinct physical bank groups/controllers: service demand is reported
    # separately. No cross-path bank conflict is introduced by this model.
    app = analyze_batch([Request(0, 512, "P0-refill")], "folded")
    data = analyze_batch([
        Request(0x1000, 64, "scalar-load"),
        Request(0x1040, 256, "vector-load"),
    ], "folded")
    print("\nIndependent App RAM and Data RAM paths")
    print(f"App RAM: 512-bit P0 refill -> {app['total_bank_beats']} bank beats, "
          f"{app['rounds']} minimum round(s)")
    print(f"Data RAM: scalar + 256-bit load -> {data['total_bank_beats']} bank beats, "
          f"{data['rounds']} minimum round(s)")
    print("The paths are independent; these round counts are not added together.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--base", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--strides", type=lambda value: tuple(
        int(item, 0) for item in value.split(",")
    ), default=DEFAULT_STRIDES)
    parser.add_argument("--widths", type=lambda value: tuple(
        int(item, 0) for item in value.split(",")
    ), default=DEFAULT_WIDTHS)
    parser.add_argument("--random-samples", type=int, default=1000)
    parser.add_argument("--random-streams", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261113)
    args = parser.parse_args()

    run_self_tests()
    print("NEXSUS 8-bank mapping/conflict model — architectural abstraction")
    print("No cycle timing, physical ports, controller queues, ECC or MOSRAM model.")
    run_stride_table(args.requests, args.base, args.strides, 64)
    run_width_table(args.base, args.widths)
    run_random_sweep(args.seed, args.random_samples,
                     args.random_streams, 64)
    run_app_data_example()
    print("\nSelf-tests: PASS")


if __name__ == "__main__":
    main()
