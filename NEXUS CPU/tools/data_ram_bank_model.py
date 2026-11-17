"""NEX-T004 Data RAM bank-group reservation model.

This is a single-group CPU bank-behavior model, not a claim about the
number/placement of physical groups or System Fabric arbitration.
"""
from __future__ import annotations

import math


class DataRamBankGroup:
    BANKS = 8
    SLICE_BYTES = 8
    LEGAL_WIDTHS = {1, 2, 4, 8, 16, 32, 64}

    def __init__(self, bank_hash: str = "folded", service_cycles_per_beat: int = 1):
        if bank_hash not in {"low", "folded"}:
            raise ValueError("bank_hash must be 'low' or 'folded'")
        if service_cycles_per_beat < 1:
            raise ValueError("service_cycles_per_beat must be positive")
        self.bank_hash = bank_hash
        self.service_cycles_per_beat = service_cycles_per_beat
        self.bank_next_cycle = [0] * self.BANKS
        self.events = []

    def bank_for_word(self, word_address: int) -> int:
        if self.bank_hash == "folded":
            return (((word_address >> 3) & 7) ^
                    ((word_address >> 6) & 7) ^
                    ((word_address >> 9) & 7)) & 7
        return (word_address // self.SLICE_BYTES) & 7

    def _plan(self, cycle: int, address: int, width: int):
        if cycle < 0 or address < 0:
            raise ValueError("cycle and address must be non-negative")
        if width not in self.LEGAL_WIDTHS:
            raise ValueError(f"unsupported access width: {width} bytes")
        if address % width:
            raise ValueError(f"{width * 8}-bit access is not naturally aligned")
        first = (address // self.SLICE_BYTES) * self.SLICE_BYTES
        last = ((address + width - 1) // self.SLICE_BYTES) * self.SLICE_BYTES
        beats = []
        word = first
        while word <= last:
            beats.append(self.bank_for_word(word))
            word += self.SLICE_BYTES
        # A wide architectural operation reserves all of its slices atomically.
        local_next = {}
        completion = cycle
        for bank in beats:
            start = max(cycle, self.bank_next_cycle[bank], local_next.get(bank, cycle))
            done = start + self.service_cycles_per_beat
            local_next[bank] = done
            completion = max(completion, done)
        return beats, local_next, completion

    def reserve(self, cycle: int, request_id: str, address: int, width: int) -> dict:
        beats, local_next, completion = self._plan(cycle, address, width)
        # Commit only after every beat has passed validation/planning.
        for bank, next_cycle in local_next.items():
            self.bank_next_cycle[bank] = next_cycle
        event = {
            "request_id": request_id,
            "request_cycle": cycle,
            "address": address,
            "width_bytes": width,
            "bank_beats": list(beats),
            "unique_banks": sorted(set(beats)),
            "bank_count_touched": len(set(beats)),
            "stripe_crossing": address // 64 != (address + width - 1) // 64,
            "service_complete_cycle": completion,
        }
        self.events.append(event)
        return event

    def reserve_batch(self, cycle: int, requests: list[dict]) -> list[dict]:
        """Reserve a same-cycle batch; bank conflicts serialize locally."""
        return [
            self.reserve(cycle, str(req["id"]), int(req["address"]), int(req["width"]))
            for req in requests
        ]
