#!/usr/bin/env python3
"""NEXSUS CPU comparison simulator — controlled 8-core model v0.2.4-dev

This is an event/cycle-level teaching and design-space model, not RTL, gem5,
or a vendor-certified replica. Unknown NEXSUS parameters are explicit inputs.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class Op:
    seq: int
    kind: str
    deps: Tuple[int, ...] = ()
    address: int = 0
    width: int = 8
    label: str = ""
    command_address: int = -1

@dataclass
class CoreProfile:
    name: str
    frontend: int
    dispatch: int
    issue: int
    retire: int
    rob: int
    units: Dict[str, int]
    latency: Dict[str, int]
    l1_kb: int
    l2_kb: int
    l3_kb: int
    l4_kb: int
    l1_lat: int
    l2_lat: int
    l3_lat: int
    l4_lat: int
    dram_lat: int
    branch_penalty: int
    frequency_ghz: float
    line_bytes: int = 64
    bank_count: int = 8
    bank_beat_bytes: int = 8
    bank_hash: str = "low"
    dram_bytes_per_cycle: float = 32
    core_count: int = 1
    core_type: str = "uniform"

# Publicly documented or independently measured values are marked in docs.
# Unpublished/uncertain values are conservative model assumptions, not claims.
PROFILES = {
    "amd_9950x": {
        "name": "AMD Ryzen 9 9950X / Zen 5",
        "core_count": 8, "core_type": "uniform", "frontend": 4,
        "dispatch": 8, "issue": 8, "retire": 8, "rob": 448,
        "units": {"INT": 6, "FP": 4, "VEC": 2, "LOAD": 4, "STORE": 2, "BR": 1, "CTX": 1, "ATOM": 1},
        "latency": {"INT": 1, "FP": 3, "VEC": 3, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 8, "CTX": 8},
        "l1_kb": 48, "l2_kb": 1024, "l3_kb": 32768, "l4_kb": 0,
        "l1_lat": 4, "l2_lat": 14, "l3_lat": 48, "l4_lat": 0, "dram_lat": 120,
        "branch_penalty": 15, "frequency_ghz": 3.0,
        "dram_lat": 120, "dram_bytes_per_cycle": 32
    },
    "intel_285k_p": {
        "name": "Intel Core Ultra 9 285K / Lion Cove P-core",
        "core_count": 8, "core_type": "P", "frontend": 8,
        "dispatch": 8, "issue": 8, "retire": 12, "rob": 576,
        "units": {"INT": 6, "FP": 4, "VEC": 2, "LOAD": 3, "STORE": 2, "BR": 1, "CTX": 1, "ATOM": 1},
        "latency": {"INT": 1, "FP": 3, "VEC": 3, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 8, "CTX": 8},
        "l1_kb": 48, "l2_kb": 3072, "l3_kb": 36864, "l4_kb": 0,
        "l1_lat": 4, "l2_lat": 17, "l3_lat": 84, "l4_lat": 0, "dram_lat": 120,
        "branch_penalty": 16, "frequency_ghz": 3.0,
        "dram_lat": 120, "dram_bytes_per_cycle": 32
    },
    "intel_285k_e": {
        "name": "Intel Core Ultra 9 285K / Skymont E-core",
        "core_count": 8, "core_type": "E", "frontend": 9,
        "dispatch": 8, "issue": 8, "retire": 16, "rob": 416,
        "units": {"INT": 4, "FP": 2, "VEC": 2, "LOAD": 3, "STORE": 2, "BR": 1, "CTX": 1, "ATOM": 1},
        "latency": {"INT": 1, "FP": 4, "VEC": 4, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 10, "CTX": 8},
        "l1_kb": 32, "l2_kb": 4096, "l3_kb": 36864, "l4_kb": 0,
        "l1_lat": 4, "l2_lat": 16, "l3_lat": 90, "l4_lat": 0, "dram_lat": 120,
        "branch_penalty": 17, "frequency_ghz": 3.0,
        "dram_lat": 120, "dram_bytes_per_cycle": 32
    },
    "nexus_balanced_128": {
        "name": "NEXSUS CPU / selected 128-window architecture",
        "core_count": 8, "core_type": "uniform", "frontend": 8,
        "dispatch": 8, "issue": 10, "retire": 8, "rob": 128,
        "units": {"INT": 4, "FP": 4, "VEC": 2, "LOAD": 8, "STORE": 4, "BR": 2, "CTX": 1, "ATOM": 1},
        "latency": {"INT": 1, "FP": 3, "VEC": 2, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 8, "CTX": 4},
        "l1_kb": 128, "l2_kb": 1024, "l3_kb": 8192, "l4_kb": 65536,
        "l1_lat": 2, "l2_lat": 8, "l3_lat": 24, "l4_lat": 64, "dram_lat": 120,
        "branch_penalty": 10, "frequency_ghz": 3.0,
        "bank_hash": "folded", "dram_bytes_per_cycle": 32
    }
}

def add_op(ops: List[Op], kind: str, deps=(), address=0, width=8, label="", command_address=None):
    seq = len(ops)
    pc = seq * 8 if command_address is None else command_address
    ops.append(Op(seq, kind, tuple(dict.fromkeys(deps)), address, width, label, pc))
    return seq

def build_composite_workload(scale: int = 1) -> Dict[str, List[Op]]:
    """One deterministic algorithm suite; every CPU receives the same logical work."""
    n = max(1, scale)
    result = {}

    # A) Scalar recurrence + independent integer work + unpredictable branches.
    ops = []
    chain = None
    for i in range(120*n):
        deps = () if chain is None else (chain,)
        chain = add_op(ops, "INT", deps, label="scalar recurrence")
        add_op(ops, "INT", (chain,), label="independent integer transform")
        if i % 12 == 0:
            add_op(ops, "BR", (chain,), label="control branch")
    result["scalar_control"] = ops

    # B) Pointer-chasing graph walk: serial loads expose memory latency.
    ops = []
    ptr = None
    for i in range(72*n):
        ptr = add_op(ops, "LOAD", () if ptr is None else (ptr,),
                     address=(0x100000 + ((i * 4099) % (256*n*1024))), label="dependent graph load")
        if i % 6 == 0:
            add_op(ops, "BR", (ptr,), label="graph decision")
    result["pointer_graph"] = ops

    # C) Dense numeric tile: independent loads, FP arithmetic and vector work.
    ops = []
    for tile in range(24*n):
        a = add_op(ops, "LOAD", (), 0x400000 + tile*256, 64, "matrix tile A")
        b = add_op(ops, "LOAD", (), 0x800000 + tile*256, 64, "matrix tile B")
        x = add_op(ops, "FP", (a,b), label="multiply accumulate")
        y = add_op(ops, "FP", (x,), label="accumulate")
        add_op(ops, "VEC", (a,b,y), label="vector tile operation")
        add_op(ops, "STORE", (y,), 0xC00000 + tile*256, 64, "matrix result")
    result["numeric_tile"] = ops

    # D) Streaming transform: sequential reads/writes, memory bandwidth pressure.
    ops = []
    for i in range(192*n):
        ld = add_op(ops, "LOAD", (), 0x1000000 + i*64, 64, "stream read")
        calc = add_op(ops, "INT", (ld,), label="stream transform")
        add_op(ops, "STORE", (calc,), 0x2000000 + i*64, 64, "stream write")
    result["streaming"] = ops

    # E) Parallel task/context workload: task-local compute and bounded context work.
    ops = []
    for task in range(16*n):
        a = add_op(ops, "LOAD", (), 0x3000000 + task*4096, 64, "task input")
        b = add_op(ops, "INT", (a,), label="task compute")
        c = add_op(ops, "FP", (b,), label="task numeric")
        d = add_op(ops, "STORE", (c,), 0x3800000 + task*4096, 64, "task output")
        add_op(ops, "CTX", (d,), label="task context save/restore")
    result["parallel_tasks"] = ops

    # F) Independent integer throughput: isolates ALU issue/resource capacity.
    ops = []
    for i in range(512*n):
        add_op(ops, "INT", label="independent integer throughput")
    result["integer_throughput"] = ops

    # G) Independent FP throughput: isolates floating-point execution resources.
    ops = []
    for i in range(512*n):
        add_op(ops, "FP", label="independent floating-point throughput")
    result["fp_throughput"] = ops

    # H) Independent vector throughput. This is a generic vector-unit test;
    # it is not yet a faithful ME512 matrix instruction model.
    ops = []
    for i in range(256*n):
        add_op(ops, "VEC", label="independent vector throughput")
    result["vector_throughput"] = ops

    # I) Branch-heavy independent control flow to expose recovery penalties.
    ops = []
    for i in range(256*n):
        add_op(ops, "BR", label="independent branch stress")
    result["branch_stress"] = ops

    # J) Explicit SPM2 hot set: same 4 KiB task-local working set is revisited.
    ops = []
    for i in range(2048*n):
        add_op(ops, "LOAD" if i % 4 else "STORE", (),
               address=(i % 64) * 64, width=64, label="SPM2: hot task working set")
    result["spm_hot_workset"] = ops

    # K) SPM2 capacity sweep: addresses cover 16 KiB, exceeding the 8 KiB SPM2.
    ops = []
    for i in range(2048*n):
        add_op(ops, "LOAD", (), address=(i % 256) * 64, width=64,
               label="SPM2: capacity sweep")
    result["spm_capacity_sweep"] = ops

    # L) Sequential command supply; one unique command address per operation.
    ops = []
    for i in range(2048*n):
        add_op(ops, "INT", label="P0 sequential", command_address=i*8)
    result["p0_sequential"] = ops

    # M) Branch-heavy command stream; branch recovery remains independently modeled.
    ops = []
    for i in range(2048*n):
        add_op(ops, "BR", label="P0 branch", command_address=i*8)
    result["p0_branch"] = ops

    # N) Repeated 2 KiB command loop (fits both P0 and conventional I-cache).
    ops = []
    for i in range(4096*n):
        add_op(ops, "INT", label="P0 working set", command_address=(i % 256)*8)
    result["p0_working_set"] = ops

    # O) Repeated 16 KiB command loop (exceeds P0 and 32 KiB conventional I-cache).
    ops = []
    for i in range(8192*n):
        add_op(ops, "INT", label="P0 starvation", command_address=(i % 2048)*8)
    result["p0_starvation"] = ops

    return result

class LRU:
    def __init__(self, capacity_bytes: int, line_bytes: int):
        self.capacity = max(1, capacity_bytes // line_bytes)
        self.lines = OrderedDict()
    def lookup(self, line: int) -> bool:
        hit = line in self.lines
        if hit:
            self.lines.move_to_end(line)
        return hit
    def touch(self, line: int) -> bool:
        hit = self.lookup(line)
        if not hit:
            self.insert(line)
        return hit
    def insert(self, line: int):
        if line in self.lines:
            self.lines.move_to_end(line)
            return
        self.lines[line] = None
        if len(self.lines) > self.capacity:
            self.lines.popitem(last=False)

class CacheHierarchy:
    def __init__(self, p: CoreProfile, shared_l2=None, shared_l3=None, shared_l4=None):
        self.line = p.line_bytes
        self.l1 = LRU(p.l1_kb*1024, self.line)
        self.l2 = shared_l2 if shared_l2 is not None else LRU(p.l2_kb*1024, self.line)
        self.l3 = shared_l3 if shared_l3 is not None else LRU(p.l3_kb*1024, self.line)
        self.l4 = shared_l4 if shared_l4 is not None else (LRU(p.l4_kb*1024, self.line) if p.l4_kb else None)
        self.p = p

    def probe(self, address: int) -> Tuple[int, str]:
        """Lookup only; cache allocation is deferred until the access completes."""
        line = address // self.line
        if self.l1.lookup(line):
            return self.p.l1_lat, "L1"
        if self.l2.lookup(line):
            return self.p.l2_lat, "L2"
        if self.l3.lookup(line):
            return self.p.l3_lat, "L3"
        if self.l4 and self.l4.lookup(line):
            return self.p.l4_lat, "L4"
        return self.p.dram_lat, "DRAM"

    def fill(self, address: int, level: str):
        """Install a completed demand line along the modeled inclusive fill path."""
        line = address // self.line
        if level == "DRAM" and self.l4:
            self.l4.insert(line)
        if level in ("DRAM", "L4"):
            if self.l3:
                self.l3.insert(line)
        if level in ("DRAM", "L4", "L3"):
            self.l2.insert(line)
        self.l1.insert(line)

    def access(self, address: int) -> Tuple[int, str]:
        """Single-core convenience path: probe and immediately complete/fill."""
        latency, level = self.probe(address)
        self.fill(address, level)
        return latency, level


def build_cache_hierarchies(p: CoreProfile, core_count: int) -> List[CacheHierarchy]:
    """Private L1 plus NEXSUS shared cache groups; reference CPUs stay per-core approximations."""
    if not p.name.startswith("NEXSUS CPU"):
        return [CacheHierarchy(p) for _ in range(core_count)]
    line = p.line_bytes
    l2_groups = [LRU(p.l2_kb * 1024, line) for _ in range(math.ceil(core_count / 2))]
    l3_groups = [LRU(p.l3_kb * 1024, line) for _ in range(math.ceil(core_count / 4))]
    l4_groups = [LRU(p.l4_kb * 1024, line) for _ in range(math.ceil(core_count / 8))] if p.l4_kb else []
    return [
        CacheHierarchy(p, l2_groups[i // 2], l3_groups[i // 4],
                       l4_groups[i // 8] if l4_groups else None)
        for i in range(core_count)
    ]


class CommandFetchModel:
    """One outstanding 64-byte command-line refill; P0 vs conventional I-cache."""
    def __init__(self, enabled: bool, p0_capacity_bytes: int = 8192,
                 conventional_capacity_bytes: int = 32768,
                 p0_refill_latency: int = 8, conventional_refill_latency: int = 32):
        self.enabled = enabled
        capacity = p0_capacity_bytes if enabled else conventional_capacity_bytes
        self.lines = LRU(capacity, 64)
        self.refill_latency = p0_refill_latency if enabled else conventional_refill_latency
        self.pending = None
        self.hits = 0
        self.refills = 0
        self.refill_bytes = 0
        self.wait_cycles = 0

    def complete(self, cycle: int):
        if self.pending is not None and self.pending[1] <= cycle:
            line, _ = self.pending
            self.lines.insert(line)
            self.pending = None

    def can_fetch(self, command_address: int, cycle: int) -> bool:
        self.complete(cycle)
        line = command_address // 64
        if self.lines.lookup(line):
            self.hits += 1
            return True
        if self.pending is not None:
            self.wait_cycles += 1
            return False
        self.pending = (line, cycle + self.refill_latency)
        self.refills += 1
        self.refill_bytes += 64
        self.wait_cycles += 1
        return False

def profile_from_dict(d: dict) -> CoreProfile:
    return CoreProfile(**d)

class SharedMemoryController:
    """Global DRAM bank/bus reservation primitive for lockstep multicore scheduling.

    Requests must be submitted as a same-cycle batch. The caller is responsible
    for collecting all cores' eligible misses before calling reserve_batch().
    """
    def __init__(self, bank_count: int = 8, beat_bytes: int = 8,
                 aggregate_bytes_per_cycle: int = 32):
        self.bank_count = bank_count
        self.beat_bytes = beat_bytes
        self.aggregate_bytes_per_cycle = aggregate_bytes_per_cycle
        self.bank_busy = [0] * bank_count
        self.bus_next_byte = 0
        self.rr_cursor = 0

    @property
    def bus_next_cycle(self) -> int:
        return math.ceil(self.bus_next_byte / max(1, self.aggregate_bytes_per_cycle))

    def _bank(self, address: int, bank_hash: str) -> int:
        if bank_hash == "folded":
            return (((address >> 3) & 7) ^ ((address >> 6) & 7) ^
                    ((address >> 9) & 7)) % self.bank_count
        return (address // self.beat_bytes) % self.bank_count

    def reserve_batch(self, cycle: int, requests: List[dict],
                      bank_hash: str = "low") -> dict:
        """Reserve one cycle's requests in rotating core order.

        Each request: {id, core, address, width}. Returns per-request bank
        wait, bus wait, and service completion cycle. The bus is work-conserving:
        idle cores do not own a reserved bandwidth share.
        """
        if not requests:
            return {}
        core_ids = sorted({int(r["core"]) for r in requests})
        start = self.rr_cursor % len(core_ids)
        rotated = core_ids[start:] + core_ids[:start]
        rank = {core: i for i, core in enumerate(rotated)}
        ordered = sorted(requests, key=lambda r: (rank[int(r["core"])], str(r["id"])))
        result = {}
        for req in ordered:
            req_id = req["id"]
            address = int(req["address"])
            width = max(1, int(req["width"]))
            first_beat_address = (address // self.beat_bytes) * self.beat_bytes
            beat_offset = address - first_beat_address
            beats = max(1, math.ceil((beat_offset + width) / self.beat_bytes))
            bank_wait = 0
            for beat in range(beats):
                bank = self._bank(first_beat_address + beat * self.beat_bytes, bank_hash)
                bank_start = max(cycle, self.bank_busy[bank])
                bank_wait = max(bank_wait, bank_start - cycle)
                self.bank_busy[bank] = bank_start + 1
            cycle_byte = cycle * self.aggregate_bytes_per_cycle
            bus_start_byte = max(cycle_byte, self.bus_next_byte)
            bus_wait = max(0, (bus_start_byte // self.aggregate_bytes_per_cycle) - cycle)
            bus_offset = bus_start_byte % self.aggregate_bytes_per_cycle
            bus_service_cycles = max(
                1, math.ceil((bus_offset + width) / self.aggregate_bytes_per_cycle)
            )
            self.bus_next_byte = bus_start_byte + width
            bank_complete = max(self.bank_busy) if self.bank_busy else cycle
            bus_complete = math.ceil(
                (bus_start_byte + width) / self.aggregate_bytes_per_cycle
            )
            result[req_id] = {
                "bank_wait": bank_wait,
                "bus_wait": bus_wait,
                "bus_service_cycles": bus_service_cycles,
                "service_complete_cycle": max(bank_complete, bus_complete),
            }
        self.rr_cursor = (start + 1) % len(core_ids)
        return result


def simulate_stream(ops: List[Op], p: CoreProfile) -> dict:
    """Single hardware thread, OoO window, in-order retirement, shared unit limits."""
    cache = CacheHierarchy(p)
    ready_at = [0] * len(ops)
    done = [False] * len(ops)
    issued = [False] * len(ops)
    dispatched = [False] * len(ops)
    rob = deque()
    unit_busy = {k: [0]*v for k,v in p.units.items()}
    bank_busy = [0] * p.bank_count
    dram_next_cycle = 0
    next_frontend = 0
    cycle = 0
    frontend_blocked_until = 0
    retired = 0
    max_rob = 0
    hits = {"L1":0,"L2":0,"L3":0,"L4":0,"DRAM":0}
    branch_misses = 0
    stalls = {"dependency_blocked_op_cycles": 0, "issue_width_blocked_op_cycles": 0,
              "execution_unit_blocked_op_cycles": 0, "frontend_limited_cycles": 0,
              "rob_full_cycles": 0, "branch_recovery_cycles": 0,
              "memory_latency_exposure_cycles": 0}
    # Fixed, repeatable misprediction pattern: one in every four branch ops.
    branch_number = 0
    limit = max(10000, len(ops)*1000)
    while retired < len(ops) and cycle < limit:
        # Complete operations.
        for op in ops:
            if issued[op.seq] and not done[op.seq] and ready_at[op.seq] <= cycle:
                done[op.seq] = True
        # In-order retirement.
        r = 0
        while rob and r < p.retire and done[rob[0]]:
            rob.popleft(); retired += 1; r += 1

        # Front-end dispatch, constrained by ROB space and branch recovery.
        if next_frontend < len(ops):
            if cycle < frontend_blocked_until:
                stalls["branch_recovery_cycles"] += 1
            elif len(rob) >= p.rob:
                stalls["rob_full_cycles"] += 1
        d = 0
        while (next_frontend < len(ops) and d < p.dispatch and
               len(rob) < p.rob and cycle >= frontend_blocked_until):
            op = ops[next_frontend]
            # Front-end throughput is separately modelled from dispatch.
            if d >= p.frontend:
                break
            dispatched[op.seq] = True
            rob.append(op.seq)
            next_frontend += 1; d += 1
        max_rob = max(max_rob, len(rob))
        if next_frontend < len(ops) and cycle >= frontend_blocked_until and len(rob) < p.rob and d >= min(p.dispatch, p.frontend):
            stalls["frontend_limited_cycles"] += 1

        # Select ready operations oldest-first; dependencies may execute out of order.
        issued_this_cycle = 0
        for seq in list(rob):
            if issued[seq]:
                continue
            op = ops[seq]
            if any(not done[x] for x in op.deps):
                stalls["dependency_blocked_op_cycles"] += 1
                continue
            if issued_this_cycle >= p.issue:
                stalls["issue_width_blocked_op_cycles"] += 1
                continue
            kind = op.kind
            resource = "LOAD" if kind == "LOAD" else ("STORE" if kind == "STORE" else kind)
            slots = unit_busy.get(resource, [])
            slot = next((i for i,t in enumerate(slots) if t <= cycle), None)
            if slot is None:
                stalls["execution_unit_blocked_op_cycles"] += 1
                continue
            latency = p.latency.get(kind, 1)
            if kind in ("LOAD", "STORE"):
                mem_lat, level = cache.access(op.address)
                hits[level] += 1
                latency = max(latency, mem_lat)
                # DRAM/L4 traffic is split into 64-bit bank beats. A wide access
                # may use several banks in parallel; repeated bank hits serialize locally.
                if level == "DRAM" or (level == "L4" and p.l4_kb > 0):
                    wait = 0
                    beats = max(1, math.ceil(op.width / p.bank_beat_bytes))
                    for beat in range(beats):
                        beat_address = op.address + beat*p.bank_beat_bytes
                        if p.bank_hash == "folded":
                            bank = (((beat_address >> 3) & 7) ^ ((beat_address >> 6) & 7) ^ ((beat_address >> 9) & 7)) % p.bank_count
                        else:
                            bank = (beat_address // p.bank_beat_bytes) % p.bank_count
                        start = max(cycle, bank_busy[bank])
                        wait = max(wait, start-cycle)
                        bank_busy[bank] = start + 1
                    bus_start = max(cycle, dram_next_cycle)
                    bus_wait = bus_start-cycle
                    bus_cycles = max(1, math.ceil(op.width / max(1, p.dram_bytes_per_cycle)))
                    dram_next_cycle = bus_start + bus_cycles
                    latency = max(latency, wait + mem_lat, bus_wait + mem_lat + bus_cycles)
            slots[slot] = cycle + 1
            issued[seq] = True
            ready_at[seq] = cycle + latency
            if kind in ("LOAD", "STORE"):
                stalls["memory_latency_exposure_cycles"] += max(0, latency - 1)
            issued_this_cycle += 1
            if kind == "BR":
                branch_number += 1
                if branch_number % 4 == 0:
                    branch_misses += 1
                    frontend_blocked_until = max(frontend_blocked_until, cycle + p.branch_penalty)
        cycle += 1
    if retired != len(ops):
        raise RuntimeError(f"simulation did not drain: retired {retired}/{len(ops)}")
    return {
        "cycles": cycle, "ops": len(ops), "ipc": round(len(ops)/max(1,cycle), 3),
        "max_rob_occupancy": max_rob, "branch_mispredicts": branch_misses,
        "cache_accesses": hits, "stall_counters": stalls
    }

def partition_dependency_components(ops: List[Op], core_count: int) -> List[List[Op]]:
    """Pack independent dependency components onto cores without breaking dependencies."""
    adjacency = [[] for _ in ops]
    for op in ops:
        for dep in op.deps:
            adjacency[op.seq].append(dep)
            adjacency[dep].append(op.seq)
    seen = set()
    components = []
    for root in range(len(ops)):
        if root in seen:
            continue
        stack = [root]
        seen.add(root)
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for nxt in adjacency[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(sorted(component))
    components.sort(key=len, reverse=True)
    bins = [[] for _ in range(max(1, core_count))]
    loads = [0] * len(bins)
    for component in components:
        target = min(range(len(bins)), key=lambda i: loads[i])
        bins[target].extend(component)
        loads[target] += len(component)
    shards = []
    for indices in bins:
        indices.sort()
        remap = {old: new for new, old in enumerate(indices)}
        shard = []
        for new_seq, old_seq in enumerate(indices):
            op = ops[old_seq]
            shard.append(Op(new_seq, op.kind,
                            tuple(remap[d] for d in op.deps if d in remap),
                            op.address, op.width, op.label, op.command_address))
        if shard:
            shards.append(shard)
    return shards

def simulate_multicore_streams(shards: List[List[Op]], p: CoreProfile,
                               aggregate_dram_bandwidth: int,
                               nexus_features=None) -> dict:
    """Lockstep cores sharing one DRAM bank/bus controller.

    Per-core pipelines, ROBs and caches remain private approximations. All
    cores advance on one global cycle and submit DRAM misses as a same-cycle batch.
    """
    features = {"spm": True, "p0": True}
    if nexus_features:
        features.update(nexus_features)
    is_nexus = p.name.startswith("NEXSUS CPU")
    states = []
    for shard in shards:
        states.append({
            "ops": shard, "cache": None, "fetch": None,\n            "spm_busy_until": 0,\n            "spm": {"accesses": 0, "bytes": 0, "port_conflicts": 0, "overflow": 0, "fallback_bytes": 0},
            "ready_at": [0] * len(shard), "done": [False] * len(shard),
            "issued": [False] * len(shard), "dispatched": [False] * len(shard),
            "rob": deque(), "unit_busy": {k: [0] * v for k, v in p.units.items()},
            "next_frontend": 0, "frontend_blocked_until": 0, "retired": 0,
            "max_rob": 0, "hits": {"L1":0,"L2":0,"L3":0,"L4":0,"DRAM":0},
            "branch_misses": 0, "branch_number": 0,
            "stalls": {"dependency_blocked_op_cycles": 0,
                       "issue_width_blocked_op_cycles": 0,
                       "execution_unit_blocked_op_cycles": 0,
                       "frontend_limited_cycles": 0, "rob_full_cycles": 0,
                       "branch_recovery_cycles": 0,
                       "memory_latency_exposure_cycles": 0}
        })
    cache_hierarchies = build_cache_hierarchies(p, len(states))
    for core_id, st in enumerate(states):
        st["cache"] = cache_hierarchies[core_id]
        if is_nexus:
            st["fetch"] = CommandFetchModel(bool(features["p0"]))
    pending_fills = []
    controller = SharedMemoryController(
        bank_count=p.bank_count, beat_bytes=p.bank_beat_bytes,
        aggregate_bytes_per_cycle=aggregate_dram_bandwidth)
    cycle = 0
    limit = max(10000, sum(len(x) for x in shards) * 1000)
    while any(st["retired"] < len(st["ops"]) for st in states) and cycle < limit:
        for st in states:
            if st["fetch"] is not None:
                st["fetch"].complete(cycle)
        completed_fills = [x for x in pending_fills if x[0] <= cycle]
        pending_fills = [x for x in pending_fills if x[0] > cycle]
        for _, core_id, address, level in completed_fills:
            states[core_id]["cache"].fill(address, level)
        pending_memory = []
        # Phase 1: complete and retire all cores at the same global cycle.
        for core_id, st in enumerate(states):
            ops = st["ops"]
            for op in ops:
                if st["issued"][op.seq] and not st["done"][op.seq] and st["ready_at"][op.seq] <= cycle:
                    st["done"][op.seq] = True
            retired_now = 0
            while st["rob"] and retired_now < p.retire and st["done"][st["rob"][0]]:
                st["rob"].popleft()
                st["retired"] += 1
                retired_now += 1

        # Phase 2: dispatch independently on each core.
        for st in states:
            ops = st["ops"]
            if st["next_frontend"] < len(ops):
                if cycle < st["frontend_blocked_until"]:
                    st["stalls"]["branch_recovery_cycles"] += 1
                elif len(st["rob"]) >= p.rob:
                    st["stalls"]["rob_full_cycles"] += 1
            dispatched_now = 0
            while (st["next_frontend"] < len(ops) and dispatched_now < p.dispatch and
                   dispatched_now < p.frontend and len(st["rob"]) < p.rob and
                   cycle >= st["frontend_blocked_until"]):
                op = ops[st["next_frontend"]]
                if st["fetch"] is not None:
                    pc = op.command_address if op.command_address >= 0 else op.seq * 8
                    if not st["fetch"].can_fetch(pc, cycle):
                        break
                st["dispatched"][op.seq] = True
                st["rob"].append(op.seq)
                st["next_frontend"] += 1
                dispatched_now += 1
            st["max_rob"] = max(st["max_rob"], len(st["rob"]))
            if (st["next_frontend"] < len(ops) and
                cycle >= st["frontend_blocked_until"] and len(st["rob"]) < p.rob and
                dispatched_now >= min(p.dispatch, p.frontend)):
                st["stalls"]["frontend_limited_cycles"] += 1

        # Phase 3: choose per-core issue candidates. DRAM misses are deferred
        # until every core has contributed its requests for this same cycle.
        for core_id, st in enumerate(states):
            ops = st["ops"]
            issued_now = 0
            for seq in list(st["rob"]):
                if st["issued"][seq]:
                    continue
                op = ops[seq]
                if any(not st["done"][dep] for dep in op.deps):
                    st["stalls"]["dependency_blocked_op_cycles"] += 1
                    continue
                if issued_now >= p.issue:
                    st["stalls"]["issue_width_blocked_op_cycles"] += 1
                    continue
                resource = "LOAD" if op.kind == "LOAD" else ("STORE" if op.kind == "STORE" else op.kind)
                slots = st["unit_busy"].get(resource, [])
                slot = next((i for i, available in enumerate(slots) if available <= cycle), None)
                if slot is None:
                    st["stalls"]["execution_unit_blocked_op_cycles"] += 1
                    continue
                mem_lat = 0
                level = None
                if op.kind in ("LOAD", "STORE"):
                    is_spm2 = op.label.startswith("SPM2:")
                    in_spm = 0 <= op.address and op.address + op.width <= 8192
                    if is_nexus and features["spm"] and is_spm2 and in_spm:
                        if st["spm_busy_until"] > cycle:
                            st["spm"]["port_conflicts"] += 1
                            mem_lat = (st["spm_busy_until"] - cycle) + 2
                        else:
                            mem_lat = 2
                        st["spm_busy_until"] = max(st["spm_busy_until"], cycle) + 1
                        st["spm"]["accesses"] += 1
                        st["spm"]["bytes"] += op.width
                        level = "SPM2"
                    else:
                        if is_nexus and is_spm2:
                            if features["spm"] and not in_spm:
                                st["spm"]["overflow"] += 1
                            st["spm"]["fallback_bytes"] += op.width
                        mem_lat, level = st["cache"].probe(op.address)
                        st["hits"][level] += 1
                item = {"core": core_id, "seq": seq, "slot": slot,
                        "latency": max(p.latency.get(op.kind, 1), mem_lat),
                        "level": level}
                if level == "DRAM":
                    item["request_id"] = f"{core_id}:{seq}"
                    pending_memory.append({
                        "id": item["request_id"], "core": core_id,
                        "address": op.address, "width": op.width
                    })
                else:
                    item["request_id"] = None
                # Mark as selected now; completion timing is finalized below.
                st["issued"][seq] = True
                slots[slot] = cycle + 1
                item["branch"] = op.kind == "BR"
                item["memory"] = op.kind in ("LOAD", "STORE")
                pending_memory.append({"_issue": item})
                issued_now += 1

        # Phase 4: one global arbitration call for all DRAM misses selected
        # across all cores this cycle.
        requests = [x for x in pending_memory if "_issue" not in x]
        reservations = controller.reserve_batch(cycle, requests, p.bank_hash) if requests else {}
        for entry in pending_memory:
            if "_issue" not in entry:
                continue
            item = entry["_issue"]
            st = states[item["core"]]
            seq = item["seq"]
            latency = item["latency"]
            if item["request_id"] is not None:
                reservation = reservations[item["request_id"]]
                beats = max(1, math.ceil(st["ops"][seq].width / p.bank_beat_bytes))
                service_delay = max(
                    reservation["bank_wait"],
                    reservation["bus_wait"] + max(0, reservation["bus_service_cycles"] - 1)
                )
                latency = max(latency, p.dram_lat + service_delay)
            st["ready_at"][seq] = cycle + latency
            if item["memory"]:
                pending_fills.append((cycle + latency, item["core"], st["ops"][seq].address, item["level"]))
                st["stalls"]["memory_latency_exposure_cycles"] += max(0, latency - 1)
            if item["branch"]:
                st["branch_number"] += 1
                if st["branch_number"] % 4 == 0:
                    st["branch_misses"] += 1
                    st["frontend_blocked_until"] = max(
                        st["frontend_blocked_until"], cycle + p.branch_penalty)

        cycle += 1

    if any(st["retired"] != len(st["ops"]) for st in states):
        totals = [f"{st['retired']}/{len(st['ops'])}" for st in states]
        raise RuntimeError(f"multicore simulation did not drain at cycle {cycle}: {totals}")
    return {"cycles": cycle, "cores": states,
            "controller": {"bank_count": p.bank_count,
                           "aggregate_dram_bytes_per_cycle": aggregate_dram_bandwidth,
                           "bank_busy_until": controller.bank_busy,
                           "bus_next_cycle": controller.bus_next_cycle}}


def simulate_cpu(workloads: Dict[str,List[Op]], profile_dict: dict, core_count=None,
                 nexus_features=None) -> dict:
    cores = core_count or profile_dict.get("core_count", 1)
    core_profile_dict = dict(profile_dict)
    aggregate_dram_bandwidth = int(profile_dict.get("dram_bytes_per_cycle", 32))
    p = profile_from_dict(core_profile_dict)
    results = {}
    for name, ops in workloads.items():
        shards = partition_dependency_components(ops, cores)
        simulation = simulate_multicore_streams(shards, p, aggregate_dram_bandwidth, nexus_features)
        per_core = simulation["cores"]
        elapsed_cycles = simulation["cycles"]
        total_ops = sum(x["retired"] for x in per_core)
        cache_totals = {k: sum(x["hits"][k] for x in per_core)
                        for k in ("L1", "L2", "L3", "L4", "DRAM")}
        stall_keys = list(per_core[0]["stalls"]) if per_core else []
        results[name] = {
            "cycles": elapsed_cycles, "ops": total_ops,
            "aggregate_ipc": round(total_ops/max(1, elapsed_cycles), 3),
            "core_cycles_sum": elapsed_cycles * len(per_core),
            "active_cores": len(per_core),
            "per_core_cycles": [elapsed_cycles for _ in per_core],
            "max_rob_occupancy": max((x["max_rob"] for x in per_core), default=0),
            "branch_mispredicts": sum(x["branch_misses"] for x in per_core),
            "cache_accesses": cache_totals,
            "stall_counters": {k: sum(x["stalls"][k] for x in per_core)
                               for k in stall_keys},
            "memory_controller": simulation["controller"],
            "spm_counters": {k: sum(x["spm"][k] for x in per_core)
                             for k in ("accesses", "bytes", "port_conflicts", "overflow", "fallback_bytes")},
            "p0_counters": {
                "hits": sum(x["fetch"].hits for x in per_core if x["fetch"] is not None),
                "refills": sum(x["fetch"].refills for x in per_core if x["fetch"] is not None),
                "refill_bytes": sum(x["fetch"].refill_bytes for x in per_core if x["fetch"] is not None),
                "wait_cycles": sum(x["fetch"].wait_cycles for x in per_core if x["fetch"] is not None),
                "mode": ("P0" if nexus_features is None or nexus_features.get("p0", True) else "conventional I-cache") if p.name.startswith("NEXSUS CPU") else "reference profile"
            },
            "parallel_model": "lockstep multicore; private L1; NEXSUS L2 shared per 2 cores, L3 per 4 and L4 per 8; reference CPU caches remain per-core approximations; shared DRAM banks and work-conserving aggregate bus; coherence not modeled"
        }
    total_cycles = sum(v["cycles"] for v in results.values())
    total_ops = sum(v["ops"] for v in results.values())
    return {"cpu": p.name, "cores_configured": cores, "clock_ghz": p.frequency_ghz,
            "nexus_features": ({"spm": True, "p0": True} if nexus_features is None else nexus_features) if p.name.startswith("NEXSUS CPU") else None,
            "cpu_ram_reference_clock_ghz": p.frequency_ghz,
            "aggregate_dram_bytes_per_cycle": aggregate_dram_bandwidth,
            "per_core_dram_bytes_per_cycle": None,
            "dram_bandwidth_policy": "shared lockstep controller; work-conserving aggregate bus; no static per-core quota",
            "kernels": results, "total_cycles": total_cycles, "total_ops": total_ops,
            "aggregate_ipc": round(total_ops/max(1,total_cycles),3),
            "time_ms_at_configured_clock": round(total_cycles/(p.frequency_ghz*1e6),6)}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--nexus-cores", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    workloads = build_composite_workload(args.scale)
    profiles = {}
    for key in ("amd_9950x","intel_285k_p","intel_285k_e"):
        profiles[key] = simulate_cpu(workloads, PROFILES[key])
    for key in ("nexus_balanced_128",):
        profiles[key] = simulate_cpu(workloads, PROFILES[key], max(8, args.nexus_cores))
    if args.json:
        print(json.dumps(profiles, indent=2))
        return
    print("NEXSUS CPU COMPOSITE WORKLOAD — CONTROLLED 8-CORE MODEL v0.2.4-dev")
    print("All targets: 8 cores, 3.0 GHz reference clock, 120-cycle DRAM latency, 32 B/cycle chip-wide DRAM ceiling; work-conserving shared controller.")
    print("Parallelism: lockstep cores; NEXSUS private L1 and shared L2/2-core, L3/4-core, L4/8-core groups; shared DRAM banks and aggregate bus; coherence remains unmodeled.")
    print(f"{'CPU profile':48} {'cycles':>12} {'ops':>10} {'IPC':>8} {'time ms*':>12}")
    for result in profiles.values():
        print(f"{result['cpu'][:48]:48} {result['total_cycles']:12d} {result['total_ops']:10d} "
              f"{result['aggregate_ipc']:8.3f} {result['time_ms_at_configured_clock']:12.6f}")
    print("\nPER-KERNEL BREAKDOWN")
    for key, result in profiles.items():
        print(f"\n[{result['cpu']}]")
        print(f"{'kernel':22} {'cycles':>10} {'ops':>9} {'IPC':>8} {'cores':>7} {'DRAM':>8}")
        for name, kernel in result["kernels"].items():
            print(f"{name:22} {kernel['cycles']:10d} {kernel['ops']:9d} "
                  f"{kernel['aggregate_ipc']:8.3f} {kernel['active_cores']:7d} "
                  f"{kernel['cache_accesses']['DRAM']:8d}")
    print("\nSTALL COUNTERS (blocked operation-cycle events and cycle counters; not additive wall-clock time)")
    for key, result in profiles.items():
        print(f"\n[{result['cpu']}]")
        print(f"{'kernel':22} {'dep-opcy':>10} {'issue-opcy':>11} {'unit-opcy':>10} {'front-cy':>9} {'ROB-cy':>8} {'branch-cy':>10} {'mem-exp':>10}")
        for name, kernel in result["kernels"].items():
            c = kernel["stall_counters"]
            print(f"{name:22} {c['dependency_blocked_op_cycles']:10d} {c['issue_width_blocked_op_cycles']:11d} "
                  f"{c['execution_unit_blocked_op_cycles']:10d} {c['frontend_limited_cycles']:9d} "
                  f"{c['rob_full_cycles']:8d} {c['branch_recovery_cycles']:10d} "
                  f"{c['memory_latency_exposure_cycles']:10d}")
    print("*Time uses configured reference clock, not measured sustained turbo.")

if __name__ == "__main__":
    main()
