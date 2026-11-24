#!/usr/bin/env python3
"""NEXSUS CPU comparison simulator — native-profile model v0.3.2-dev (CS pool + dual-bank EB + page metadata)

This is an event/cycle-level teaching and design-space model, not RTL, gem5,
or a vendor-certified replica. Unknown NEXSUS parameters are explicit inputs.
"""
from __future__ import annotations
import argparse
import json
import math
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class Op:
    seq: int
    kind: str
    deps: Tuple[int, ...] = ()
    address: int = 0
    width: int = 8
    label: str = ""
    command_address: int = -1
    exec_width_bits: int = 64
    rac_reads: Optional[int] = None
    rac_writes: Optional[int] = None
    rac_read_accesses: Optional[Tuple[Tuple[str, int, int], ...]] = None
    rac_write_accesses: Optional[Tuple[Tuple[str, int, int], ...]] = None

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
    branch_predictor: str = "modern_assumed"
    vector_bits: int = 128
    matrix_unit: str = "VEC"
    execution_topology: dict = field(default_factory=dict)
    app_ram_bytes_per_cycle_per_core: int = 64
    data_ram_bytes_per_cycle_per_core: int = 0
    app_ram_bank_count_per_group: int = 8
    data_ram_bank_count_per_group: int = 8
    memory_bank_slice_bits: int = 64
    memory_bank_group_width_bits: int = 512
    memory_fabric_shared: bool = False
    cache_grouping: dict = field(default_factory=dict)
    scheduler_entries: int = 0  # 0 keeps the legacy ROB-sized scheduling window
    rac_read_budget: int = 0  # logical 64-bit slots/core/cycle; 0 disables RAC model
    rac_write_budget: int = 0
    # Legacy per-register-class port limits; retained for NEX-T017 compatibility.
    rac_physical_read_ports: Optional[Dict[str, int]] = None
    rac_physical_write_ports: Optional[Dict[str, int]] = None
    # NEX-T018: register index maps to index % bank_count.
    rac_physical_bank_counts: Optional[Dict[str, int]] = None
    rac_physical_read_ports_per_bank: Optional[Dict[str, int]] = None
    rac_physical_write_ports_per_bank: Optional[Dict[str, int]] = None

# Publicly documented or independently measured values are marked in docs.
# Unpublished/uncertain values are conservative model assumptions, not claims.
PROFILES = {
    "amd_9950x3d2": {
        "name": "AMD Ryzen 9 9950X3D2 Dual Edition / Zen 5",
        "core_count": 16, "core_type": "uniform", "frontend": 4,
        "dispatch": 8, "issue": 8, "retire": 8, "rob": 448,
        "units": {"INT": 6, "FP": 4, "VEC": 2, "LOAD": 4, "STORE": 2, "BR": 1, "CTX": 1, "ATOM": 1, "IRQ": 1},
        "latency": {"INT": 1, "FP": 3, "VEC": 3, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 8, "CTX": 8, "IRQ": 12},
        "l1_kb": 48, "l2_kb": 1024, "l3_kb": 196608, "l4_kb": 0,
        "l1_lat": 4, "l2_lat": 14, "l3_lat": 48, "l4_lat": 0, "dram_lat": 120,
        "branch_penalty": 15, "frequency_ghz": 4.3, "dram_bytes_per_cycle": 21, "vector_bits": 512, "matrix_unit": "VEC"
    },
    "intel_xeon_698x": {
        "name": "Intel Xeon 698X / Redwood Cove+",
        "core_count": 86, "core_type": "uniform", "frontend": 6,
        "dispatch": 8, "issue": 8, "retire": 8, "rob": 512,
        "units": {"INT": 6, "FP": 4, "VEC": 2, "AMX": 1, "LOAD": 4, "STORE": 2, "BR": 1, "CTX": 1, "ATOM": 1, "IRQ": 1},
        "latency": {"INT": 1, "FP": 4, "VEC": 3, "AMX": 2, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 10, "CTX": 8, "IRQ": 14},
        "l1_kb": 48, "l2_kb": 2048, "l3_kb": 344064, "l4_kb": 0,
        "l1_lat": 4, "l2_lat": 16, "l3_lat": 60, "l4_lat": 0, "dram_lat": 150,
        "branch_penalty": 16, "frequency_ghz": 2.0, "dram_bytes_per_cycle": 160, "vector_bits": 512, "matrix_unit": "AMX",
        "branch_predictor": "modern_assumed"
    },
    "apple_m6": {
        "name": "Apple M6 / 12-core ARM SoC (heterogeneous approximation)",
        "core_count": 12, "core_type": "uniform", "frontend": 6,
        "dispatch": 8, "issue": 8, "retire": 8, "rob": 384,
        "units": {"INT": 6, "FP": 4, "VEC": 2, "LOAD": 4, "STORE": 2, "BR": 1, "CTX": 1, "ATOM": 1, "IRQ": 1},
        "latency": {"INT": 1, "FP": 3, "VEC": 2, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 8, "CTX": 6, "IRQ": 10},
        "l1_kb": 64, "l2_kb": 4096, "l3_kb": 24576, "l4_kb": 0,
        "l1_lat": 3, "l2_lat": 12, "l3_lat": 36, "l4_lat": 0, "dram_lat": 100,
        "branch_penalty": 12, "frequency_ghz": 3.0, "dram_bytes_per_cycle": 48, "vector_bits": 128, "matrix_unit": "VEC"
    },
    "nexus_balanced_128": {
        "name": "NEXSUS CPU / 8-core proposed architecture",
        "core_count": 8, "core_type": "uniform", "frontend": 8,
        "dispatch": 8, "issue": 16, "retire": 8, "rob": 512, "scheduler_entries": 256,
        "rac_read_budget": 80, "rac_write_budget": 64,
        "units": {"ARITH": 8, "LOGIC": 8, "CMP": 8, "FP": 6, "FMA": 4, "VEC": 2, "LOAD": 8, "STORE": 4, "BR": 2, "CTX": 1, "ATOM": 1, "ME512": 1, "IRQ": 1},
        "execution_topology": {"ARITH128_PAIRS": [[0, 1], [2, 3]]},
        "latency": {"ARITH": 1, "LOGIC": 1, "CMP": 1, "FP": 3, "FMA": 4, "VEC": 2, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 8, "CTX": 4, "ME512": 4, "IRQ": 6},
        "l1_kb": 1024, "l2_kb": 2048, "l3_kb": 8192, "l4_kb": 65536,
        "l1_lat": 2, "l2_lat": 8, "l3_lat": 24, "l4_lat": 64, "dram_lat": 120,
        "branch_penalty": 8, "frequency_ghz": 3.0, "bank_hash": "folded", "dram_bytes_per_cycle": 512,
        "branch_predictor": "small_2bit", "vector_bits": 512, "matrix_unit": "ME512",
        "app_ram_bytes_per_cycle_per_core": 64, "data_ram_bytes_per_cycle_per_core": 64,
        "app_ram_bank_count_per_group": 8, "data_ram_bank_count_per_group": 8,
        "memory_bank_slice_bits": 64, "memory_bank_group_width_bits": 512,
        "memory_fabric_shared": True,
        "cache_grouping": {"l1_cores_per_group": 1, "l2_cores_per_group": 2,
                           "l3_cores_per_group": 4, "l4_cores_per_group": 8}
    }
}

def add_op(ops: List[Op], kind: str, deps=(), address=0, width=8, label="", command_address=None,
           exec_width_bits=64):
    seq = len(ops)
    pc = -1 if command_address is None else command_address
    ops.append(Op(seq, kind, tuple(dict.fromkeys(deps)), address, width, label, pc,
                  exec_width_bits))
    return seq

def execution_resource_kind(kind: str, matrix_unit: str, available_units=None) -> str:
    """Map operation classes to independent physical execution pools.

    INT remains a compatibility alias for Arithmetic ALU. Reference profiles
    without split scalar pools continue to use their generic INT resource.
    """
    if kind == "FMA":
        return "FMA"
    if kind == "ME512":
        return matrix_unit
    if kind.startswith("VEC_"):
        return "VEC"
    if kind == "INT" and available_units is not None and "ARITH" in available_units:
        return "ARITH"
    return kind


def is_vector_operation(kind: str) -> bool:
    return kind == "VEC" or kind.startswith("VEC_")


def rac_operand_footprint(op: Op, profile: CoreProfile) -> Tuple[int, int]:
    """Return this operation's logical RAC read/write slots.

    NEXSUS budgets count 64-bit lanes. Explicit per-op overrides are preferred
    for unusual opcodes. Default ME512 footprints use one 512-bit slice per
    operand per cycle; full tile reservation is tracked separately by ISA.
    """
    if profile.rac_read_budget <= 0 and profile.rac_write_budget <= 0:
        return 0, 0
    if op.rac_reads is not None or op.rac_writes is not None:
        return max(0, op.rac_reads or 0), max(0, op.rac_writes or 0)

    kind = op.kind.upper()
    lanes = max(1, math.ceil(op.exec_width_bits / 64))
    if kind in ("INT", "ARITH", "LOGIC", "CMP", "FP"):
        return 2 * lanes, lanes
    if kind == "FMA":
        return 3 * lanes, lanes
    if is_vector_operation(kind):
        return 2 * lanes, lanes
    if kind == "ME512":
        label = op.label.upper()
        if "MMAC" in label:
            return 24, 8
        if "MTRANS" in label or "MREDUCE" in label:
            return 8, 8
        return 16, 8
    if kind == "LOAD":
        return 0, max(1, math.ceil(op.width / 8))
    if kind == "STORE":
        return max(1, math.ceil(op.width / 8)), 0
    if kind == "ATOM":
        slots = max(1, math.ceil(op.width / 8))
        return slots, slots
    if kind in ("WLOAD", "WSTORE"):
        slots = max(1, math.ceil(op.width / 8))
        return slots, slots
    return 0, 0


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

    # F2) Independent 128-bit integer throughput for mixed-width ALU testing.
    ops = []
    for i in range(256*n):
        add_op(ops, "INT", label="independent 128-bit integer throughput",
               exec_width_bits=128)
    result["integer128_throughput"] = ops

    # G) Independent FP throughput: isolates floating-point execution resources.
    ops = []
    for i in range(512*n):
        add_op(ops, "FP", label="independent floating-point throughput")
    result["fp_throughput"] = ops

    # G2) Dedicated fused multiply-add workload.
    ops = []
    for i in range(512*n):
        add_op(ops, "FMA", label="independent fused multiply-add throughput")
    result["fma_throughput"] = ops

    # G2b) Serial dependency chain: isolates FMA latency from issue throughput.
    ops = []
    previous = None
    for i in range(256*n):
        previous = add_op(
            ops, "FMA", () if previous is None else (previous,),
            label="dependent fused multiply-add chain",
        )
    result["fma_dependency_chain"] = ops

    # G3) Concurrent FP64 + dedicated FMA issue pressure. Equal independent
    # streams test independent execution pools under the global issue limit.
    ops = []
    for i in range(256*n):
        add_op(ops, "FP", label="mixed FP64/FMA ordinary FP stream")
        add_op(ops, "FMA", label="mixed FP64/FMA fused stream")
    result["fp_fma_mixed"] = ops

    # H) Independent 512-bit vector arithmetic mix. Each opcode uses the VEC
    # issue resource; dependency chains are kept separate from issue throughput.
    ops = []
    vector_kinds = ("VEC_ADD", "VEC_SUB", "VEC_MUL", "VEC_FMA", "VEC_PERMUTE", "VEC_REDUCE")
    for i in range(256*n):
        add_op(ops, vector_kinds[i % len(vector_kinds)],
               label="independent 512-bit vector arithmetic",
               exec_width_bits=512)
    result["vector_throughput"] = ops

    # H0) Per-opcode dependency chains isolate result-forwarding latency.
    # These intentionally contain no memory operations.
    for vector_kind in vector_kinds:
        ops = []
        previous = None
        for i in range(64*n):
            previous = add_op(
                ops, vector_kind, () if previous is None else (previous,),
                label=f"{vector_kind} dependent result chain", exec_width_bits=512,
            )
        result[f"{vector_kind.lower()}_dependency_chain"] = ops

    # H1) Per-operation vector arithmetic streams expose opcode-specific counts.
    for vector_kind in vector_kinds:
        ops = []
        for i in range(128*n):
            add_op(ops, vector_kind, label=f"{vector_kind} independent throughput",
                   exec_width_bits=512)
        result[vector_kind.lower()] = ops

    # H2) ME512 tiled matrix multiply-accumulate. Each tile consumes A/B
    # operands across K steps and chains the partial accumulator before store.
    # This models a 512-bit tile MAC operation, not a finalized matrix ISA.
    ops = []
    tile_count = 16*n
    k_steps = 8
    for tile in range(tile_count):
        accumulator = None
        for k in range(k_steps):
            a = add_op(ops, "LOAD", (), 0x5000000 + (tile*k_steps+k)*128,
                       64, "ME512 matrix A tile")
            b = add_op(ops, "LOAD", (), 0x6000000 + (tile*k_steps+k)*128,
                       64, "ME512 matrix B tile")
            deps = (a, b) if accumulator is None else (a, b, accumulator)
            accumulator = add_op(
                ops, "ME512", deps, width=64,
                label="ME512 512-bit tile multiply-accumulate",
                exec_width_bits=512,
            )
        add_op(ops, "STORE", (accumulator,),
               0x7000000 + tile*128, 64, "ME512 accumulated matrix tile")
    result["me512_matrix"] = ops

    # H2a) Operand-resident ME512 issue throughput: no LOAD/STORE operations.
    ops = []
    for i in range(128*n):
        add_op(ops, "ME512", label="independent ME512 tile MAC", exec_width_bits=512)
    result["me512_independent_throughput"] = ops

    # H2b) Operand-resident accumulator recurrence isolates ME512 result latency.
    ops = []
    previous = None
    for i in range(128*n):
        previous = add_op(
            ops, "ME512", () if previous is None else (previous,),
            label="dependent ME512 accumulator chain", exec_width_bits=512,
        )
    result["me512_dependency_chain"] = ops

    # H2c) Mixed VEC + ME512 + memory stream with real operand dependencies.
    # Both execution units consume each loaded operand; stores wait for both
    # arithmetic results. This exposes cache/DRAM feed latency and resource overlap.
    ops = []
    for i in range(128*n):
        load = add_op(ops, "LOAD", address=0xA000000 + (i % 256) * 64,
                      width=64, label="mixed Data RAM operand load")
        vec = add_op(ops, "VEC_ADD", (load,), label="mixed VEC arithmetic",
                     exec_width_bits=512)
        me512 = add_op(ops, "ME512", (load,), label="mixed ME512 tile MAC",
                       exec_width_bits=512)
        if i % 2 == 0:
            add_op(ops, "STORE", (vec, me512),
                   address=0xB000000 + (i % 128) * 64,
                   width=64, label="mixed Data RAM result store")
    result["vec_me512_memory_overlap"] = ops

    # H3) Atomic read-modify-write contention on a small shared address set.
    ops = []
    for i in range(256*n):
        add_op(ops, "ATOM", address=0x7800000 + (i % 8)*8, width=8,
               label="shared atomic counter contention")
    result["atomic_contention"] = ops

    # H4) Deterministic IRQ/exception service proxy with context entry/exit.
    ops = []
    for event in range(64*n):
        work = add_op(ops, "INT", label="pre-interrupt work")
        irq = add_op(ops, "IRQ", (work,), label="IRQ/exception entry service")
        ctx = add_op(ops, "CTX", (irq,), label="interrupt context frame")
        add_op(ops, "INT", (ctx,), label="post-interrupt return work")
    result["irq_exception_stress"] = ops

    # I) Branch-heavy independent control flow to expose recovery penalties.
    ops = []
    for i in range(256*n):
        add_op(ops, "BR", label="independent branch stress")
    result["branch_stress"] = ops

    # J) Dependent pointer chain repeatedly visits a 4 KiB TW-resident set.
    ops = []
    previous = None
    for i in range(512*n):
        previous = add_op(ops, "LOAD", () if previous is None else (previous,),
                          address=(i % 64) * 64, width=64,
                          label="TW: dependent hot task working set")
    result["tw_hot_workset"] = ops

    # K) Dependent chain covers 16 KiB: half fits TW, half uses Data RAM.
    ops = []
    previous = None
    for i in range(512*n):
        previous = add_op(ops, "LOAD", () if previous is None else (previous,),
                          address=(i % 256) * 64, width=64,
                          label="TW: dependent capacity sweep")
    result["tw_capacity_sweep"] = ops

    # L) Sequential command supply; one unique command address per operation.
    ops = []
    for i in range(2048*n):
        add_op(ops, "INT", label="CS sequential", command_address=i*8)
    result["cs_sequential"] = ops

    # M) Branch-heavy command stream; branch recovery remains independently modeled.
    ops = []
    for i in range(2048*n):
        add_op(ops, "BR", label="CS branch", command_address=i*8)
    result["cs_branch"] = ops

    # N) Repeated 2 KiB command loop (fits one CS slot and conventional I-cache).
    ops = []
    for i in range(4096*n):
        add_op(ops, "INT", label="CS working set", command_address=(i % 256)*8)
    result["cs_working_set"] = ops

    # O) One sequential pass over 64 KiB of commands: exceeds the 16 KiB CS pool and 32 KiB reference I-cache.
    ops = []
    # 8 KiB instructions = 64 KiB code: 4x the 16 KiB CS pool and 2x the 32 KiB reference I-cache.
    for i in range(8192*n):
        add_op(ops, "INT", label="CS starvation", command_address=i*8)
    result["cs_starvation"] = ops

    return result

class CachePort:
    """Parameterized cache request port; defaults are provisional design assumptions.

    One port admits one cache-line request per cycle. Wider requests reserve
    proportionally more service cycles. Shared cache objects share this port.
    """
    def __init__(self, ports: int = 1, lines_per_port_cycle: int = 1):
        if ports < 1 or lines_per_port_cycle < 1:
            raise ValueError("cache ports and line service rate must be positive")
        self.ports = ports
        self.lines_per_port_cycle = lines_per_port_cycle
        self.next_cycle = [0] * ports
        self.requests = 0
        self.wait_cycles = 0

    def reserve(self, cycle: int, width_bytes: int, line_bytes: int = 64) -> int:
        lines = max(1, math.ceil(max(1, width_bytes) / line_bytes))
        service = max(1, math.ceil(lines / self.lines_per_port_cycle))
        slot = min(range(self.ports), key=lambda i: self.next_cycle[i])
        start = max(cycle, self.next_cycle[slot])
        wait = start - cycle
        self.next_cycle[slot] = start + service
        self.requests += 1
        self.wait_cycles += wait
        return wait


class LRU:
    def __init__(self, capacity_bytes: int, line_bytes: int):
        self.capacity = max(1, capacity_bytes // line_bytes)
        self.lines = OrderedDict()
        self.port = CachePort()
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

    def reserve(self, level: str, cycle: int, width_bytes: int = 8) -> int:
        """Reserve a request on the selected level's shared port."""
        target = getattr(self, level.lower(), None)
        if target is None:
            raise ValueError(f"Cannot reserve {level}: cache level is unavailable")
        return target.port.reserve(cycle, width_bytes, self.line)

    def prefill(self, address: int, level: str):
        """Place an untimed shared working-set line at its chosen group level."""
        targets = {"L1": self.l1, "L2": self.l2,
                   "L3": self.l3, "L4": self.l4}
        target = targets.get(level)
        if target is None:
            raise ValueError(f"Cannot prefill {level}: cache level is unavailable")
        target.insert(address // self.line)

    def fill(self, address: int, level: str, active_core_count: int = 1,
             peer_caches: Optional[List["CacheHierarchy"]] = None,
             core_id: int = 0, active_core_ids: Optional[List[int]] = None):
        """Complete a demand fill using NEXSUS' direct L4-to-active-group distribution.

        NEXSUS does not cascade L4->L3->L2->L1. A DRAM miss first installs
        the line in the shared L4 home, then distributes directly to the
        cache level shared by the active cooperating group:
          8 cores -> each private L1 (parallel destinations)
          4 cores -> their shared L3
          2 cores -> their shared L2
          1 core  -> its private L1
        Other architectures retain the conventional inclusive fill behavior.
        """
        line = address // self.line
        if self.p.name.startswith("NEXSUS CPU"):
            if level == "DRAM":
                if self.l4 is None:
                    raise ValueError("NEXSUS DataRAM miss requires a shared L4 home")
                self.l4.insert(line)
            participants = sorted(set(active_core_ids or [core_id]))
            active = len(participants)
            # Sharing is inferred only when those cores requested this same
            # line together; merely having 8 cores configured is not enough.
            if active >= 8 and participants == list(range(8)):
                if peer_caches is None or len(peer_caches) < 8:
                    raise ValueError("8-core L4 distribution requires all eight destination caches")
                # One completion event fans out to all eight private L1s.
                for destination in peer_caches[:8]:
                    destination.l1.insert(line)
            elif active >= 4 and participants == list(range((participants[0] // 4) * 4,
                                                             (participants[0] // 4) * 4 + 4)):
                self.l3.insert(line)
            elif active >= 2 and participants == list(range((participants[0] // 2) * 2,
                                                             (participants[0] // 2) * 2 + 2)):
                self.l2.insert(line)
            else:
                # No complete aligned sharing group: keep the line private
                # to the participating cores rather than broadcasting system-wide.
                if peer_caches is not None:
                    for participant in participants:
                        peer_caches[participant].l1.insert(line)
                else:
                    self.l1.insert(line)
            return

        # Conventional reference-CPU inclusive allocation model.
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


def distribute_memory_to_l4(caches: List[CacheHierarchy], addresses: List[int],
                            mode: str = "partitioned",
                            target_blocks: Optional[List[int]] = None) -> Dict[int, int]:
    """Untimed setup: place memory-sourced lines directly in selected L4 homes.

    This models destination/visibility placement only, not transfer cycles or
    bandwidth. Each eight-core block owns one L4 home. Partitioned mode assigns
    successive lines round-robin across selected blocks; replicated/selective
    modes install every line in each selected block's L4.
    """
    if not caches:
        raise ValueError("Cannot distribute to L4: no core cache hierarchies supplied")
    block_count = math.ceil(len(caches) / 8)
    selected = list(range(block_count)) if target_blocks is None else list(target_blocks)
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("target_blocks must contain unique valid L4 block indices")
    if any(block < 0 or block >= block_count for block in selected):
        raise ValueError(f"target_blocks index outside available L4 blocks (0..{block_count - 1})")
    if mode not in ("partitioned", "replicated", "selective_multicast"):
        raise ValueError(f"Unsupported L4 distribution mode: {mode}")
    if mode == "selective_multicast" and target_blocks is None:
        raise ValueError("selective_multicast requires explicit target_blocks")

    homes = {block: caches[block * 8].l4 for block in selected}
    if any(home is None for home in homes.values()):
        raise ValueError("Cannot distribute to L4: selected block has no L4 cache")
    counts = {block: 0 for block in selected}
    for index, address in enumerate(addresses):
        destinations = ([selected[index % len(selected)]] if mode == "partitioned"
                        else selected)
        line = address // caches[0].line
        for block in destinations:
            homes[block].insert(line)
            counts[block] += 1
    return counts



def timed_memory_to_l4(caches: List[CacheHierarchy], addresses: List[int],
                       chunk_bytes: int = 256,
                       data_ram_bytes_per_cycle: int = 64,
                       l4_ingress_bytes_per_cycle: int = 64,
                       source_first_beat_latency: int = 0,
                       l4_ingress_latency: int = 0) -> dict:
    """Timed bulk transfer from Data RAM directly into one eight-core L4 home.

    addresses are contiguous byte addresses, one per cache line. This models
    a single eight-core block only. Source bandwidth/bank service and L4 ingress
    are separate resources; chunks may overlap in the pipeline. No L4-to-L4
    forwarding or normal demand-fill path is involved.
    """
    if len(caches) != 8:
        raise ValueError("timed Data RAM-to-L4 transfer requires exactly 8 core caches")
    if any(cache.l4 is None for cache in caches):
        raise ValueError("timed Data RAM-to-L4 transfer requires an L4 cache on every core")
    l4 = caches[0].l4
    if any(cache.l4 is not l4 for cache in caches):
        raise ValueError("all 8 cores must share the same L4 home")
    if not addresses:
        raise ValueError("timed Data RAM-to-L4 transfer requires at least one address")
    if chunk_bytes <= 0 or data_ram_bytes_per_cycle <= 0 or l4_ingress_bytes_per_cycle <= 0:
        raise ValueError("chunk size and both bandwidth values must be positive")
    if source_first_beat_latency < 0 or l4_ingress_latency < 0:
        raise ValueError("transfer latencies cannot be negative")

    line_bytes = caches[0].line
    if any(int(address) % line_bytes for address in addresses):
        raise ValueError(f"all transfer addresses must be {line_bytes}-byte aligned")
    ordered_addresses = [int(address) for address in addresses]
    if any(b - a != line_bytes for a, b in zip(ordered_addresses, ordered_addresses[1:])):
        raise ValueError("bulk transfer addresses must describe one contiguous cache-line range")
    if chunk_bytes < line_bytes or chunk_bytes % line_bytes:
        raise ValueError(f"chunk_bytes must be a positive multiple of cache-line size ({line_bytes})")

    lines_per_chunk = max(1, chunk_bytes // line_bytes)
    chunks = []
    for start in range(0, len(ordered_addresses), lines_per_chunk):
        chunk_addresses = ordered_addresses[start:start + lines_per_chunk]
        chunks.append({
            "id": f"bulk-l4-{len(chunks)}",
            "core": 0,
            "address": chunk_addresses[0],
            "width": len(chunk_addresses) * line_bytes,
            "addresses": chunk_addresses,
        })

    source = SharedMemoryController(
        bank_count=8, beat_bytes=8,
        aggregate_bytes_per_cycle=data_ram_bytes_per_cycle,
    )
    source_reservations = source.reserve_batch(
        0, [{"id": c["id"], "core": 0, "address": c["address"], "width": c["width"]}
            for c in chunks]
    )

    l4_next_cycle = 0
    ingress_events = []
    completed_lines = []
    for chunk in chunks:
        source_done = source_reservations[chunk["id"]]["service_complete_cycle"] + source_first_beat_latency
        ingress_start = max(source_done, l4_next_cycle)
        ingress_cycles = max(1, math.ceil(chunk["width"] / l4_ingress_bytes_per_cycle))
        ingress_done = ingress_start + ingress_cycles + l4_ingress_latency
        l4_next_cycle = ingress_done
        completed_lines.extend((ingress_done, address) for address in chunk["addresses"])
        ingress_events.append({
            "chunk_id": chunk["id"],
            "bytes": chunk["width"],
            "source_complete_cycle": source_done,
            "ingress_start_cycle": ingress_start,
            "ingress_complete_cycle": ingress_done,
            "ingress_wait_cycles": ingress_start - source_done,
        })

    for _, address in sorted(completed_lines):
        l4.insert(address // line_bytes)

    return {
        "cores": 8,
        "l4_home_count": 1,
        "bytes_transferred": len(ordered_addresses) * line_bytes,
        "cache_lines_transferred": len(ordered_addresses),
        "chunk_bytes": chunk_bytes,
        "chunk_count": len(chunks),
        "data_ram_bytes_per_cycle": data_ram_bytes_per_cycle,
        "l4_ingress_bytes_per_cycle": l4_ingress_bytes_per_cycle,
        "source_first_beat_latency": source_first_beat_latency,
        "l4_ingress_latency": l4_ingress_latency,
        "source_request_events": source.request_events,
        "l4_ingress_events": ingress_events,
        "data_ram_bus_next_cycle": source.bus_next_cycle,
        "cycles": max(event["ingress_complete_cycle"] for event in ingress_events),
        "l4_resident_lines": sum(1 for address in ordered_addresses
                                 if l4.lookup(address // line_bytes)),
        "model_scope": "single 8-core block; direct Data RAM-to-L4; no cross-L4 forwarding",
    }


def timed_l4_to_l1(caches: List[CacheHierarchy], addresses: List[int],
                   target_cores: Optional[List[int]] = None,
                   chunk_bytes: int = 256,
                   l4_read_bytes_per_cycle: int = 64,
                   l1_ingress_bytes_per_cycle: int = 64,
                   l4_read_latency: int = 0,
                   l1_ingress_latency: int = 0) -> dict:
    """Timed direct copies from the shared L4 home into selected private L1s.

    This is explicitly NOT an L4->L3->L2->L1 cascade. L4 reads share one
    configurable source service resource; each destination core has an
    independent configurable L1 ingress resource. Different destinations
    may overlap their L1 ingress with later L4 reads. Bandwidth/latency values
    are model inputs, not frozen hardware decisions.
    """
    if len(caches) != 8:
        raise ValueError("direct L4-to-L1 transfer requires exactly 8 core caches")
    l4 = caches[0].l4
    if l4 is None or any(cache.l4 is not l4 for cache in caches):
        raise ValueError("all 8 cores must share the same L4 home")
    if not addresses:
        raise ValueError("direct L4-to-L1 transfer requires at least one address")
    if target_cores is None:
        targets = list(range(8))
    else:
        targets = list(target_cores)
    if not targets or len(set(targets)) != len(targets):
        raise ValueError("target_cores must contain unique valid core indices")
    if any(core < 0 or core >= 8 for core in targets):
        raise ValueError("target_cores index outside available cores (0..7)")
    if chunk_bytes <= 0 or l4_read_bytes_per_cycle <= 0 or l1_ingress_bytes_per_cycle <= 0:
        raise ValueError("chunk size and both bandwidth values must be positive")
    if l4_read_latency < 0 or l1_ingress_latency < 0:
        raise ValueError("transfer latencies cannot be negative")

    line_bytes = caches[0].line
    ordered_addresses = [int(address) for address in addresses]
    if any(address % line_bytes for address in ordered_addresses):
        raise ValueError(f"all transfer addresses must be {line_bytes}-byte aligned")
    if any(b - a != line_bytes for a, b in zip(ordered_addresses, ordered_addresses[1:])):
        raise ValueError("direct L4-to-L1 addresses must describe one contiguous cache-line range")
    if chunk_bytes < line_bytes or chunk_bytes % line_bytes:
        raise ValueError(f"chunk_bytes must be a positive multiple of cache-line size ({line_bytes})")
    missing = [address for address in ordered_addresses
               if not l4.lookup(address // line_bytes)]
    if missing:
        raise ValueError(f"L4 source miss at address 0x{missing[0]:x}; direct copy requires resident L4 lines")

    lines_per_chunk = chunk_bytes // line_bytes
    chunks = [
        ordered_addresses[start:start + lines_per_chunk]
        for start in range(0, len(ordered_addresses), lines_per_chunk)
    ]
    l4_next_cycle = l4_read_latency
    l1_next_cycle = {core: 0 for core in targets}
    source_events, destination_events = [], []
    for core in targets:
        for chunk_index, chunk in enumerate(chunks):
            width = len(chunk) * line_bytes
            source_start = l4_next_cycle
            source_done = source_start + max(1, math.ceil(width / l4_read_bytes_per_cycle))
            l4_next_cycle = source_done
            ingress_start = max(source_done, l1_next_cycle[core])
            ingress_done = ingress_start + max(1, math.ceil(width / l1_ingress_bytes_per_cycle)) + l1_ingress_latency
            l1_next_cycle[core] = ingress_done
            source_events.append({
                "core": core, "chunk_index": chunk_index, "bytes": width,
                "start_cycle": source_start, "complete_cycle": source_done,
            })
            destination_events.append({
                "core": core, "chunk_index": chunk_index, "bytes": width,
                "start_cycle": ingress_start, "complete_cycle": ingress_done,
                "wait_cycles": ingress_start - source_done,
            })
            for address in chunk:
                caches[core].l1.insert(address // line_bytes)

    return {
        "cores": 8,
        "l4_home_count": 1,
        "target_cores": targets,
        "unique_bytes": len(ordered_addresses) * line_bytes,
        "bytes_copied": len(ordered_addresses) * line_bytes * len(targets),
        "l4_source_bytes_read": len(ordered_addresses) * line_bytes * len(targets),
        "l4_source_read_count": len(chunks) * len(targets),
        "distribution_policy": "serialized per-destination L4 reads; multicast is not modeled",
        "cache_lines_per_core": len(ordered_addresses),
        "chunk_bytes": chunk_bytes,
        "chunk_count_per_core": len(chunks),
        "l4_read_bytes_per_cycle": l4_read_bytes_per_cycle,
        "l1_ingress_bytes_per_cycle": l1_ingress_bytes_per_cycle,
        "l4_read_latency": l4_read_latency,
        "l1_ingress_latency": l1_ingress_latency,
        "l4_source_events": source_events,
        "l1_ingress_events": destination_events,
        "l4_source_next_cycle": l4_next_cycle,
        "l1_resident_lines": {
            core: sum(1 for address in ordered_addresses
                      if caches[core].l1.lookup(address // line_bytes))
            for core in targets
        },
        "cycles": max(event["complete_cycle"] for event in destination_events),
        "transfer_path": "L4 -> private L1 (direct; L2/L3 bypassed)",
        "model_scope": "single 8-core block; one shared L4 source; independent per-core L1 ingress",
    }


def timed_l4_to_l1_multicast(caches: List[CacheHierarchy], addresses: List[int],
                              target_cores: Optional[List[int]] = None,
                              chunk_bytes: int = 256,
                              l4_read_bytes_per_cycle: int = 64,
                              fanout_bytes_per_cycle: int = 256,
                              l1_ingress_bytes_per_cycle: int = 64,
                              l4_read_latency: int = 0,
                              fanout_latency: int = 0,
                              l1_ingress_latency: int = 0) -> dict:
    """Timed one-read/many-destination L4 multicast into selected private L1s.

    The shared fanout bandwidth is aggregate replicated-payload bandwidth:
    a chunk of N bytes sent to K destinations consumes N*K fanout bytes.
    L4 reads are serialized; fanout may overlap the next L4 read; each L1
    ingress is independently scheduled after fanout completion. This is an
    explicit topology scenario, not a free multicast assumption.
    """
    if len(caches) != 8:
        raise ValueError("multicast L4-to-L1 transfer requires exactly 8 core caches")
    l4 = caches[0].l4
    if l4 is None or any(cache.l4 is not l4 for cache in caches):
        raise ValueError("all 8 cores must share the same L4 home")
    if not addresses:
        raise ValueError("multicast L4-to-L1 transfer requires at least one address")
    targets = list(range(8)) if target_cores is None else list(target_cores)
    if not targets or len(set(targets)) != len(targets):
        raise ValueError("target_cores must contain unique valid core indices")
    if any(core < 0 or core >= 8 for core in targets):
        raise ValueError("target_cores index outside available cores (0..7)")
    if min(chunk_bytes, l4_read_bytes_per_cycle, fanout_bytes_per_cycle,
           l1_ingress_bytes_per_cycle) <= 0:
        raise ValueError("chunk size and all bandwidth values must be positive")
    if min(l4_read_latency, fanout_latency, l1_ingress_latency) < 0:
        raise ValueError("transfer latencies cannot be negative")

    line_bytes = caches[0].line
    ordered_addresses = [int(address) for address in addresses]
    if any(address % line_bytes for address in ordered_addresses):
        raise ValueError(f"all transfer addresses must be {line_bytes}-byte aligned")
    if any(b - a != line_bytes for a, b in zip(ordered_addresses, ordered_addresses[1:])):
        raise ValueError("multicast L4-to-L1 addresses must describe one contiguous cache-line range")
    if chunk_bytes < line_bytes or chunk_bytes % line_bytes:
        raise ValueError(f"chunk_bytes must be a positive multiple of cache-line size ({line_bytes})")
    missing = [address for address in ordered_addresses
               if not l4.lookup(address // line_bytes)]
    if missing:
        raise ValueError(f"L4 source miss at address 0x{missing[0]:x}; multicast requires resident L4 lines")

    lines_per_chunk = chunk_bytes // line_bytes
    chunks = [ordered_addresses[start:start + lines_per_chunk]
              for start in range(0, len(ordered_addresses), lines_per_chunk)]
    l4_next_cycle = l4_read_latency
    fanout_next_cycle = fanout_latency
    l1_next_cycle = {core: 0 for core in targets}
    source_events, fanout_events, destination_events = [], [], []
    for chunk_index, chunk in enumerate(chunks):
        width = len(chunk) * line_bytes
        source_start = l4_next_cycle
        source_done = source_start + max(1, math.ceil(width / l4_read_bytes_per_cycle))
        l4_next_cycle = source_done

        replicated_bytes = width * len(targets)
        fanout_start = max(source_done, fanout_next_cycle)
        fanout_done = fanout_start + max(1, math.ceil(replicated_bytes / fanout_bytes_per_cycle))
        fanout_next_cycle = fanout_done
        source_events.append({
            "chunk_index": chunk_index, "bytes": width,
            "start_cycle": source_start, "complete_cycle": source_done,
        })
        fanout_events.append({
            "chunk_index": chunk_index, "source_bytes": width,
            "replicated_bytes": replicated_bytes,
            "start_cycle": fanout_start, "complete_cycle": fanout_done,
            "wait_cycles": fanout_start - source_done,
        })
        for core in targets:
            ingress_start = max(fanout_done, l1_next_cycle[core])
            ingress_done = ingress_start + max(1, math.ceil(width / l1_ingress_bytes_per_cycle)) + l1_ingress_latency
            l1_next_cycle[core] = ingress_done
            destination_events.append({
                "core": core, "chunk_index": chunk_index, "bytes": width,
                "start_cycle": ingress_start, "complete_cycle": ingress_done,
                "wait_cycles": ingress_start - fanout_done,
            })
            for address in chunk:
                caches[core].l1.insert(address // line_bytes)

    unique_bytes = len(ordered_addresses) * line_bytes
    return {
        "cores": 8, "l4_home_count": 1, "target_cores": targets,
        "unique_bytes": unique_bytes,
        "bytes_copied": unique_bytes * len(targets),
        "l4_source_bytes_read": unique_bytes,
        "l4_source_read_count": len(chunks),
        "fanout_bytes": unique_bytes * len(targets),
        "fanout_chunk_count": len(chunks),
        "distribution_policy": "one serialized L4 read per chunk; explicit shared multicast fanout",
        "cache_lines_per_core": len(ordered_addresses), "chunk_bytes": chunk_bytes,
        "chunk_count": len(chunks),
        "l4_read_bytes_per_cycle": l4_read_bytes_per_cycle,
        "fanout_bytes_per_cycle": fanout_bytes_per_cycle,
        "fanout_bandwidth_semantics": "aggregate replicated-payload bytes per cycle",
        "l1_ingress_bytes_per_cycle": l1_ingress_bytes_per_cycle,
        "l4_read_latency": l4_read_latency, "fanout_latency": fanout_latency,
        "l1_ingress_latency": l1_ingress_latency,
        "l4_source_events": source_events, "fanout_events": fanout_events,
        "l1_ingress_events": destination_events,
        "l4_source_next_cycle": l4_next_cycle,
        "fanout_next_cycle": fanout_next_cycle,
        "l1_resident_lines": {
            core: sum(1 for address in ordered_addresses
                      if caches[core].l1.lookup(address // line_bytes))
            for core in targets
        },
        "cycles": max(event["complete_cycle"] for event in destination_events),
        "transfer_path": "L4 -> shared multicast fanout -> selected private L1s (L2/L3 bypassed)",
        "model_scope": "single 8-core block; one shared L4 source; aggregate fanout resource; independent per-core L1 ingress",
    }


def run_l4_l1_transfer_sweep(
    working_set_kib_values: Tuple[int, ...] = (64, 256),
    chunk_bytes_values: Tuple[int, ...] = (64, 256, 1024),
    l4_read_bandwidth_values: Tuple[int, ...] = (64, 128, 256),
    l1_ingress_bandwidth_values: Tuple[int, ...] = (64, 128, 256),
    target_core_counts: Tuple[int, ...] = (1, 2, 4, 8),
) -> dict:
    """Explore direct L4->L1 transfer settings for one 8-core NEXSUS block.

    This is a parameter sweep, not a selected/frozen hardware operating point.
    L4 is preloaded as untimed setup; only the direct L4 read and destination
    L1 ingress path are timed. Data RAM is intentionally outside this sweep.
    """
    profile = profile_from_dict(PROFILES["nexus_balanced_128"])
    rows = []
    for working_set_kib in working_set_kib_values:
        if working_set_kib <= 0:
            raise ValueError("working-set sizes must be positive")
        line_bytes = profile.line_bytes
        total_bytes = working_set_kib * 1024
        if total_bytes % line_bytes:
            raise ValueError("working-set size must be a multiple of cache-line size")
        if working_set_kib * 1024 > profile.l4_kb * 1024:
            raise ValueError("working set exceeds the configured L4 capacity")
        addresses = [
            0x10000000 + offset
            for offset in range(0, total_bytes, line_bytes)
        ]
        for chunk_bytes in chunk_bytes_values:
            for l4_bw in l4_read_bandwidth_values:
                for l1_bw in l1_ingress_bandwidth_values:
                    for target_count in target_core_counts:
                        if target_count < 1 or target_count > 8:
                            raise ValueError("target core counts must be in the range 1..8")
                        caches = build_cache_hierarchies(profile, 8)
                        shared_l4 = caches[0].l4
                        for address in addresses:
                            shared_l4.insert(address // line_bytes)
                        result = timed_l4_to_l1(
                            caches, addresses,
                            target_cores=list(range(target_count)),
                            chunk_bytes=chunk_bytes,
                            l4_read_bytes_per_cycle=l4_bw,
                            l1_ingress_bytes_per_cycle=l1_bw,
                        )
                        elapsed = max(1, result["cycles"])
                        rows.append({
                            "working_set_kib": working_set_kib,
                            "target_core_count": target_count,
                            "chunk_bytes": chunk_bytes,
                            "l4_read_bytes_per_cycle": l4_bw,
                            "l1_ingress_bytes_per_cycle": l1_bw,
                            "unique_bytes": result["unique_bytes"],
                            "bytes_copied": result["bytes_copied"],
                            "l4_source_bytes_read": result["l4_source_bytes_read"],
                            "l4_source_read_count": result["l4_source_read_count"],
                            "chunk_count_per_core": result["chunk_count_per_core"],
                            "cycles": result["cycles"],
                            "effective_bytes_per_cycle": result["bytes_copied"] / elapsed,
                            "l4_source_service_cycles": result["l4_source_next_cycle"],
                            "l1_ingress_wait_cycles": sum(
                                event["wait_cycles"]
                                for event in result["l1_ingress_events"]
                            ),
                        })
    return {
        "experiment": "8-core direct shared L4-to-private-L1 transfer design-space sweep",
        "cores_per_block": 8,
        "transfer_path": "L4 -> selected private L1s; L2/L3 bypassed",
        "distribution_policy": "serialized per-destination L4 reads; multicast is not modeled",
        "data_ram_baseline_bytes_per_cycle": 64,
        "timing_scope": "L4 source read and per-core L1 ingress only; L4 prefill is untimed setup",
        "hardware_decisions_frozen_by_sweep": [],
        "open_parameters": [
            "chunk_bytes", "L4 read bandwidth", "per-core L1 ingress bandwidth",
            "source and ingress queueing", "arbitration", "transfer latency",
        ],
        "row_count": len(rows),
        "results": rows,
    }


def run_l4_l1_distribution_comparison_sweep(
    working_set_kib_values: Tuple[int, ...] = (64, 256),
    chunk_bytes_values: Tuple[int, ...] = (64, 256, 1024),
    l4_read_bandwidth_values: Tuple[int, ...] = (64, 128, 256),
    fanout_bandwidth_values: Tuple[int, ...] = (64, 256, 1024),
    l1_ingress_bandwidth_values: Tuple[int, ...] = (64, 128, 256),
    target_core_counts: Tuple[int, ...] = (1, 2, 4, 8),
) -> dict:
    """Compare conservative unicast against explicit multicast fanout settings.

    Every multicast row is paired with a unicast row using identical working
    set, chunk, L4 read and per-core L1 ingress settings. Fanout bandwidth is
    aggregate replicated-payload capacity. This is design-space exploration,
    not a selected hardware operating point.
    """
    profile = profile_from_dict(PROFILES["nexus_balanced_128"])
    rows = []
    unicast_cache = {}
    line_bytes = profile.line_bytes
    for working_set_kib in working_set_kib_values:
        if working_set_kib <= 0:
            raise ValueError("working-set sizes must be positive")
        total_bytes = working_set_kib * 1024
        if total_bytes % line_bytes:
            raise ValueError("working-set size must be a multiple of cache-line size")
        if total_bytes > profile.l4_kb * 1024:
            raise ValueError("working set exceeds the configured L4 capacity")
        addresses = [0x18000000 + offset for offset in range(0, total_bytes, line_bytes)]
        for chunk_bytes in chunk_bytes_values:
            if chunk_bytes < line_bytes or chunk_bytes % line_bytes:
                raise ValueError(f"chunk_bytes must be a positive multiple of cache-line size ({line_bytes})")
            for l4_bw in l4_read_bandwidth_values:
                if l4_bw <= 0:
                    raise ValueError("L4 read bandwidth values must be positive")
                for l1_bw in l1_ingress_bandwidth_values:
                    if l1_bw <= 0:
                        raise ValueError("L1 ingress bandwidth values must be positive")
                    for target_count in target_core_counts:
                        if target_count < 1 or target_count > 8:
                            raise ValueError("target core counts must be in the range 1..8")
                        key = (working_set_kib, chunk_bytes, l4_bw, l1_bw, target_count)
                        if key not in unicast_cache:
                            caches = build_cache_hierarchies(profile, 8)
                            for address in addresses:
                                caches[0].l4.insert(address // line_bytes)
                            unicast = timed_l4_to_l1(
                                caches, addresses, target_cores=list(range(target_count)),
                                chunk_bytes=chunk_bytes,
                                l4_read_bytes_per_cycle=l4_bw,
                                l1_ingress_bytes_per_cycle=l1_bw,
                            )
                            unicast_cache[key] = {
                                "cycles": unicast["cycles"],
                                "l4_source_bytes_read": unicast["l4_source_bytes_read"],
                                "l4_source_read_count": unicast["l4_source_read_count"],
                                "bytes_copied": unicast["bytes_copied"],
                                "effective_bytes_per_cycle": unicast["bytes_copied"] / max(1, unicast["cycles"]),
                            }
                        baseline = unicast_cache[key]
                        for fanout_bw in fanout_bandwidth_values:
                            if fanout_bw <= 0:
                                raise ValueError("fanout bandwidth values must be positive")
                            caches = build_cache_hierarchies(profile, 8)
                            for address in addresses:
                                caches[0].l4.insert(address // line_bytes)
                            multicast = timed_l4_to_l1_multicast(
                                caches, addresses, target_cores=list(range(target_count)),
                                chunk_bytes=chunk_bytes,
                                l4_read_bytes_per_cycle=l4_bw,
                                fanout_bytes_per_cycle=fanout_bw,
                                l1_ingress_bytes_per_cycle=l1_bw,
                            )
                            cycles = multicast["cycles"]
                            rows.append({
                                "working_set_kib": working_set_kib,
                                "target_core_count": target_count,
                                "chunk_bytes": chunk_bytes,
                                "l4_read_bytes_per_cycle": l4_bw,
                                "fanout_bytes_per_cycle": fanout_bw,
                                "l1_ingress_bytes_per_cycle": l1_bw,
                                "unique_bytes": multicast["unique_bytes"],
                                "bytes_copied": multicast["bytes_copied"],
                                "unicast_l4_source_bytes_read": baseline["l4_source_bytes_read"],
                                "multicast_l4_source_bytes_read": multicast["l4_source_bytes_read"],
                                "l4_source_bytes_saved": baseline["l4_source_bytes_read"] - multicast["l4_source_bytes_read"],
                                "unicast_l4_source_read_count": baseline["l4_source_read_count"],
                                "multicast_l4_source_read_count": multicast["l4_source_read_count"],
                                "fanout_bytes": multicast["fanout_bytes"],
                                "unicast_cycles": baseline["cycles"],
                                "multicast_cycles": cycles,
                                "cycle_delta_multicast_minus_unicast": cycles - baseline["cycles"],
                                "multicast_speedup_vs_unicast": baseline["cycles"] / max(1, cycles),
                                "unicast_effective_bytes_per_cycle": baseline["effective_bytes_per_cycle"],
                                "multicast_effective_bytes_per_cycle": multicast["bytes_copied"] / max(1, cycles),
                                "fanout_service_cycles": multicast["fanout_next_cycle"],
                                "l4_source_service_cycles": multicast["l4_source_next_cycle"],
                                "fanout_wait_cycles": sum(event["wait_cycles"] for event in multicast["fanout_events"]),
                                "l1_ingress_wait_cycles": sum(event["wait_cycles"] for event in multicast["l1_ingress_events"]),
                            })
    return {
        "experiment": "8-core L4-to-L1 unicast versus multicast distribution comparison",
        "cores_per_block": 8,
        "working_set_home": "shared L4; prefill is untimed setup",
        "unicast_policy": "serialized per-destination L4 reads",
        "multicast_policy": "one serialized L4 read per chunk plus shared aggregate fanout",
        "fanout_bandwidth_semantics": "aggregate replicated-payload bytes per cycle; N bytes to K targets consumes N*K bytes",
        "timing_scope": "L4 source, multicast fanout where applicable, and per-core L1 ingress",
        "data_ram_baseline_bytes_per_cycle": 64,
        "hardware_decisions_frozen_by_sweep": [],
        "open_parameters": [
            "L4 read bandwidth", "fanout aggregate bandwidth", "per-core L1 ingress bandwidth",
            "chunk size", "fanout topology and physical replication cost",
            "source/fanout/ingress queueing", "arbitration", "transfer latency",
        ],
        "unicast_baseline_row_count": len(unicast_cache),
        "multicast_row_count": len(rows),
        "row_count": len(rows),
        "results": rows,
    }


def build_cache_hierarchies(p: CoreProfile, core_count: int) -> List[CacheHierarchy]:
    """Build private and shared cache objects using each modeled architecture's topology.

    Controlled 8-core topology assumptions:
    - AMD Zen 5: private L1/L2; one shared 32 MiB L3.
    - Intel Lion Cove P: private L1/L2; one shared 36 MiB L3.
    - Intel Skymont E: private L1; 4 MiB L2 shared per 4-core cluster; shared L3.
    - NEXSUS: private L1; L2/2-core, L3/4-core and L4/8-core groups.
    """
    line = p.line_bytes
    if p.name.startswith("NEXSUS CPU"):
        l2_groups = [LRU(p.l2_kb * 1024, line) for _ in range(math.ceil(core_count / 2))]
        l3_groups = [LRU(p.l3_kb * 1024, line) for _ in range(math.ceil(core_count / 4))]
        l4_groups = [LRU(p.l4_kb * 1024, line) for _ in range(math.ceil(core_count / 8))] if p.l4_kb else []
        return [
            CacheHierarchy(p, l2_groups[i // 2], l3_groups[i // 4],
                           l4_groups[i // 8] if l4_groups else None)
            for i in range(core_count)
        ]

    # Reference CPUs have a socket/package-level shared LLC in this model.
    shared_l3 = LRU(p.l3_kb * 1024, line) if p.l3_kb else None
    if p.core_type == "E":
        # Skymont E-core cluster: four cores share the modeled L2.
        l2_groups = [LRU(p.l2_kb * 1024, line) for _ in range(math.ceil(core_count / 4))]
        return [CacheHierarchy(p, l2_groups[i // 4], shared_l3) for i in range(core_count)]
    return [CacheHierarchy(p, None, shared_l3) for _ in range(core_count)]


def build_command_page_descriptors(ops: List[Op], page_bytes: int = 2048) -> dict:
    """Describe only code pages actually touched by a core's command stream."""
    page_lengths = {}
    for op in ops:
        pc = op.command_address if op.command_address >= 0 else op.seq * 8
        page_id, offset = divmod(max(0, int(pc)), page_bytes)
        page_lengths[page_id] = max(page_lengths.get(page_id, 0), offset + 8)
    page_ids = sorted(page_lengths)
    descriptors = {}
    for index, page_id in enumerate(page_ids):
        valid_bytes = min(page_bytes, math.ceil(page_lengths[page_id] / 8) * 8)
        next_is_sequential = (index + 1 < len(page_ids) and
                              page_ids[index + 1] == page_id + 1)
        descriptor = {"logical_page_id": page_id, "valid_bytes": valid_bytes}
        if valid_bytes == page_bytes:
            if not next_is_sequential:
                descriptor["stream_end"] = True
        elif next_is_sequential:
            descriptor["marker"] = "CF_NEXT"
            descriptor["next_logical_page_id"] = page_id + 1
        else:
            descriptor["marker"] = "CF_END"
        descriptors[page_id] = descriptor
    return descriptors


def validate_px_page_descriptors(pages: List[dict]) -> bool:
    """Validate CodeFlow Manager metadata; markers are never executable operations."""
    if not pages:
        raise ValueError("CodeFlow stream must contain at least one page")
    seen = set()
    for index, page in enumerate(pages):
        page_id = int(page["logical_page_id"])
        valid_bytes = int(page["valid_bytes"])
        marker = page.get("marker")
        if page_id in seen:
            raise ValueError(f"duplicate logical page id: {page_id}")
        seen.add(page_id)
        if valid_bytes <= 0 or valid_bytes > 2048 or valid_bytes % 8:
            raise ValueError(f"invalid or misaligned valid_bytes for page {page_id}")
        is_last = index == len(pages) - 1
        if valid_bytes == 2048:
            if marker not in (None, "FULL"):
                raise ValueError("full 2-KiB pages continue automatically and take no marker")
            if page.get("stream_end", False) and not is_last:
                raise ValueError("stream_end can only appear on the final code page")
            if is_last and not page.get("stream_end", False):
                raise ValueError("a full final page requires stream_end metadata, not CF_END")
            if not is_last and int(pages[index + 1]["logical_page_id"]) != page_id + 1:
                raise ValueError("full-page sequential continuation must name the next logical page")
        elif marker == "CF_NEXT":
            if is_last:
                raise ValueError("CF_NEXT requires a following logical page")
            next_id = int(page.get("next_logical_page_id", -1))
            if next_id != int(pages[index + 1]["logical_page_id"]):
                raise ValueError("CF_NEXT target does not match the next logical page")
        elif marker == "CF_END":
            if not is_last:
                raise ValueError("CF_END cannot precede another page in the same code stream")
        else:
            raise ValueError("partial page requires CF_NEXT or CF_END metadata")
    return True


class CommandFetchModel:
    """Conventional I-cache or CS0-CS7 pool feeding two 2-KiB EB banks."""
    def __init__(self, enabled: bool, p0_capacity_bytes: int = 16384,
                 conventional_capacity_bytes: int = 32768,
                 p0_refill_latency: int = 48, conventional_refill_latency: int = 8,
                 p0_buffer_bytes: int = 2048, page_descriptors: dict | None = None,
                 pool_miss_latency: int = 120, code_cache_bytes: int = 65536, app_first_beat_latency: int = 40, app_beat_interval: int = 1, c0_to_cs_bytes_per_cycle: int = 20, cs_to_eb_bytes_per_cycle: int = 20, codeflow_enabled: bool = False,
                 app_ram_controller=None, core_id: int = 0,
                 known_page_ids=None):
        self.enabled = enabled
        self.capacity_bytes = p0_capacity_bytes if enabled else conventional_capacity_bytes
        self.lines = LRU(self.capacity_bytes, 64)
        self.refill_latency = p0_refill_latency if enabled else conventional_refill_latency
        self.p0_buffer_bytes = p0_buffer_bytes
        # When supplied by the workload builder, this prevents speculative
        # refills beyond the actual command stream while preserving early
        # ping-pong prefetch for pages that really exist.
        self.known_page_ids = (None if known_page_ids is None
                               else {int(page_id) for page_id in known_page_ids})
        self.page_descriptors = {int(k): v for k, v in (page_descriptors or {}).items()}
        self.codeflow_enabled = codeflow_enabled
        self.app_ram_controller = app_ram_controller
        self.core_id = int(core_id)
        self.pool_miss_latency = pool_miss_latency  # legacy fallback
        self.code_cache_capacity_pages = max(1, code_cache_bytes // p0_buffer_bytes)
        self.code_cache_pages = OrderedDict()
        self.app_first_beat_latency = app_first_beat_latency
        self.app_beat_interval = max(1, app_beat_interval)
        self.c0_to_cs_bytes_per_cycle = max(1, int(c0_to_cs_bytes_per_cycle))
        self.cs_to_eb_bytes_per_cycle = max(1, int(cs_to_eb_bytes_per_cycle))
        self.c0_to_cs_cycles = math.ceil(p0_buffer_bytes / self.c0_to_cs_bytes_per_cycle)
        self.cs_to_eb_cycles = math.ceil(p0_buffer_bytes / self.cs_to_eb_bytes_per_cycle)
        self.c0_hits = self.c0_misses = self.app_beats = self.app_bytes = 0
        self.app_source_cycles = self.code_slot_cycles = self.code_stream_cycles = 0
        self.pool_initialized = False
        self.pool_refill_bytes = 0
        self.p0_buffers = [None, None]  # EB-A/B, 2 KiB each
        self.p0_pending = None
        self.pending = {}
        self.max_i_mshrs = 32
        self.i_prefetch_lines = 16
        self.active_block = None
        self.hits = self.refills = self.refill_bytes = self.wait_cycles = 0
        self.prefetches = self.buffer_hits = self.prefetch_wait_cycles = 0
        self.bank_switches = self.ready_boundaries = self.boundary_waits = 0
        self.useful_bytes = self.wasted_bytes = 0
        self.pool_pages = OrderedDict()
        self.pool_hits = self.pool_misses = 0

    def complete(self, cycle: int):
        if self.enabled:
            if self.p0_pending is not None and self.p0_pending[1] <= cycle:
                block, _, bank = self.p0_pending
                self.p0_buffers[bank] = block
                self.p0_pending = None
            return
        ready_lines = [line for line, ready in self.pending.items() if ready <= cycle]
        for line in ready_lines:
            self.lines.insert(line)
            del self.pending[line]

    def _next_logical_page(self, block: int):
        descriptor = self.page_descriptors.get(block)
        if descriptor is None:
            next_block = block + 1
            if self.known_page_ids is not None and next_block not in self.known_page_ids:
                return None
            return next_block
        valid_bytes = int(descriptor.get("valid_bytes", self.p0_buffer_bytes))
        marker = descriptor.get("marker")
        if descriptor.get("stream_end", False):
            return None
        if valid_bytes == self.p0_buffer_bytes:
            next_block = block + 1
            if self.known_page_ids is not None and next_block not in self.known_page_ids:
                return None
            return next_block
        if marker == "CF_END":
            return None
        if marker == "CF_NEXT":
            return int(descriptor.get("next_logical_page_id", block + 1))
        raise ValueError(f"partial code page {block} has no valid CF_NEXT/CF_END marker")

    def _validate_fetch_address(self, block: int, offset: int):
        # PX valid-byte boundaries are executable metadata for the integrated
        # CodeFlow path. Legacy P0-only mode models a padded execution buffer
        # and must not reject fetches into the rest of that physical page.
        if not self.codeflow_enabled:
            return
        descriptor = self.page_descriptors.get(block)
        if descriptor is None:
            return
        valid_bytes = int(descriptor.get("valid_bytes", self.p0_buffer_bytes))
        if offset < 0 or offset >= valid_bytes:
            raise ValueError(f"fetch into invalid/padding bytes of code page {block}")
        if valid_bytes <= 0 or valid_bytes > self.p0_buffer_bytes or valid_bytes % 8:
            raise ValueError(f"invalid valid_bytes/alignment for code page {block}")

    def _pool_probe(self, block: int) -> bool:
        """Check pool residency without recording a miss before source admission."""
        max_pages = max(1, self.capacity_bytes // self.p0_buffer_bytes)
        if not self.pool_initialized:
            # Legacy mode assumes OS launch-time staging. Integrated CodeFlow
            # mode starts cold: the first demanded page must traverse App RAM,
            # C0, Code Slot and EB like every later nonresident page.
            if not self.codeflow_enabled:
                for page in range(block, block + max_pages):
                    self.pool_pages[page] = None
            self.pool_initialized = True
        if block in self.pool_pages:
            self.pool_hits += 1
            self.pool_pages.move_to_end(block)
            return True
        return False

    def _pool_record_miss(self, block: int, transfer_bytes: int | None = None):
        max_pages = max(1, self.capacity_bytes // self.p0_buffer_bytes)
        self.pool_misses += 1
        self.pool_refill_bytes += (self.p0_buffer_bytes if transfer_bytes is None
                                   else max(1, int(transfer_bytes)))
        self.pool_pages[block] = None
        if len(self.pool_pages) > max_pages:
            self.pool_pages.popitem(last=False)

    def _pool_touch(self, block: int) -> bool:
        """Compatibility helper for callers that do not have admission control."""
        if self._pool_probe(block):
            return True
        self._pool_record_miss(block)
        return False

    def _start_p0_prefetch(self, block: int, cycle: int, allow_active_bank: bool = False):
        if block in self.p0_buffers or (self.p0_pending and self.p0_pending[0] == block):
            return
        if self.p0_pending is not None:
            return
        bank = block & 1
        if self.active_block is not None and bank == (self.active_block & 1):
            if not allow_active_bank:
                return  # do not overwrite a bank still consumed by sequential fetch
            self.active_block = None  # branch redirect abandons the old sequential stream
        descriptor = self.page_descriptors.get(block)
        valid_bytes = int(descriptor.get("valid_bytes", self.p0_buffer_bytes)
                          if descriptor is not None else self.p0_buffer_bytes)
        if valid_bytes <= 0 or valid_bytes > self.p0_buffer_bytes or valid_bytes % 8:
            raise ValueError(f"invalid transfer length for code page {block}: {valid_bytes}")
        beats = math.ceil(valid_bytes / 8)
        code_slot_delay = stream_delay = 0
        pool_hit = self._pool_probe(block)
        source_delay = 0
        if not pool_hit and not self.codeflow_enabled:
            self._pool_record_miss(block, valid_bytes)
            source_delay = self.pool_miss_latency
        elif not pool_hit:
            code_slot_delay = math.ceil(valid_bytes / self.c0_to_cs_bytes_per_cycle)
            stream_delay = math.ceil(valid_bytes / self.cs_to_eb_bytes_per_cycle)
            if block in self.code_cache_pages:
                self._pool_record_miss(block, valid_bytes)
                self.c0_hits += 1
                self.code_cache_pages.move_to_end(block)
            else:
                if self.app_ram_controller is not None:
                    request_id = f"core{self.core_id}:page{block}"
                    admission = self.app_ram_controller.reserve_batch(cycle, [{
                        "id": request_id, "core": self.core_id,
                        "address": block * self.p0_buffer_bytes,
                        "bytes": valid_bytes,
                    }])[request_id]
                    if not admission["accepted"]:
                        # Rejected requests must remain nonresident and retry.
                        return
                    source_delay = max(0, admission["ready_cycle"] - cycle)
                else:
                    source_delay = self.app_first_beat_latency + max(0, beats - 1) * self.app_beat_interval + 1
                self._pool_record_miss(block, valid_bytes)
                self.c0_misses += 1
                self.app_beats += beats
                self.app_bytes += valid_bytes
                self.app_source_cycles += source_delay
                self.code_cache_pages[block] = None
                if len(self.code_cache_pages) > self.code_cache_capacity_pages:
                    self.code_cache_pages.popitem(last=False)
            self.code_slot_cycles += code_slot_delay
            self.code_stream_cycles += stream_delay
        ready_cycle = cycle + self.refill_latency + source_delay + code_slot_delay + stream_delay
        self.p0_pending = (block, ready_cycle, bank)
        self.prefetches += 1
        self.refills += 1
        self.refill_bytes += valid_bytes
        self.useful_bytes += valid_bytes

    def _start_i_prefetch(self, first_line: int, cycle: int):
        """Issue a bounded stream of conventional I-cache line fills."""
        for offset in range(self.i_prefetch_lines):
            line = first_line + offset
            if self.lines.lookup(line) or line in self.pending:
                continue
            if len(self.pending) >= self.max_i_mshrs:
                break
            self.pending[line] = cycle + self.refill_latency
            self.refills += 1
            self.refill_bytes += 64
            self.useful_bytes += 64

    def can_fetch(self, command_address: int, cycle: int, sequential: bool = True) -> bool:
        self.complete(cycle)
        if self.enabled:
            block = max(0, command_address) // self.p0_buffer_bytes
            offset = max(0, command_address) % self.p0_buffer_bytes
            self._validate_fetch_address(block, offset)
            if sequential and self.active_block is not None and block != self.active_block:
                expected = self._next_logical_page(self.active_block)
                if expected is None:
                    raise ValueError(f"CF_END reached for page {self.active_block}; no sequential next page")
                if block != expected:
                    raise ValueError(f"PX sequential transition expected logical page {expected}, got {block}")
            if block in self.p0_buffers:
                if self.active_block != block:
                    if self.active_block is not None:
                        self.bank_switches += 1
                    self.active_block = block
                    self.ready_boundaries += 1
                self.hits += 1
                self.buffer_hits += 1
                next_block = self._next_logical_page(block)
                if next_block is not None:
                    self._start_p0_prefetch(next_block, cycle)
                return True
            self.wait_cycles += 1
            self.boundary_waits += 1
            if self.p0_pending is not None:
                self.prefetch_wait_cycles += 1
            else:
                self._start_p0_prefetch(block, cycle, allow_active_bank=not sequential)
            return False
        line = command_address // 64
        if self.lines.lookup(line):
            self.hits += 1
            self._start_i_prefetch(line + 1, cycle)
            return True
        if line not in self.pending:
            self._start_i_prefetch(line, cycle)
        self.wait_cycles += 1
        return False


class AppRamController:
    """Fabric-managed App RAM ports: one independent 64-B/cycle path per core.

    Each core has its own bank scheduling, byte-bandwidth timeline and
    outstanding-request capacity. Requests from different cores therefore
    progress concurrently; there is no fictitious chip-wide 64-B/cycle bus.
    The System Fabric coordinates the independent core ports.
    """
    def __init__(self, bank_count: int = 8, beat_bytes: int = 8,
                 bytes_per_cycle: int = 64, first_beat_latency: int = 40,
                 beat_interval: int = 1, max_outstanding: int = 16):
        self.bank_count = max(1, int(bank_count))
        self.beat_bytes = max(1, int(beat_bytes))
        self.bytes_per_cycle = max(1, int(bytes_per_cycle))
        self.first_beat_latency = max(0, int(first_beat_latency))
        self.beat_interval = max(1, int(beat_interval))
        self.max_outstanding = max(1, int(max_outstanding))
        self.bank_busy = {}
        self.bus_next_byte = {}
        self.inflight = {}
        self.rr_cursor = 0
        self.accepted = 0
        self.rejected_queue_full = 0
        self.bank_conflicts = 0
        self.transferred_bytes = 0
        self.request_cycles = []
        self.request_events = []
        self.bytes_by_core = {}

    def _bank(self, address: int) -> int:
        return (int(address) // self.beat_bytes) % self.bank_count

    def _core_banks(self, core: int) -> list[int]:
        return self.bank_busy.setdefault(int(core), [0] * self.bank_count)

    def complete(self, cycle: int):
        for key in [k for k, item in self.inflight.items() if item["ready"] <= cycle]:
            del self.inflight[key]

    def reserve_batch(self, cycle: int, requests: List[dict]) -> dict:
        """Admit same-cycle requests independently on each core's App RAM port."""
        self.complete(cycle)
        if not requests:
            return {}
        cores = sorted({int(r["core"]) for r in requests})
        start = self.rr_cursor % len(cores)
        rotated = cores[start:] + cores[:start]
        rank = {core: i for i, core in enumerate(rotated)}
        ordered = sorted(
            requests,
            key=lambda r: (-int(r.get("priority", 0)),
                           rank[int(r["core"])], str(r["id"])),
        )
        result = {}
        for req in ordered:
            req_id = req["id"]
            core = int(req["core"])
            if req_id in self.inflight:
                raise ValueError(f"duplicate in-flight App RAM request id: {req_id}")
            core_inflight = sum(1 for item in self.inflight.values() if item["core"] == core)
            if core_inflight >= self.max_outstanding:
                self.rejected_queue_full += 1
                result[req_id] = {"accepted": False, "reason": "core_queue_full"}
                continue
            address = int(req["address"])
            size = max(1, int(req["bytes"]))
            beats = math.ceil(size / self.beat_bytes)
            touched = set()
            bank_busy = self._core_banks(core)
            bank_complete = cycle
            for beat in range(beats):
                bank = self._bank(address + beat * self.beat_bytes)
                touched.add(bank)
                bank_start = max(cycle, bank_busy[bank])
                if bank_start > cycle:
                    self.bank_conflicts += 1
                bank_busy[bank] = bank_start + self.beat_interval
                bank_complete = max(bank_complete, bank_busy[bank])
            bus_start_byte = max(cycle * self.bytes_per_cycle,
                                 self.bus_next_byte.get(core, 0))
            bus_complete = math.ceil((bus_start_byte + size) / self.bytes_per_cycle)
            self.bus_next_byte[core] = bus_start_byte + size
            ready = max(
                cycle + self.first_beat_latency + max(0, bank_complete - cycle),
                bus_complete,
            )
            self.inflight[req_id] = {"ready": ready, "core": core}
            self.accepted += 1
            self.transferred_bytes += size
            self.bytes_by_core[core] = self.bytes_by_core.get(core, 0) + size
            self.request_cycles.append(cycle)
            result[req_id] = {
                "accepted": True, "bank_count_touched": len(touched),
                "ready_cycle": ready, "queue_occupancy": core_inflight + 1,
                "core": core, "core_bytes_per_cycle": self.bytes_per_cycle,
            }
            self.request_events.append({
                "request_id": str(req_id), "core": core, "address": address,
                "bytes": size, "request_cycle": cycle,
                "bank_count_touched": len(touched), "ready_cycle": ready,
                "queue_occupancy": core_inflight + 1,
            })
        self.rr_cursor = (start + 1) % len(cores)
        return result


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
        self.request_cycles = []
        self.request_events = []

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
            self.request_cycles.append(cycle)
            address = int(req["address"])
            width = max(1, int(req["width"]))
            first_beat_address = (address // self.beat_bytes) * self.beat_bytes
            beat_offset = address - first_beat_address
            beats = max(1, math.ceil((beat_offset + width) / self.beat_bytes))
            bank_wait = 0
            touched_banks = set()
            for beat in range(beats):
                bank = self._bank(first_beat_address + beat * self.beat_bytes, bank_hash)
                touched_banks.add(bank)
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
            # A request waits only for banks touched by its own beats.
            # Unrelated busy banks must not destroy cross-bank parallelism.
            bank_complete = max((self.bank_busy[bank] for bank in touched_banks),
                                default=cycle)
            bus_complete = math.ceil(
                (bus_start_byte + width) / self.aggregate_bytes_per_cycle
            )
            service_complete_cycle = max(bank_complete, bus_complete)
            result[req_id] = {
                "bank_wait": bank_wait,
                "bus_wait": bus_wait,
                "bus_service_cycles": bus_service_cycles,
                "service_complete_cycle": service_complete_cycle,
            }
            self.request_events.append({
                "request_id": str(req_id),
                "core": int(req["core"]),
                "address": address,
                "width": width,
                "request_cycle": cycle,
                "bank_wait": bank_wait,
                "bus_wait": bus_wait,
                "service_complete_cycle": service_complete_cycle,
            })
        self.rr_cursor = (start + 1) % len(core_ids)
        return result



class DataRamController:
    """System-Fabric-facing Data RAM ports: 64 B/cycle per active core.

    This models the independently provisioned core-facing links only. The
    shared physical bank-group count, placement and multi-client arbitration
    are intentionally not inferred here; those belong to NEX-T004 and later.
    App RAM uses a separate AppRamController instance and timeline.
    """
    def __init__(self, bytes_per_cycle_per_core: int = 64):
        self.bytes_per_cycle_per_core = max(1, int(bytes_per_cycle_per_core))
        self.bus_next_byte = {}
        self.request_cycles = []
        self.request_events = []
        self.transferred_bytes = 0
        self.bytes_by_core = {}
        self.accepted = 0

    @property
    def bus_next_cycle(self) -> int:
        """Latest per-core link drain cycle; not a shared chip-wide bus."""
        return max(
            (math.ceil(byte_cursor / self.bytes_per_cycle_per_core)
             for byte_cursor in self.bus_next_byte.values()),
            default=0,
        )

    def reserve_batch(self, cycle: int, requests: List[dict],
                      bank_hash: str = "low") -> dict:
        if not requests:
            return {}
        result = {}
        # Each core owns an independent Fabric-facing bandwidth timeline.
        # Requests from other cores cannot consume this core's link capacity.
        for req in sorted(requests, key=lambda x: (int(x["core"]), str(x["id"]))):
            core = int(req["core"])
            req_id = req["id"]
            size = max(1, int(req["width"]))
            rate = self.bytes_per_cycle_per_core
            start_byte = max(cycle * rate, self.bus_next_byte.get(core, 0))
            wait = max(0, math.ceil(start_byte / rate) - cycle)
            service_cycles = max(1, math.ceil((start_byte % rate + size) / rate))
            complete = math.ceil((start_byte + size) / rate)
            self.bus_next_byte[core] = start_byte + size
            self.accepted += 1
            self.transferred_bytes += size
            self.bytes_by_core[core] = self.bytes_by_core.get(core, 0) + size
            self.request_cycles.append(cycle)
            result[req_id] = {
                "bank_wait": 0, "bus_wait": wait,
                "bus_service_cycles": service_cycles,
                "service_complete_cycle": complete,
                "core": core, "core_bytes_per_cycle": rate,
            }
            self.request_events.append({
                "request_id": str(req_id), "core": core,
                "address": int(req["address"]), "width": size,
                "request_cycle": cycle, "bank_wait": 0, "bus_wait": wait,
                "service_complete_cycle": complete,
            })
        return result


def branch_mispredict(op: Op, branch_number: int, predictor: str) -> bool:
    """Deterministic branch-prediction sensitivity model; rates are assumptions."""
    label = op.label.lower()
    if predictor == "none":
        rate = 0.50
    elif "branch stress" in label or "p0 branch" in label:
        rate = 0.50
    elif "graph decision" in label:
        rate = 0.20 if predictor == "small_2bit" else 0.15
    elif "control branch" in label:
        rate = 0.08 if predictor == "small_2bit" else 0.05
    else:
        rate = 0.04 if predictor == "small_2bit" else 0.02
    mixed = (branch_number * 1103515245 + op.seq * 12345 + 0x9E3779B9) & 0xFFFFFFFF
    return mixed % 10000 < int(rate * 10000)


def simulate_stream(ops: List[Op], p: CoreProfile) -> dict:
    """Single hardware thread, OoO window, in-order retirement, shared unit limits."""
    cache = CacheHierarchy(p)
    ready_at = [0] * len(ops)
    done = [False] * len(ops)
    issued = [False] * len(ops)
    dispatched = [False] * len(ops)
    rob = deque()
    scheduler = deque()
    scheduler_capacity = p.scheduler_entries if p.scheduler_entries > 0 else p.rob
    unit_busy = {k: [0]*v for k,v in p.units.items()}
    bank_busy = [0] * p.bank_count
    dram_next_cycle = 0
    next_frontend = 0
    cycle = 0
    frontend_blocked_until = 0
    retired = 0
    max_rob = 0
    max_scheduler = 0
    issue_peak_ops_per_cycle = 0
    rac_read_slots_granted = 0
    rac_write_slots_granted = 0
    rac_peak_read_slots_per_cycle = 0
    rac_peak_write_slots_per_cycle = 0
    hits = {"L1":0,"L2":0,"L3":0,"L4":0,"DRAM":0}
    branch_misses = 0
    stalls = {"dependency_blocked_op_cycles": 0, "issue_width_blocked_op_cycles": 0,
              "execution_unit_blocked_op_cycles": 0, "rac_read_budget_blocked_op_cycles": 0,
              "rac_write_budget_blocked_op_cycles": 0,
              "rac_physical_read_port_blocked_op_cycles": 0,
              "rac_physical_write_port_blocked_op_cycles": 0,
              "rac_destination_conflict_op_cycles": 0,
              "frontend_limited_cycles": 0,
              "rob_full_cycles": 0, "scheduler_full_cycles": 0,
              "branch_recovery_cycles": 0,
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
            elif len(scheduler) >= scheduler_capacity:
                stalls["scheduler_full_cycles"] += 1
        d = 0
        while (next_frontend < len(ops) and d < p.dispatch and
               len(rob) < p.rob and len(scheduler) < scheduler_capacity and cycle >= frontend_blocked_until):
            op = ops[next_frontend]
            # Front-end throughput is separately modelled from dispatch.
            if d >= p.frontend:
                break
            dispatched[op.seq] = True
            rob.append(op.seq)
            scheduler.append(op.seq)
            next_frontend += 1; d += 1
        max_rob = max(max_rob, len(rob))
        max_scheduler = max(max_scheduler, len(scheduler))
        if next_frontend < len(ops) and cycle >= frontend_blocked_until and len(rob) < p.rob and d >= min(p.dispatch, p.frontend):
            stalls["frontend_limited_cycles"] += 1

        # Select ready operations oldest-first; dependencies may execute out of order.
        issued_this_cycle = 0
        rac_reads_this_cycle = 0
        rac_writes_this_cycle = 0
        physical_reads_this_cycle = {}
        physical_writes_this_cycle = {}
        rac_destinations_this_cycle = set()
        for seq in list(scheduler):
            op = ops[seq]
            if any(not done[x] for x in op.deps):
                stalls["dependency_blocked_op_cycles"] += 1
                continue
            if issued_this_cycle >= p.issue:
                stalls["issue_width_blocked_op_cycles"] += 1
                continue
            kind = op.kind
            exec_kind = execution_resource_kind(kind, p.matrix_unit, unit_busy)
            # Reference CPU profiles without a dedicated FMA pool model FMA
            # through their generic FP resource. NEXSUS has an explicit FMA pool.
            resource = exec_kind if exec_kind in unit_busy else ("FP" if kind == "FMA" else exec_kind)
            slots = unit_busy.get(resource, [])
            selected_slots = None
            topology = getattr(p, "execution_topology", {}) or {}
            if resource in ("INT", "ARITH") and op.exec_width_bits >= 128 and topology.get("ARITH128_PAIRS", topology.get("INT128_PAIRS")):
                selected_slots = next(
                    (pair for pair in topology.get("ARITH128_PAIRS", topology.get("INT128_PAIRS", []))
                     if all(index < len(slots) and slots[index] <= cycle for index in pair)),
                    None,
                )
            elif resource in ("INT", "ARITH") and topology.get("ARITH128_PAIRS", topology.get("INT128_PAIRS")):
                slot = next((i for i,t in enumerate(slots) if t <= cycle), None)
                selected_slots = [slot] if slot is not None else None
            else:
                slot = next((i for i,t in enumerate(slots) if t <= cycle), None)
                selected_slots = [slot] if slot is not None else None
            if not selected_slots:
                stalls["execution_unit_blocked_op_cycles"] += 1
                continue
            op_rac_reads, op_rac_writes = rac_operand_footprint(op, p)
            if (p.rac_read_budget > 0 and
                    rac_reads_this_cycle + op_rac_reads > p.rac_read_budget):
                stalls["rac_read_budget_blocked_op_cycles"] += 1
                continue
            if (p.rac_write_budget > 0 and
                    rac_writes_this_cycle + op_rac_writes > p.rac_write_budget):
                stalls["rac_write_budget_blocked_op_cycles"] += 1
                continue

            read_accesses = op.rac_read_accesses
            write_accesses = op.rac_write_accesses
            subbank_mode = p.rac_physical_bank_counts is not None
            physical_ports_enabled = (
                p.rac_physical_read_ports is not None or
                p.rac_physical_write_ports is not None or
                subbank_mode or
                p.rac_physical_read_ports_per_bank is not None or
                p.rac_physical_write_ports_per_bank is not None
            )
            if subbank_mode:
                for register_class, count in p.rac_physical_bank_counts.items():
                    if not isinstance(count, int) or count < 1:
                        raise ValueError(
                            f"invalid physical RAC bank count for {register_class}: {count!r}"
                        )
                if (p.rac_physical_read_ports_per_bank is None or
                        p.rac_physical_write_ports_per_bank is None):
                    raise ValueError("sub-bank mode requires both per-bank read and write port maps")
                missing_reads = set(p.rac_physical_bank_counts) - set(p.rac_physical_read_ports_per_bank)
                missing_writes = set(p.rac_physical_bank_counts) - set(p.rac_physical_write_ports_per_bank)
                if missing_reads or missing_writes:
                    raise ValueError(
                        f"sub-bank port maps missing register classes: reads={sorted(missing_reads)}, "
                        f"writes={sorted(missing_writes)}"
                    )
            if physical_ports_enabled and (read_accesses is None or write_accesses is None):
                if op_rac_reads or op_rac_writes:
                    raise ValueError(
                        f"op {op.seq} needs explicit RAC bank/index metadata "
                        "when physical RF ports are enabled"
                    )
                read_accesses = read_accesses or ()
                write_accesses = write_accesses or ()
            read_accesses = tuple(read_accesses or ())
            write_accesses = tuple(write_accesses or ())
            def normalize_accesses(accesses, direction):
                normalized = []
                for access in accesses:
                    if (not isinstance(access, (tuple, list)) or len(access) != 3 or
                            not isinstance(access[0], str) or not access[0] or
                            not isinstance(access[1], int) or access[1] < 0 or
                            not isinstance(access[2], int) or access[2] < 1):
                        raise ValueError(
                            f"op {op.seq} has invalid RAC {direction} access {access!r}"
                        )
                    normalized.append((access[0], access[1], access[2]))
                return normalized
            read_accesses = normalize_accesses(read_accesses, "read")
            write_accesses = normalize_accesses(write_accesses, "write")
            if op.rac_read_accesses is not None and sum(x[2] for x in read_accesses) != op_rac_reads:
                raise ValueError(f"op {op.seq} RAC read slots do not match bank metadata")
            if op.rac_write_accesses is not None and sum(x[2] for x in write_accesses) != op_rac_writes:
                raise ValueError(f"op {op.seq} RAC write slots do not match bank metadata")

            read_counts = {}
            write_counts = {}
            def physical_bank_key(register_class, register_index):
                if subbank_mode:
                    count = p.rac_physical_bank_counts.get(register_class, 0)
                    if count < 1:
                        raise ValueError(
                            f"missing physical RAC sub-bank count for {register_class}"
                        )
                    return (register_class, register_index % count)
                return register_class
            for register_class, register_index, _slots in read_accesses:
                key = physical_bank_key(register_class, register_index)
                read_counts[key] = read_counts.get(key, 0) + 1
            for register_class, register_index, _slots in write_accesses:
                key = physical_bank_key(register_class, register_index)
                write_counts[key] = write_counts.get(key, 0) + 1
            destinations = [(bank, index) for bank, index, _slots in write_accesses]
            if len(destinations) != len(set(destinations)):
                raise ValueError(f"op {op.seq} writes one register more than once")
            if any(destination in rac_destinations_this_cycle for destination in destinations):
                stalls["rac_destination_conflict_op_cycles"] += 1
                continue
            read_port_map = (p.rac_physical_read_ports_per_bank
                             if subbank_mode else p.rac_physical_read_ports)
            if subbank_mode:
                for bank, count in read_counts.items():
                    limit = read_port_map.get(bank[0], 0)
                    if count > limit:
                        raise ValueError(
                            f"op {op.seq} requires {count} physical RAC reads from "
                            f"{bank[0]} sub-bank {bank[1]}, configured limit is {limit}"
                        )
            if read_port_map is not None and any(
                physical_reads_this_cycle.get(bank, 0) + count >
                read_port_map.get(bank[0] if subbank_mode else bank, 0)
                for bank, count in read_counts.items()
            ):
                stalls["rac_physical_read_port_blocked_op_cycles"] += 1
                continue
            write_port_map = (p.rac_physical_write_ports_per_bank
                              if subbank_mode else p.rac_physical_write_ports)
            if subbank_mode:
                for bank, count in write_counts.items():
                    limit = write_port_map.get(bank[0], 0)
                    if count > limit:
                        raise ValueError(
                            f"op {op.seq} requires {count} physical RAC writes to "
                            f"{bank[0]} sub-bank {bank[1]}, configured limit is {limit}"
                        )
            if write_port_map is not None and any(
                physical_writes_this_cycle.get(bank, 0) + count >
                write_port_map.get(bank[0] if subbank_mode else bank, 0)
                for bank, count in write_counts.items()
            ):
                stalls["rac_physical_write_port_blocked_op_cycles"] += 1
                continue
            vector_factor = (max(1, math.ceil(op.exec_width_bits / p.vector_bits))
                             if is_vector_operation(kind) or (kind == "ME512" and exec_kind == "VEC") else 1)
            base_latency = (p.latency.get("FMA", p.latency.get("FP", 1))
                            if kind == "FMA" else p.latency.get(exec_kind, 1))
            latency = base_latency * vector_factor
            if kind in ("LOAD", "STORE", "ATOM"):
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
            for slot_index in selected_slots:
                slots[slot_index] = cycle + 1
            issued[seq] = True
            scheduler.remove(seq)
            ready_at[seq] = cycle + latency
            if kind in ("LOAD", "STORE", "ATOM"):
                stalls["memory_latency_exposure_cycles"] += max(0, latency - 1)
            issued_this_cycle += 1
            rac_reads_this_cycle += op_rac_reads
            rac_writes_this_cycle += op_rac_writes
            for bank, count in read_counts.items():
                physical_reads_this_cycle[bank] = physical_reads_this_cycle.get(bank, 0) + count
            for bank, count in write_counts.items():
                physical_writes_this_cycle[bank] = physical_writes_this_cycle.get(bank, 0) + count
            rac_destinations_this_cycle.update(destinations)
            rac_read_slots_granted += op_rac_reads
            rac_write_slots_granted += op_rac_writes
            rac_peak_read_slots_per_cycle = max(rac_peak_read_slots_per_cycle, rac_reads_this_cycle)
            rac_peak_write_slots_per_cycle = max(rac_peak_write_slots_per_cycle, rac_writes_this_cycle)
            if kind == "BR":
                branch_number += 1
                if branch_mispredict(op, branch_number, p.branch_predictor):
                    branch_misses += 1
                    frontend_blocked_until = max(frontend_blocked_until, cycle + p.branch_penalty)
        issue_peak_ops_per_cycle = max(issue_peak_ops_per_cycle, issued_this_cycle)
        cycle += 1
    if retired != len(ops):
        raise RuntimeError(f"simulation did not drain: retired {retired}/{len(ops)}")
    return {
        "cycles": cycle, "ops": len(ops), "retired_ops": retired,
        "completed": retired == len(ops), "ipc": round(retired/max(1,cycle), 3),
        "max_rob_occupancy": max_rob, "max_scheduler_occupancy": max_scheduler,
        "issue_peak_ops_per_cycle": issue_peak_ops_per_cycle,
        "rac_read_slots_granted": rac_read_slots_granted,
        "rac_write_slots_granted": rac_write_slots_granted,
        "rac_peak_read_slots_per_cycle": rac_peak_read_slots_per_cycle,
        "rac_peak_write_slots_per_cycle": rac_peak_write_slots_per_cycle,
        "branch_mispredicts": branch_misses,
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
            if op.label.startswith("CS working set"):
                command_pc = (new_seq % 256) * 8
            elif op.label.startswith("CS starvation"):
                command_pc = new_seq * 8
            elif op.label.startswith("CS sequential") or op.label.startswith("CS branch"):
                command_pc = new_seq * 8
            else:
                command_pc = op.command_address if op.command_address >= 0 else new_seq * 8
            shard.append(Op(new_seq, op.kind,
                            tuple(remap[d] for d in op.deps if d in remap),
                            op.address, op.width, op.label, command_pc,
                            op.exec_width_bits))
        if shard:
            shards.append(shard)
    return shards

def simulate_multicore_streams(shards: List[List[Op]], p: CoreProfile,
                               aggregate_dram_bandwidth: int,
                               nexus_features=None) -> dict:
    """Lockstep cores with independent App RAM and Data RAM controllers.

    Per-core pipelines, ROBs and caches remain private approximations. All
    cores advance on one global cycle. Instruction-page requests are admitted
    by the separate AppRamController; data misses are batched through the
    SharedMemoryController. Both timelines advance on the same global cycle.
    """
    features = {"spm": True, "p0": True, "codeflow": False}
    if nexus_features:
        features.update(nexus_features)
        # Canonical public feature names; legacy internal keys remain an implementation detail.
        if "task_workspace" in nexus_features:
            features["spm"] = bool(nexus_features["task_workspace"])
        if "code_slots" in nexus_features:
            features["p0"] = bool(nexus_features["code_slots"])
    is_nexus = p.name.startswith("NEXSUS CPU")
    # App RAM instruction fetches use a separate controller from Data RAM.
    app_controller = AppRamController(
        bank_count=int(features.get("app_bank_count", 8)),
        beat_bytes=int(features.get("app_beat_bytes", 8)),
        bytes_per_cycle=int(features.get("app_bytes_per_cycle", 64)),
        first_beat_latency=int(features.get("app_first_beat_latency", 40)),
        beat_interval=int(features.get("app_beat_interval", 1)),
        max_outstanding=int(features.get("app_max_outstanding", 16)),
    ) if is_nexus and bool(features.get("codeflow", False)) else None
    states = []
    for shard in shards:
        states.append({
            "ops": shard, "cache": None, "fetch": None,
            "spm_busy_until": 0,
            "spm": {"accesses": 0, "bytes": 0, "port_conflicts": 0, "overflow": 0, "fallback_bytes": 0},
            "ready_at": [0] * len(shard), "done": [False] * len(shard), "issue_cycles": [],
            "issued": [False] * len(shard), "dispatched": [False] * len(shard),
            "rob": deque(), "scheduler": deque(), "scheduler_capacity": (p.scheduler_entries if p.scheduler_entries > 0 else p.rob),
            "unit_busy": {k: [0] * v for k, v in p.units.items()},
            "next_frontend": 0, "frontend_blocked_until": 0, "retired": 0, "last_pc": None,
            "max_rob": 0, "max_scheduler": 0, "hits": {"L1":0,"L2":0,"L3":0,"L4":0,"DRAM":0},
            "branch_misses": 0, "branch_number": 0,
            "mshr_inflight": [],
            "mshr_max_outstanding": 0, "mshr_full_events": 0,
            "mshr_full_cycles": 0, "mshr_blocked_this_cycle": False,
            "stalls": {"dependency_blocked_op_cycles": 0,
                       "issue_width_blocked_op_cycles": 0,
                       "execution_unit_blocked_op_cycles": 0,
                       "frontend_limited_cycles": 0, "rob_full_cycles": 0,
                       "scheduler_full_cycles": 0,
                       "branch_recovery_cycles": 0,
                       "memory_latency_exposure_cycles": 0,
                       "data_mshr_full_events": 0}
        })
    cache_hierarchies = build_cache_hierarchies(p, len(states))
    # Optional untimed preloaded working set. Select its home level from the
    # collaborating core-group width (1/2/4/8+ -> L1/L2/L3/L4). Insert each
    # line once per distinct shared cache object, not once per participating core.
    prefill_addresses = features.get("cache_prefill_addresses", ())
    prefill_level = features.get("cache_prefill_level", "L1")
    if prefill_addresses:
        if prefill_level not in ("L1", "L2", "L3", "L4"):
            raise ValueError(f"Unsupported cache prefill level: {prefill_level}")
        seen_cache_objects = set()
        for hierarchy in cache_hierarchies:
            cache_object = getattr(hierarchy, prefill_level.lower(), None)
            if cache_object is None:
                raise ValueError(f"Cache prefill level {prefill_level} is unavailable")
            if id(cache_object) in seen_cache_objects:
                continue
            seen_cache_objects.add(id(cache_object))
            for address in prefill_addresses:
                hierarchy.prefill(int(address), prefill_level)
    for core_id, st in enumerate(states):
        st["cache"] = cache_hierarchies[core_id]
        if is_nexus:
            st["fetch"] = CommandFetchModel(
                bool(features["p0"]),
                p0_capacity_bytes=int(features.get("p0_capacity_kb", 16)) * 1024,
                p0_refill_latency=int(features.get("p0_refill_latency", 48)),
                p0_buffer_bytes=int(features.get("p0_buffer_bytes", 2048)),
                page_descriptors=(features.get("px_page_descriptors") or
                                  build_command_page_descriptors(
                                      shard, int(features.get("p0_buffer_bytes", 2048))
                                  )),
                pool_miss_latency=int(features.get("px_pool_miss_latency", 120)),
                codeflow_enabled=bool(features.get("codeflow", False)),
                code_cache_bytes=int(features.get("code_cache_kb", 64)) * 1024,
                app_first_beat_latency=int(features.get("app_first_beat_latency", 40)),
                app_beat_interval=int(features.get("app_beat_interval", 1)),
                c0_to_cs_bytes_per_cycle=int(features.get("c0_to_cs_bytes_per_cycle", 20)),
                cs_to_eb_bytes_per_cycle=int(features.get("cs_to_eb_bytes_per_cycle", 20)),
                app_ram_controller=app_controller if bool(features.get("codeflow", False)) else None,
                core_id=core_id,
                known_page_ids={
                    max(0, (op.command_address if op.command_address >= 0 else op.seq * 8))
                    // int(features.get("p0_buffer_bytes", 2048))
                    for op in shard
                },
                conventional_capacity_bytes=int(features.get("conventional_icache_kb", 32)) * 1024,
                conventional_refill_latency=int(features.get("conventional_refill_latency", 8)),
            )
        else:
            # Give reference CPUs an explicit conventional instruction-fetch
            # path instead of silently granting zero-latency command delivery.
            st["fetch"] = CommandFetchModel(
                False,
                conventional_capacity_bytes=int(features.get("conventional_icache_kb", 32)) * 1024,
                conventional_refill_latency=int(features.get("conventional_refill_latency", 32)),
            )
    pending_fills = []
    data_ram_per_core = int(getattr(p, "data_ram_bytes_per_cycle_per_core", 0) or
                             (64 if is_nexus else 0))
    controller = (DataRamController(data_ram_per_core) if data_ram_per_core else
                  SharedMemoryController(
                      bank_count=p.bank_count, beat_bytes=p.bank_beat_bytes,
                      aggregate_bytes_per_cycle=aggregate_dram_bandwidth))
    cycle = 0
    limit = max(10000, sum(len(x) for x in shards) * 1000)
    while any(st["retired"] < len(st["ops"]) for st in states) and cycle < limit:
        for st in states:
            if st["fetch"] is not None:
                st["fetch"].complete(cycle)
        completed_fills = [x for x in pending_fills if x[0] <= cycle]
        pending_fills = [x for x in pending_fills if x[0] > cycle]
        # Coalesce distribution participants by identical line and completion
        # cycle. A configured core that did not request this line is not a
        # destination in the active sharing group.
        fill_groups = {}
        for ready_cycle, core_id, address, level in completed_fills:
            key = (ready_cycle, address, level)
            fill_groups.setdefault(key, []).append(core_id)
        for (_, address, level), core_ids in fill_groups.items():
            owner = min(core_ids)
            states[owner]["cache"].fill(
                address, level, active_core_count=len(core_ids),
                peer_caches=cache_hierarchies, core_id=owner,
                active_core_ids=core_ids
            )
        pending_memory = []
        mshr_capacity = features.get("data_mshr_entries")
        mshr_reserved_this_cycle = [0] * len(states)
        # MSHR entries are released only after the corresponding data fill completes.
        if mshr_capacity is not None:
            for st in states:
                st["mshr_inflight"] = [ready for ready in st["mshr_inflight"] if ready > cycle]
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
                elif len(st["scheduler"]) >= st["scheduler_capacity"]:
                    st["stalls"]["scheduler_full_cycles"] += 1
            dispatched_now = 0
            while (st["next_frontend"] < len(ops) and dispatched_now < p.dispatch and
                   dispatched_now < p.frontend and len(st["rob"]) < p.rob and
                   len(st["scheduler"]) < st["scheduler_capacity"] and
                   cycle >= st["frontend_blocked_until"]):
                op = ops[st["next_frontend"]]
                if st["fetch"] is not None and not features.get("execution_only", False):
                    pc = op.command_address if op.command_address >= 0 else op.seq * 8
                    sequential_fetch = st["last_pc"] is None or pc == st["last_pc"] + 8
                    if not st["fetch"].can_fetch(pc, cycle, sequential=sequential_fetch):
                        break
                    st["last_pc"] = pc
                st["dispatched"][op.seq] = True
                st["rob"].append(op.seq)
                st["scheduler"].append(op.seq)
                st["next_frontend"] += 1
                dispatched_now += 1
            st["max_rob"] = max(st["max_rob"], len(st["rob"]))
            st["max_scheduler"] = max(st.get("max_scheduler", 0), len(st["scheduler"]))
            if (st["next_frontend"] < len(ops) and
                cycle >= st["frontend_blocked_until"] and len(st["rob"]) < p.rob and
                dispatched_now >= min(p.dispatch, p.frontend)):
                st["stalls"]["frontend_limited_cycles"] += 1

        # Phase 3: choose per-core issue candidates. DRAM misses are deferred
        # until every core has contributed its requests for this same cycle.
        for core_id, st in enumerate(states):
            ops = st["ops"]
            st["mshr_blocked_this_cycle"] = False
            issued_now = 0
            for seq in list(st["scheduler"]):
                op = ops[seq]
                if any(not st["done"][dep] for dep in op.deps):
                    st["stalls"]["dependency_blocked_op_cycles"] += 1
                    continue
                if issued_now >= p.issue:
                    st["stalls"]["issue_width_blocked_op_cycles"] += 1
                    continue
                exec_kind = execution_resource_kind(op.kind, p.matrix_unit, st["unit_busy"])
                # Non-NEXSUS reference profiles may expose only a generic FP pool.
                resource = exec_kind if exec_kind in st["unit_busy"] else ("FP" if op.kind == "FMA" else exec_kind)
                slots = st["unit_busy"].get(resource, [])
                topology = getattr(p, "execution_topology", {}) or {}
                selected_slots = None
                if resource == "INT" and op.exec_width_bits >= 128 and topology.get("INT128_PAIRS"):
                    selected_slots = next(
                        (pair for pair in topology["INT128_PAIRS"]
                         if all(index < len(slots) and slots[index] <= cycle for index in pair)),
                        None,
                    )
                elif resource == "INT" and topology.get("INT128_PAIRS"):
                    slot_index = next((i for i, available in enumerate(slots) if available <= cycle), None)
                    selected_slots = [slot_index] if slot_index is not None else None
                else:
                    slot_index = next((i for i, available in enumerate(slots) if available <= cycle), None)
                    selected_slots = [slot_index] if slot_index is not None else None
                if not selected_slots:
                    st["stalls"]["execution_unit_blocked_op_cycles"] += 1
                    continue
                slot = selected_slots[0]
                mem_lat = 0
                level = None
                if op.kind in ("LOAD", "STORE", "ATOM"):
                    is_spm2 = op.kind != "ATOM" and op.label.startswith("TW:")
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
                        level = "TW"
                    else:
                        if is_nexus and is_spm2:
                            if features["spm"] and not in_spm:
                                st["spm"]["overflow"] += 1
                            st["spm"]["fallback_bytes"] += op.width
                        mem_lat, level = st["cache"].probe(op.address)
                        if level != "DRAM":
                            cache_port_wait = st["cache"].reserve(level, cycle, op.width)
                            mem_lat += cache_port_wait
                        if level == "DRAM" and mshr_capacity is not None:
                            outstanding = len(st["mshr_inflight"]) + mshr_reserved_this_cycle[core_id]
                            if outstanding >= int(mshr_capacity):
                                st["mshr_full_events"] += 1  # blocked request-attempt cycles
                                st["stalls"]["data_mshr_full_events"] += 1
                                if not st["mshr_blocked_this_cycle"]:
                                    st["mshr_full_cycles"] += 1
                                    st["mshr_blocked_this_cycle"] = True
                                continue
                            mshr_reserved_this_cycle[core_id] += 1
                        st["hits"][level] += 1
                item = {"core": core_id, "seq": seq, "slot": slot,
                        "latency": max((p.latency.get("FMA", p.latency.get(resource, 1))
                                         if op.kind == "FMA" else p.latency.get(exec_kind, 1)) *
                                       (max(1, math.ceil(op.exec_width_bits / p.vector_bits)) if is_vector_operation(op.kind) or (op.kind == "ME512" and exec_kind == "VEC") else 1),
                                       mem_lat),
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
                st["scheduler"].remove(seq)
                st["issue_cycles"].append(cycle)
                for slot_index in selected_slots:
                    slots[slot_index] = cycle + 1
                item["branch"] = op.kind == "BR"
                item["memory"] = op.kind in ("LOAD", "STORE", "ATOM")
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
            if item["request_id"] is not None and mshr_capacity is not None:
                st["mshr_inflight"].append(cycle + latency)
                st["mshr_max_outstanding"] = max(
                    st["mshr_max_outstanding"], len(st["mshr_inflight"])
                )
            if item["memory"]:
                pending_fills.append((cycle + latency, item["core"], st["ops"][seq].address, item["level"]))
                st["stalls"]["memory_latency_exposure_cycles"] += max(0, latency - 1)
            if item["branch"]:
                st["branch_number"] += 1
                if branch_mispredict(st["ops"][seq], st["branch_number"], p.branch_predictor):
                    st["branch_misses"] += 1
                    st["frontend_blocked_until"] = max(
                        st["frontend_blocked_until"], cycle + p.branch_penalty)

        cycle += 1

    if any(st["retired"] != len(st["ops"]) for st in states):
        totals = [f"{st['retired']}/{len(st['ops'])}" for st in states]
        raise RuntimeError(f"multicore simulation did not drain at cycle {cycle}: {totals}")
    return {"cycles": cycle, "cores": states,
            "data_mshr": {
                "capacity_per_core": (int(mshr_capacity) if mshr_capacity is not None else None),
                "max_outstanding_per_core": [st["mshr_max_outstanding"] for st in states],
                # A blocked request is retried on later cycles; these counters
                # deliberately distinguish retry attempts from unique full cycles.
                "full_events_per_core": [st["mshr_full_events"] for st in states],
                "total_full_events": sum(st["mshr_full_events"] for st in states),
                "blocked_request_attempts_per_core": [st["mshr_full_events"] for st in states],
                "total_blocked_request_attempts": sum(st["mshr_full_events"] for st in states),
                "full_cycles_per_core": [st["mshr_full_cycles"] for st in states],
                "total_full_cycles": sum(st["mshr_full_cycles"] for st in states),
            },
            "app_controller": ({"bank_count_per_core": app_controller.bank_count,
                                "per_core_bytes_per_cycle": app_controller.bytes_per_cycle,
                                "active_core_count": len(states),
                                "aggregate_bytes_per_cycle": app_controller.bytes_per_cycle * len(states),
                                "max_outstanding_per_core": app_controller.max_outstanding,
                                "max_outstanding": app_controller.max_outstanding,
                                "accepted": app_controller.accepted,
                                "queue_rejections": app_controller.rejected_queue_full,
                                "bank_conflicts": app_controller.bank_conflicts,
                                "transferred_bytes": app_controller.transferred_bytes,
                                "bytes_by_core": app_controller.bytes_by_core,
                                "request_cycles": sorted(set(app_controller.request_cycles)),
                                "request_events": app_controller.request_events}
                               if app_controller is not None else None),
            "controller": ({
                           "model": "per_core_fabric_ports",
                           "per_core_bytes_per_cycle": controller.bytes_per_cycle_per_core,
                           "active_core_count": len(states),
                           "aggregate_core_facing_capacity_bytes_per_cycle": controller.bytes_per_cycle_per_core * len(states),
                           "accepted": controller.accepted,
                           "bus_next_cycle": controller.bus_next_cycle,
                           "transferred_bytes": controller.transferred_bytes,
                           "bytes_by_core": controller.bytes_by_core,
                           "request_cycles": sorted(set(controller.request_cycles)),
                           "request_events": controller.request_events
                         } if isinstance(controller, DataRamController) else {
                           "model": "legacy_shared_controller",
                           "bank_count": p.bank_count,
                           "aggregate_dram_bytes_per_cycle": aggregate_dram_bandwidth,
             "dram_latency_cycles": p.dram_lat,
                           "bank_busy_until": controller.bank_busy,
                           "bus_next_cycle": controller.bus_next_cycle,
                           "request_cycles": sorted(set(controller.request_cycles)),
                           "request_events": controller.request_events})}


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
            "issue_span_cycles": (max(cycle for x in per_core for cycle in x["issue_cycles"]) - min(cycle for x in per_core for cycle in x["issue_cycles"]) + 1) if any(x["issue_cycles"] for x in per_core) else 0,
            "aggregate_ipc": round(total_ops/max(1, elapsed_cycles), 3),
            "core_cycles_sum": elapsed_cycles * len(per_core),
            "active_cores": len(per_core),
            "per_core_cycles": [elapsed_cycles for _ in per_core],
            "max_rob_occupancy": max((x["max_rob"] for x in per_core), default=0),
            "max_scheduler_occupancy": max((x.get("max_scheduler", 0) for x in per_core), default=0),
            "branch_mispredicts": sum(x["branch_misses"] for x in per_core),
            "cache_accesses": cache_totals,
            "stall_counters": {k: sum(x["stalls"][k] for x in per_core)
                               for k in stall_keys},
            "memory_controller": simulation["controller"],
            "data_mshr": simulation["data_mshr"],
            "app_ram_controller": simulation["app_controller"],
            "workspace_counters": {k: sum(x["spm"][k] for x in per_core)
                             for k in ("accesses", "bytes", "port_conflicts", "overflow", "fallback_bytes")},
            "codeflow_counters": {
                "hits": sum(x["fetch"].hits for x in per_core if x["fetch"] is not None),
                "refills": sum(x["fetch"].refills for x in per_core if x["fetch"] is not None),
                "refill_bytes": sum(x["fetch"].refill_bytes for x in per_core if x["fetch"] is not None),
                "wait_cycles": sum(x["fetch"].wait_cycles for x in per_core if x["fetch"] is not None),
                "bank_switches": sum(x["fetch"].bank_switches for x in per_core if x["fetch"] is not None),
                "ready_boundaries": sum(x["fetch"].ready_boundaries for x in per_core if x["fetch"] is not None),
                "boundary_waits": sum(x["fetch"].boundary_waits for x in per_core if x["fetch"] is not None),
                "useful_bytes": sum(x["fetch"].useful_bytes for x in per_core if x["fetch"] is not None),
                "pool_hits": sum(x["fetch"].pool_hits for x in per_core if x["fetch"] is not None),
                "pool_misses": sum(x["fetch"].pool_misses for x in per_core if x["fetch"] is not None),
                "pool_refill_bytes": sum(x["fetch"].pool_refill_bytes for x in per_core if x["fetch"] is not None),
                "code_cache_hits": sum(x["fetch"].c0_hits for x in per_core if x["fetch"] is not None),
                "code_cache_misses": sum(x["fetch"].c0_misses for x in per_core if x["fetch"] is not None),
                "app_ram_beats": sum(x["fetch"].app_beats for x in per_core if x["fetch"] is not None),
                "app_ram_bytes": sum(x["fetch"].app_bytes for x in per_core if x["fetch"] is not None),
                "app_source_cycles": sum(x["fetch"].app_source_cycles for x in per_core if x["fetch"] is not None),
                "code_slot_transfer_cycles": sum(x["fetch"].code_slot_cycles for x in per_core if x["fetch"] is not None),
                "code_stream_transfer_cycles": sum(x["fetch"].code_stream_cycles for x in per_core if x["fetch"] is not None),
                "mode": ("execution-only backend isolation" if nexus_features and nexus_features.get("execution_only", False)
                         else ("CodeFlow C0 -> CS -> EB" if p.name.startswith("NEXSUS CPU") and
                               (nexus_features is None or nexus_features.get("p0", True))
                               else "conventional I-cache"))
            },
            "parallel_model": "lockstep multicore; private L1; NEXSUS L2 shared per 2 cores, L3 per 4 and L4 per 8; reference CPU caches remain per-core approximations; shared DRAM banks and work-conserving aggregate bus; coherence not modeled"
        }
    total_cycles = sum(v["cycles"] for v in results.values())
    total_ops = sum(v["ops"] for v in results.values())
    return {"cpu": p.name, "cores_configured": cores, "clock_ghz": p.frequency_ghz,
            "rob_entries": p.rob, "scheduler_entries_per_core": (p.scheduler_entries if p.scheduler_entries > 0 else p.rob),
            "nexus_features": ({"task_workspace": True, "code_slots": True, "p0_capacity_kb": 16, "eb_kb": 4, "eb_bank_kb": 2, "p0_refill_latency": 48, "branch_predictor": p.branch_predictor} if nexus_features is None else nexus_features) if p.name.startswith("NEXSUS CPU") else None,
            "register_architecture": ({"RA": {"count": 32, "width_bits": 64}, "FA": {"count": 32, "width_bits": 64}, "DA": {"count": 32, "width_bits": 64}, "MA": {"count": 32, "width_bits": 256}, "selector_bits": 5, "total_physical_bytes": 1792} if p.name.startswith("NEXSUS CPU") else None),
            "cpu_ram_reference_clock_ghz": p.frequency_ghz,
            "aggregate_dram_bytes_per_cycle": aggregate_dram_bandwidth,
            "dram_latency_cycles": p.dram_lat,
            "per_core_dram_bytes_per_cycle": (p.data_ram_bytes_per_cycle_per_core or None),
            "dram_bandwidth_policy": ("per-core Fabric-facing DataRAM ports; aggregate capacity scales with active cores" if p.data_ram_bytes_per_cycle_per_core > 0 else "shared lockstep controller; work-conserving aggregate bus; no static per-core quota"),
            "kernels": results, "total_cycles": total_cycles, "total_ops": total_ops,
            "aggregate_ipc": round(total_ops/max(1,total_cycles),3),
            "time_ms_at_configured_clock": round(total_cycles/(p.frequency_ghz*1e6),6)}

def run_execution_topology_sweep(workloads: Dict[str, List[Op]], profile_dict: dict) -> dict:
    """Compare baseline execution resources with the proposed mixed-width NEXSUS topology."""
    target = {name: workloads[name] for name in (
        "integer_throughput", "integer128_throughput", "fp_throughput",
        "numeric_tile", "streaming", "scalar_control"
    )}
    variants = {
        "baseline_2INT_2FP": {
            "units": {**profile_dict["units"], "INT": 2, "FP": 2},
            # The two baseline INT64 lanes must cooperate for one 128-bit op.
            "execution_topology": {"INT128_PAIRS": [[0, 1]]},
        },
        "proposed_2x128_plus_4x64_INT__6x64_FP": {
            "units": {**profile_dict["units"], "INT": 8, "FP": 6},
            "execution_topology": {"INT128_PAIRS": [[0, 1], [2, 3]]},
        },
    }
    runs = {}
    for name, config in variants.items():
        profile = dict(profile_dict)
        profile["units"] = config["units"]
        profile["execution_topology"] = config["execution_topology"]
        runs[name] = simulate_cpu(
            target, profile, 8,
            {"task_workspace": True, "code_slots": True, "codeflow": True,
             "p0_capacity_kb": 16, "p0_refill_latency": 48},
        )
    rows = {}
    for kernel in target:
        base = runs["baseline_2INT_2FP"]["kernels"][kernel]
        proposed = runs["proposed_2x128_plus_4x64_INT__6x64_FP"]["kernels"][kernel]
        rows[kernel] = {
            "ops_preserved": base["ops"] == proposed["ops"],
            "ops": base["ops"],
            "baseline_cycles": base["cycles"],
            "proposed_cycles": proposed["cycles"],
            "cycles_saved": base["cycles"] - proposed["cycles"],
            "improvement_percent": round(
                100 * (base["cycles"] - proposed["cycles"]) / max(1, base["cycles"]), 2
            ),
            "baseline_int_fp_unit_stalls": base["stall_counters"]["execution_unit_blocked_op_cycles"],
            "proposed_int_fp_unit_stalls": proposed["stall_counters"]["execution_unit_blocked_op_cycles"],
        }
    return {
        "experiment": "NEXSUS mixed-width INT and six-lane FP execution topology",
        "cores": 8,
        "variants": {
            name: {"units": config["units"], "execution_topology": config["execution_topology"],
                   "total_cycles": run["total_cycles"], "total_ops": run["total_ops"]}
            for name, (config, run) in zip(variants.keys(), zip(variants.values(), runs.values()))
        },
        "kernels": rows,
        "assumptions": (
            "Baseline has two 64-bit INT lanes which must pair to execute one 128-bit operation. "
            "The proposal has eight 64-bit issue lanes: lanes 0-1 and 2-3 form two 128-bit-capable "
            "pairs, while lanes 4-7 remain independent 64-bit lanes. Each pair can instead issue "
            "two independent 64-bit operations. INT128 ops reserve both lanes of one pair for one cycle. "
            "FP has six independent 64-bit lanes. "
            "FMA and IEEE binary128 are not modeled. Frontend/dispatch/issue limits remain unchanged."
        ),
    }



def run_execution_resource_count_sweep(workloads: Dict[str, List[Op]], profile_dict: dict,
                                       int_counts=(2, 4, 6, 8, 10),
                                       fp_counts=(2, 4, 6, 8)) -> dict:
    """Sweep per-core INT/FP issue resources while holding all other assumptions fixed."""
    target = {name: workloads[name] for name in (
        "integer_throughput", "integer128_throughput", "fp_throughput",
        "numeric_tile", "scalar_control"
    )}
    rows = {}
    expected_ops = {name: len(ops) for name, ops in target.items()}
    for int_count in int_counts:
        pairs = [[i, i + 1] for i in range(0, int_count - 1, 2)]
        for fp_count in fp_counts:
            profile = dict(profile_dict)
            profile["units"] = {**profile_dict["units"], "INT": int_count, "FP": fp_count}
            profile["execution_topology"] = {"INT128_PAIRS": pairs}
            run = simulate_cpu(
                target, profile, 8,
                {"task_workspace": False, "code_slots": False},
            )
            key = f"INT{int_count}_FP{fp_count}"
            kernels = {}
            for name, row in run["kernels"].items():
                kernels[name] = {
                    "ops": row["ops"],
                    "ops_preserved": row["ops"] == expected_ops[name],
                    "cycles": row["cycles"],
                    "ipc": row["aggregate_ipc"],
                    "execution_unit_blocked_op_cycles":
                        row["stall_counters"]["execution_unit_blocked_op_cycles"],
                    "dependency_blocked_op_cycles":
                        row["stall_counters"]["dependency_blocked_op_cycles"],
                    "issue_width_blocked_op_cycles":
                        row["stall_counters"]["issue_width_blocked_op_cycles"],
                }
            rows[key] = {
                "int_lanes_per_core": int_count,
                "int128_pairs_per_core": len(pairs),
                "fp64_lanes_per_core": fp_count,
                "total_cycles": run["total_cycles"],
                "total_ops": run["total_ops"],
                "kernels": kernels,
            }
    if any(not row["ops_preserved"] for variant in rows.values()
           for row in variant["kernels"].values()):
        raise AssertionError("resource-count sweep changed logical operation count")
    return {
        "experiment": "NEXSUS per-core INT/FP execution resource count sweep",
        "cores": 8,
        "int_counts": list(int_counts),
        "fp_counts": list(fp_counts),
        "same_logical_workload": expected_ops,
        "results": rows,
        "assumptions": (
            "Only per-core INT and FP unit counts change. INT128 pairs are adjacent "
            "64-bit lanes; each 128-bit operation reserves one complete pair. All "
            "variants use the same eight-core lockstep model, issue/frontend widths, "
            "latencies, caches, and logical operations. FMA and IEEE binary128 are "
            "not modeled. Results are simulator estimates, not silicon measurements."
        ),
    }



def run_fma_resource_sweep(workloads: Dict[str, List[Op]], profile_dict: dict,
                           fp_counts=(6,), fma_counts=(4,)) -> dict:
    """Sweep physically independent FP64 and dedicated FMA execution pools."""
    target = {name: workloads[name] for name in (
        "fp_throughput", "fma_throughput", "fma_dependency_chain",
        "fp_fma_mixed", "numeric_tile", "scalar_control"
    )}
    expected_ops = {name: len(ops) for name, ops in target.items()}
    rows = {}
    for fp_count in fp_counts:
        for fma_count in fma_counts:
            if fp_count < 1 or fma_count < 1:
                raise ValueError("FP and FMA execution counts must be positive")
            profile = dict(profile_dict)
            profile["units"] = {**profile_dict["units"], "INT": 8,
                                "FP": int(fp_count), "FMA": int(fma_count)}
            profile["execution_topology"] = {"INT128_PAIRS": [[0, 1], [2, 3]]}
            run = simulate_cpu(target, profile, 8,
                               {"task_workspace": False, "code_slots": False})
            key = f"FP{fp_count}_FMA{fma_count}"
            kernels = {}
            for name, row in run["kernels"].items():
                kernels[name] = {
                    "ops": row["ops"], "ops_preserved": row["ops"] == expected_ops[name],
                    "cycles": row["cycles"], "ipc": row["aggregate_ipc"],
                    "execution_unit_blocked_op_cycles": row["stall_counters"]["execution_unit_blocked_op_cycles"],
                    "dependency_blocked_op_cycles": row["stall_counters"]["dependency_blocked_op_cycles"],
                    "issue_width_blocked_op_cycles": row["stall_counters"]["issue_width_blocked_op_cycles"],
                    "issue_span_cycles": row["issue_span_cycles"],
                }
            rows[key] = {"fp64_lanes_per_core": int(fp_count),
                         "dedicated_fma_units_per_core": int(fma_count),
                         "total_cycles": run["total_cycles"], "total_ops": run["total_ops"],
                         "kernels": kernels}
    if any(not row["ops_preserved"] for variant in rows.values()
           for row in variant["kernels"].values()):
        raise AssertionError("FP/FMA sweep changed logical operation count")
    return {
        "experiment": "NEXSUS independent FP64 lanes and dedicated FMA units",
        "cores": 8, "fp_counts": list(fp_counts), "fma_counts": list(fma_counts),
        "same_logical_workload": expected_ops, "results": rows,
        "assumptions": (
            "FP64 and FMA use separate execution availability arrays. FP operations "
            "cannot consume FMA slots and FMA operations cannot consume FP64 slots. "
            "Global issue width and shared FA register-bank port limits remain separate; "
            "FA port capacity is not assumed to scale with unit count. Simulator estimates."
        ),
    }


def run_fma_latency_sweep(workloads: Dict[str, List[Op]], profile_dict: dict,
                          latencies=(3, 4, 5, 6), fp_count=6, fma_count=4) -> dict:
    """Sweep FMA result latency on its independent dedicated execution pool."""
    target = {name: workloads[name] for name in (
        "fp_throughput", "fma_throughput", "fma_dependency_chain", "fp_fma_mixed"
    )}
    expected_ops = {name: len(ops) for name, ops in target.items()}
    rows = {}
    for fma_latency in latencies:
        profile = dict(profile_dict)
        profile["units"] = {**profile_dict["units"], "FP": int(fp_count),
                            "FMA": int(fma_count)}
        profile["latency"] = {**profile_dict["latency"], "FMA": int(fma_latency)}
        profile["execution_topology"] = dict(profile_dict.get("execution_topology", {}) or {})
        run = simulate_cpu(target, profile, 8,
                           {"task_workspace": False, "code_slots": False})
        kernels = {}
        for name, row in run["kernels"].items():
            kernels[name] = {
                "ops": row["ops"], "ops_preserved": row["ops"] == expected_ops[name],
                "cycles": row["cycles"], "issue_span_cycles": row["issue_span_cycles"],
                "ipc": row["aggregate_ipc"],
                "execution_unit_blocked_op_cycles": row["stall_counters"]["execution_unit_blocked_op_cycles"],
                "dependency_blocked_op_cycles": row["stall_counters"]["dependency_blocked_op_cycles"],
            }
        rows[str(fma_latency)] = {
            "fma_latency_cycles": int(fma_latency),
            "fp64_lanes_per_core": int(fp_count),
            "dedicated_fma_units_per_core": int(fma_count),
            "total_cycles": run["total_cycles"], "total_ops": run["total_ops"],
            "kernels": kernels,
        }
    if any(not row["ops_preserved"] for variant in rows.values()
           for row in variant["kernels"].values()):
        raise AssertionError("FMA latency sweep changed logical operation count")
    return {
        "experiment": "NEXSUS dedicated FMA result-latency sensitivity with fixed FP6/FMA4 topology",
        "cores": 8, "fp64_lanes_per_core": int(fp_count),
        "dedicated_fma_units_per_core": int(fma_count),
        "latencies_cycles": [int(x) for x in latencies],
        "same_logical_workload": expected_ops, "results": rows,
        "assumptions": (
            "FMA uses its own dedicated execution slots and retains one-op-per-cycle "
            "initiation per unit; only result latency changes. FP64 uses a separate pool. "
            "Global issue width and FA bank constraints remain separate. Simulator estimates."
        ),
    }


def run_data_mshr_sweep(profile_dict: dict, capacities=(1, 2, 4, 8, 16, 32, 64, 128),
                        ops_per_core=128) -> dict:
    """Sweep per-core Data RAM MSHRs on cold-load and mixed compute/load traces."""
    if ops_per_core < 1:
        raise ValueError("ops_per_core must be positive")
    profile = profile_from_dict(profile_dict)

    cold_shards = partition_dependency_components([
        Op(i, "LOAD", address=0x10000000 + i * profile.line_bytes,
           width=8, label="Data RAM MSHR cold miss")
        for i in range(ops_per_core * 8)
    ], 8)

    # One independent cold LOAD followed by three independent INT operations.
    # This exposes memory-level parallelism without making every instruction a LOAD.
    mixed_ops_per_core = ops_per_core * 4
    mixed_shards = []
    for core_id in range(8):
        shard = []
        for seq in range(mixed_ops_per_core):
            if seq % 4 == 0:
                shard.append(Op(
                    seq, "LOAD",
                    address=(0x50000000 + core_id * 0x1000000
                             + (seq // 4) * profile.line_bytes),
                    width=8, label="mixed MSHR cold load",
                ))
            else:
                shard.append(Op(seq, "INT", label="independent mixed compute"))
        mixed_shards.append(shard)

    def run_capacity(shards, expected_ops, expected_requests, capacity, workload_name):
        run = simulate_multicore_streams(
            shards, profile, int(profile_dict.get("dram_bytes_per_cycle", 32)),
            {"task_workspace": False, "code_slots": False,
             "data_mshr_entries": int(capacity)},
        )
        total_ops = sum(core["retired"] for core in run["cores"])
        request_count = len(run["controller"]["request_events"])
        max_outstanding = run["data_mshr"]["max_outstanding_per_core"]
        if total_ops != expected_ops or request_count != expected_requests:
            raise AssertionError(
                f"{workload_name} MSHR sweep lost work or requests: "
                f"retired={total_ops}/{expected_ops}, requests={request_count}/{expected_requests}"
            )
        if any(value > int(capacity) for value in max_outstanding):
            raise AssertionError("per-core MSHR occupancy exceeded configured capacity")
        return {
            "capacity_per_core": int(capacity),
            "cycles": run["cycles"],
            "ops_retired": total_ops,
            "data_ram_requests": request_count,
            "max_outstanding_per_core": max_outstanding,
            "total_full_events": run["data_mshr"]["total_full_events"],
            "total_blocked_request_attempts": run["data_mshr"]["total_blocked_request_attempts"],
            "total_full_cycles": run["data_mshr"]["total_full_cycles"],
            "full_cycles_per_core": run["data_mshr"]["full_cycles_per_core"],
            "app_ram_controller": run["app_controller"],
        }

    cold_rows = {}
    mixed_rows = {}
    for capacity in capacities:
        if int(capacity) < 1:
            raise ValueError("MSHR capacity must be at least one")
        cold_rows[str(capacity)] = run_capacity(
            cold_shards, ops_per_core * 8, ops_per_core * 8,
            capacity, "cold-load",
        )
        mixed_rows[str(capacity)] = run_capacity(
            mixed_shards, mixed_ops_per_core * 8, (mixed_ops_per_core // 4) * 8,
            capacity, "mixed compute/load",
        )

    return {
        "experiment": "NEXSUS per-core Data RAM MSHR capacity sweep",
        "cores": 8,
        "ops_per_core": ops_per_core,
        "same_cold_load_workload": True,
        "mixed_workload": {
            "ops_per_core": mixed_ops_per_core,
            "load_ops_per_core": mixed_ops_per_core // 4,
            "compute_ops_per_core": mixed_ops_per_core - mixed_ops_per_core // 4,
            "pattern": "1 independent cold LOAD followed by 3 independent INT operations",
        },
        "app_ram_and_data_ram_controllers_independent": True,
        "counter_definitions": {
            "total_blocked_request_attempts": "A request remains blocked for one cycle and is counted again if retried next cycle.",
            "total_full_cycles": "Per-core cycles in which at least one request was blocked by a full MSHR pool; multiple blocked requests on one core in one cycle count once."
        },
        "results": cold_rows,
        "mixed_results": mixed_rows,
        "assumptions": (
            "Each MSHR entry tracks one outstanding Data RAM demand miss per core "
            "until its fill completes. MSHR capacity is per-core, not shared; the "
            "Data RAM bank/bus controller remains shared. App RAM instruction fetch "
            "uses its own independent controller. Results are simulator estimates."
        ),
    }


def run_branch_predictor_sweep(workloads: Dict[str, List[Op]], profile_dict: dict) -> dict:
    """Compare NEXSUS predictor-off and compact-predictor assumptions on identical traces."""
    target = {name: workloads[name] for name in ("scalar_control", "pointer_graph", "branch_stress")}
    runs = {}
    for mode in ("none", "small_2bit"):
        profile = dict(profile_dict)
        profile["branch_predictor"] = mode
        runs[mode] = simulate_cpu(target, profile, profile.get("core_count", 8),
                                  {"task_workspace": True, "code_slots": True, "p0_capacity_kb": 16,
                                   "p0_refill_latency": 48, "spm0_kb": 4,
                                   "spm0_bank_kb": 2})
    rows = {}
    for name in target:
        off = runs["none"]["kernels"][name]
        compact = runs["small_2bit"]["kernels"][name]
        rows[name] = {
            "ops_preserved": off["ops"] == compact["ops"],
            "ops": off["ops"],
            "cycles_predictor_off": off["cycles"],
            "cycles_compact_predictor": compact["cycles"],
            "mispredicts_predictor_off": off["branch_mispredicts"],
            "mispredicts_compact_predictor": compact["branch_mispredicts"],
            "cycles_saved": off["cycles"] - compact["cycles"],
        }
    return {"experiment": "NEXSUS compact branch predictor ablation",
            "cores": profile_dict.get("core_count", 8), "kernels": rows,
            "assumptions": "Deterministic workload-class misprediction rates; not a cycle-accurate 2-bit predictor or vendor predictor model."}


def run_nexus_ablation(workloads: Dict[str, List[Op]], profile_dict: dict) -> dict:
    """Run the four controlled NEXSUS TW/CS combinations on identical work."""
    variants = {
        "N-FULL": {"task_workspace": True, "code_slots": True},
        "N-NO-TW": {"task_workspace": False, "code_slots": True},
        "N-NO-CS": {"task_workspace": True, "code_slots": False},
        "N-BASE": {"task_workspace": False, "code_slots": False},
    }
    runs = {
        name: simulate_cpu(workloads, profile_dict, max(8, profile_dict.get("core_count", 8)), flags)
        for name, flags in variants.items()
    }
    comparison = {}
    for kernel in workloads:
        full = runs["N-FULL"]["kernels"][kernel]
        no_spm = runs["N-NO-TW"]["kernels"][kernel]
        no_p0 = runs["N-NO-CS"]["kernels"][kernel]
        base = runs["N-BASE"]["kernels"][kernel]
        spm_gain = no_spm["cycles"] - full["cycles"]
        p0_gain = no_p0["cycles"] - full["cycles"]
        combined_gain = base["cycles"] - full["cycles"]
        comparison[kernel] = {
            "ops_preserved": all(runs[n]["kernels"][kernel]["ops"] == full["ops"] for n in variants),
            "ops": full["ops"],
            "cycles": {n: runs[n]["kernels"][kernel]["cycles"] for n in variants},
            "tw_cycles_saved_with_cs_on": spm_gain,
            "cs_cycles_saved_with_tw_on": p0_gain,
            "combined_cycles_saved": combined_gain,
            "interaction_cycles": combined_gain - (spm_gain + p0_gain),
            "tw_percent_vs_no_tw": round(100 * spm_gain / max(1, no_spm["cycles"]), 3),
            "cs_percent_vs_no_cs": round(100 * p0_gain / max(1, no_p0["cycles"]), 3),
            "combined_percent_vs_base": round(100 * combined_gain / max(1, base["cycles"]), 3),
        }
    return {
        "experiment": "NEXSUS TW/CS four-way ablation",
        "clock_ghz": runs["N-FULL"]["clock_ghz"],
        "cores": runs["N-FULL"]["cores_configured"],
        "variants": {name: {"features": flags, "total_cycles": runs[name]["total_cycles"],
                            "total_ops": runs[name]["total_ops"]}
                     for name, flags in variants.items()},
        "kernels": comparison,
        "full_runs": runs,
        "assumptions": {
            "p0_enabled": "CS0-CS7: 8 x 2 KiB code pool; EB: 4 KiB as two 2 KiB ping-pong banks; 2 KiB refill modeled at 48 cycles (32 payload + 16 source/control overhead assumption)",
            "p0_disabled": "32 KiB conventional instruction cache; 64-byte line; 32-cycle provisional refill",
            "spm2_enabled": "8 KiB task workspace; 2-cycle provisional access; one modeled port per core",
            "spm2_disabled": "Tagged TW accesses use normal cache/Data RAM path",
            "scope": "TW task workspace and CS-to-EB instruction feed modeled; OW, CP0-CP3 and XW remain partially abstracted",
        },
    }


def run_p0_capacity_sweep(workloads, profile_dict, capacities_kb=(4, 8, 16, 32, 64),
                            refill_latency=48, pool_miss_latency=120):
    """Single-core 64-KiB sequential code stream; vary only CS pool capacity."""
    target = {"cs_starvation": workloads["cs_starvation"]}
    last_page = (len(target["cs_starvation"]) * 8 - 1) // 2048
    page_descriptors = {last_page: {"valid_bytes": 2048, "stream_end": True}}
    rows = {}
    for capacity_kb in capacities_kb:
        run = simulate_cpu(
            target, profile_dict, 1,
            {"task_workspace": True, "code_slots": True, "p0_capacity_kb": capacity_kb,
             "p0_refill_latency": refill_latency, "px_pool_miss_latency": pool_miss_latency,
             "px_page_descriptors": page_descriptors},
        )
        rows[str(capacity_kb)] = {
            "capacity_kb": capacity_kb,
            "refill_latency_cycles": refill_latency,
            "pool_miss_latency_cycles": pool_miss_latency,
            "total_cycles": run["total_cycles"],
            "total_ops": run["total_ops"],
            "kernels": {name: {"cycles": row["cycles"], "ops": row["ops"],
                               "code_slots": row["codeflow_counters"]}
                        for name, row in run["kernels"].items()},
        }
    return {
        "experiment": "NEXSUS CS pool capacity sensitivity sweep",
        "profile": profile_dict["name"], "cores": 1,
        "same_workload_operation_count": next(iter(rows.values()))["total_ops"],
        "assumptions": "A 64-KiB sequential code stream; first pool pages staged at dispatch; later PX-pool misses pay the configured App-RAM source latency. Only pool capacity changes.",
        "results": rows,
    }


def run_fetch_latency_sweep(workloads, conventional_latencies=(8, 16, 24, 32),
                            p0_latencies=(32, 34, 48, 64, 96), p0_capacity_kb=64):
    """Compare reference I-cache refill assumptions with NEXSUS P0 refill assumptions."""
    target = {"cs_starvation": workloads["cs_starvation"]}
    last_page = (len(target["cs_starvation"]) * 8 - 1) // 2048
    page_descriptors = {last_page: {"valid_bytes": 2048, "stream_end": True}}
    rows = {"amd_9950x3d2": {}, "intel_xeon_698x": {}, "apple_m6": {},
            "nexus_conventional": {}, "nexus_p0": {}}
    for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6"):
        for latency in conventional_latencies:
            run = simulate_cpu(target, PROFILES[key], 1,
                               {"conventional_refill_latency": latency})
            kernel = run["kernels"]["cs_starvation"]
            rows[key][str(latency)] = {
                "refill_latency_cycles": latency, "cycles": kernel["cycles"],
                "ops": kernel["ops"], "fetch": kernel["codeflow_counters"],
            }
    for latency in conventional_latencies:
        run = simulate_cpu(
            target, PROFILES["nexus_balanced_128"], 1,
            {"task_workspace": True, "code_slots": False, "conventional_refill_latency": latency,
             "px_page_descriptors": page_descriptors},
        )
        kernel = run["kernels"]["cs_starvation"]
        rows["nexus_conventional"][str(latency)] = {
            "refill_latency_cycles": latency, "cycles": kernel["cycles"],
            "ops": kernel["ops"], "fetch": kernel["codeflow_counters"],
        }
    for latency in p0_latencies:
        run = simulate_cpu(
            target, PROFILES["nexus_balanced_128"], 1,
            {"task_workspace": True, "code_slots": True, "p0_capacity_kb": p0_capacity_kb,
             "p0_refill_latency": latency, "px_pool_miss_latency": 120,
             "px_page_descriptors": page_descriptors},
        )
        kernel = run["kernels"]["cs_starvation"]
        rows["nexus_p0"][str(latency)] = {
            "refill_latency_cycles": latency, "capacity_kb": p0_capacity_kb,
            "cycles": kernel["cycles"], "ops": kernel["ops"],
            "fetch": kernel["codeflow_counters"],
        }
    counts = {row["ops"] for group in rows.values() for row in group.values()}
    if len(counts) != 1:
        raise AssertionError(f"fetch sweep changed operation count: {counts}")
    return {
        "experiment": "Conventional instruction-cache vs NEXSUS P0 refill sensitivity",
        "cores": 1, "kernel": "cs_starvation",
        "operations_per_run": next(iter(counts)),
        "conventional_capacity_kb": 32,
        "p0_capacity_kb": p0_capacity_kb,
        "assumptions": "Single-core 64-KiB sequential code stream; conventional I-cache uses bounded multi-line prefetch; CS pool is set to 64 KiB so the whole stream is resident and source misses do not confound CS-to-EB transfer latency; only transfer latency varies within each path.",
        "results": rows,
    }


def run_vector_matrix_isolation_sweep(workloads: Dict[str, List[Op]]) -> dict:
    """Compare normal instruction delivery with a fetch-bypassed backend upper bound."""
    names = ("vector_throughput", "vec_add", "vec_sub", "vec_mul",
             "vec_fma", "vec_permute", "vec_reduce",
             "vec_add_dependency_chain", "vec_sub_dependency_chain",
             "vec_mul_dependency_chain", "vec_fma_dependency_chain",
             "vec_permute_dependency_chain", "vec_reduce_dependency_chain",
             "me512_independent_throughput", "me512_dependency_chain",
             "me512_matrix", "vec_me512_memory_overlap")
    target = {name: workloads[name] for name in names if name in workloads}
    profiles = ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128")
    rows = {}
    for key in profiles:
        profile = PROFILES[key]
        core_count = 8
        if key == "nexus_balanced_128":
            normal_features = {"task_workspace": True, "code_slots": True,
                               "codeflow": True, "p0_capacity_kb": 16,
                               "p0_refill_latency": 48}
        else:
            normal_features = None
        normal = simulate_cpu(target, profile, core_count, normal_features)
        isolated = simulate_cpu(target, profile, core_count,
                                {"execution_only": True})
        mixed = target.get("vec_me512_memory_overlap", [])
        warm_addresses = sorted({op.address for op in mixed
                                 if op.kind in ("LOAD", "STORE", "ATOM")})
        cache_resident = simulate_cpu(
            {"vec_me512_memory_overlap": mixed}, profile, core_count,
            {"execution_only": True,
             "cache_prefill_addresses": warm_addresses,
             "cache_prefill_level": "L4" if key == "nexus_balanced_128" else "L3"},
        ) if mixed else None
        rows[key] = {
            "normal": normal,
            "execution_only": isolated,
            "cache_resident": cache_resident,
        }
    return {
        "experiment": "VEC and ME512 instruction-fetch isolation with cold and preloaded-cache paths",
        "cores_per_profile": 8,
        "same_logical_workloads": list(target),
        "execution_only_definition": "Bypass instruction-fetch readiness only; retain per-core dispatch/issue, execution units, dependencies, Data RAM/cache timing and retirement.",
        "cache_resident_definition": "Before timed simulation, preload each working-set line once per distinct cache group at its selected home level. Default L1 is for one-core work; choose L2/L3/L4 for 2/4/8+ collaborating cores. Prefill is untimed setup; a group sees its shared home level without artificially duplicating the line into every private L1.",
        "results": rows,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--nexus-cores", type=int, default=8)
    ap.add_argument("--normalized-8core", action="store_true", help="run all four architectures with exactly eight active cores")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ablation", action="store_true", help="run four-way NEXSUS Task Workspace / Code Slots ablation")
    ap.add_argument("--branch-sweep", action="store_true", help="compare NEXSUS predictor-off and compact predictor")
    ap.add_argument("--cs-capacity-kb", "--p0-capacity-kb", dest="p0_capacity_kb", type=int, default=16, help="CS0-CS7 code-slot capacity in KiB; EB is 4 KiB (2x2 KiB)")
    ap.add_argument("--p0-refill-cycles", type=int, default=48, help="provisional 2-KiB CS-to-EB refill latency")
    ap.add_argument("--cs-sweep", "--p0-sweep", dest="p0_sweep", action="store_true", help="run 4/8/16/32 KiB CS code-slot capacity sweep (legacy flag: --p0-sweep)")
    ap.add_argument("--fetch-sweep", action="store_true", help="compare conventional I-cache and P0 refill latency sensitivity")
    ap.add_argument("--execution-sweep", action="store_true", help="compare baseline and mixed-width NEXSUS INT/FP resources")
    ap.add_argument("--resource-sweep", action="store_true", help="sweep per-core INT/FP unit counts with fixed workloads")
    ap.add_argument("--fma-sweep", action="store_true", help="sweep independent dedicated FMA units alongside FP64 lanes")
    ap.add_argument("--fma-latency-sweep", action="store_true", help="sweep FMA result latency with FP6/FMA4 held fixed")
    ap.add_argument("--mshr-sweep", action="store_true", help="sweep per-core Data RAM MSHR capacities 1/2/4/8/16/32")
    ap.add_argument("--vec-me512-isolation", action="store_true", help="compare normal VEC/ME512 workloads with instruction-fetch-bypassed backend isolation")
    ap.add_argument("--l4-l1-sweep", action="store_true", help="sweep direct shared L4-to-private-L1 transfer parameters for one 8-core block")
    ap.add_argument("--l4-l1-distribution-sweep", action="store_true", help="compare L4-to-L1 unicast and multicast fanout distribution models")
    args = ap.parse_args()
    workloads = build_composite_workload(args.scale)
    if args.l4_l1_sweep:
        result = run_l4_l1_transfer_sweep()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("8-CORE DIRECT L4 -> L1 TRANSFER DESIGN-SPACE SWEEP")
            print(f"Rows: {result['row_count']} (no hardware operating point selected)")
            for row in result["results"]:
                print(
                    f"WS={row['working_set_kib']:>3} KiB targets={row['target_core_count']} "
                    f"chunk={row['chunk_bytes']:>4}B L4={row['l4_read_bytes_per_cycle']:>3} "
                    f"L1={row['l1_ingress_bytes_per_cycle']:>3} "
                    f"cycles={row['cycles']:>7} throughput={row['effective_bytes_per_cycle']:>9.2f} B/cycle"
                )
        return
    if args.l4_l1_distribution_sweep:
        result = run_l4_l1_distribution_comparison_sweep()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("8-CORE L4 -> L1 UNICAST / MULTICAST DISTRIBUTION COMPARISON")
            print(f"Rows: {result['row_count']} (no hardware operating point selected)")
            for target_count in (1, 2, 4, 8):
                candidates = [row for row in result["results"] if row["target_core_count"] == target_count]
                best = min(candidates, key=lambda row: row["multicast_cycles"] / max(1, row["unicast_cycles"]))
                print(f"targets={target_count}: best multicast/unicast cycle ratio="
                      f"{best['multicast_cycles'] / max(1, best['unicast_cycles']):.3f}, "
                      f"source saved={best['l4_source_bytes_saved']} B, "
                      f"fanout={best['fanout_bytes_per_cycle']} B/cycle")
        return
    if args.vec_me512_isolation:
        result = run_vector_matrix_isolation_sweep(workloads)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("VEC / ME512 INSTRUCTION-FETCH ISOLATION")
            for profile, pair in result["results"].items():
                for kernel in result["same_logical_workloads"]:
                    normal = pair["normal"]["kernels"][kernel]
                    isolated = pair["execution_only"]["kernels"][kernel]
                    print(f"{profile:20} {kernel:20} normal={normal['cycles']:>5} backend={isolated['cycles']:>5} "
                          f"fetch_wait={normal['codeflow_counters']['wait_cycles']:>6}")
        return
    if args.mshr_sweep:
        result = run_data_mshr_sweep(PROFILES["nexus_balanced_128"])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS DATA RAM MSHR CAPACITY SWEEP")
            for name, row in result["results"].items():
                print(f"{name} entries/core: cycles={row['cycles']} "
                      f"max={max(row['max_outstanding_per_core'])} "
                      f"full-events={row['total_full_events']}")
        return
    if args.fma_latency_sweep:
        result = run_fma_latency_sweep(workloads, PROFILES["nexus_balanced_128"])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS FMA RESULT-LATENCY SWEEP")
            for name, row in result["results"].items():
                chain = row["kernels"]["fma_dependency_chain"]
                throughput = row["kernels"]["fma_throughput"]
                print(f"{name} cycles: chain={chain['cycles']} independent={throughput['cycles']}")
        return
    if args.fma_sweep:
        result = run_fma_resource_sweep(
            workloads, PROFILES["nexus_balanced_128"],
            fp_counts=(6, 8), fma_counts=(2, 4))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS FP64/FMA RESOURCE SWEEP")
            for name, row in result["results"].items():
                fp = row["kernels"]["fp_throughput"]
                fma = row["kernels"]["fma_throughput"]
                print(f"{name}: FP64={fp['cycles']} FMA={fma['cycles']} stalls={fp['execution_unit_blocked_op_cycles']}/{fma['execution_unit_blocked_op_cycles']}")
        return
    if args.resource_sweep:
        result = run_execution_resource_count_sweep(workloads, PROFILES["nexus_balanced_128"])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS INT/FP RESOURCE COUNT SWEEP")
            for name, row in result["results"].items():
                print(f'{name}: cycles={row["total_cycles"]} ops={row["total_ops"]}')
        return
    if args.execution_sweep:
        result = run_execution_topology_sweep(workloads, PROFILES["nexus_balanced_128"])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS MIXED-WIDTH EXECUTION TOPOLOGY SWEEP")
            for name, row in result["kernels"].items():
                print(f'{name}: baseline={row["baseline_cycles"]} proposed={row["proposed_cycles"]} '
                      f'saved={row["cycles_saved"]} ({row["improvement_percent"]}%)')
        return
    if args.normalized_8core:
        normalized = {}
        for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6", "nexus_balanced_128"):
            normalized[key] = simulate_cpu(workloads, PROFILES[key], 8)
        if args.json:
            print(json.dumps(normalized, indent=2))
        else:
            print("NORMALIZED 8-CORE ARCHITECTURE COMPARISON")
            for key, result in normalized.items():
                print(f'{key}: cycles={result["total_cycles"]} ops={result["total_ops"]} IPC={result["aggregate_ipc"]}')
        return
    if args.fetch_sweep:
        result = run_fetch_latency_sweep(workloads)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("INSTRUCTION FETCH REFILL SENSITIVITY — PROVISIONAL MODEL")
            for profile, rows in result["results"].items():
                for row in rows.values():
                    print(f'{profile:20} refill={row["refill_latency_cycles"]:>2} cycles={row["cycles"]} ops={row["ops"]}')
        return
    if args.p0_sweep:
        result = run_p0_capacity_sweep(workloads, PROFILES["nexus_balanced_128"],
                                        refill_latency=args.p0_refill_cycles)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS CS CODE-SLOT CAPACITY SENSITIVITY — PROVISIONAL MODEL")
            for row in result["results"].values():
                print(f'{row["capacity_kb"]:>2} KiB: cycles={row["total_cycles"]} ops={row["total_ops"]}')
        return
    if args.branch_sweep:
        result = run_branch_predictor_sweep(workloads, PROFILES["nexus_balanced_128"])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS BRANCH PREDICTOR ABLATION")
            for name, row in result["kernels"].items():
                print(f'{name}: off={row["cycles_predictor_off"]} compact={row["cycles_compact_predictor"]} saved={row["cycles_saved"]}')
        return
    if args.ablation:
        result = run_nexus_ablation(workloads, PROFILES["nexus_balanced_128"])
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("NEXSUS TW/CS FOUR-WAY ABLATION — PROVISIONAL MODEL")
            for name, row in result["variants"].items():
                print("{} cycles={} ops={}".format(name, row["total_cycles"], row["total_ops"]))
            print("PER-KERNEL EFFECTS")
            for kernel, row in result["kernels"].items():
                print("{} full={} no-SPM={} no-P0={} base={} interaction={}".format(
                    kernel, row["cycles"]["N-FULL"], row["cycles"]["N-NO-TW"],
                    row["cycles"]["N-NO-CS"], row["cycles"]["N-BASE"], row["interaction_cycles"]))
        return
    profiles = {}
    for key in ("amd_9950x3d2", "intel_xeon_698x", "apple_m6"):
        profiles[key] = simulate_cpu(workloads, PROFILES[key])
    for key in ("nexus_balanced_128",):
        profiles[key] = simulate_cpu(
            workloads, PROFILES[key], max(8, args.nexus_cores),
            {"task_workspace": True, "code_slots": True, "codeflow": True, "p0_capacity_kb": args.p0_capacity_kb,
             "p0_refill_latency": args.p0_refill_cycles},
        )
    if args.json:
        print(json.dumps(profiles, indent=2))
        return
    print("NEXSUS CPU COMPOSITE WORKLOAD — NATIVE PROFILE MODEL v0.3.2-dev")
    print("Native modeled cores: AMD 16, Intel Xeon 698X 86, Apple M6 12, NEXSUS 8; one hardware thread/core. Clock and memory parameters are explicit model assumptions.")
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
    print("*Simulated architecture profiles, not silicon measurements. Apple M6 heterogeneous cores are represented by a weighted homogeneous approximation; vendor-private microarchitecture details are assumptions. NEXSUS CS pool feeds EB-A/B (2x2 KiB).")

if __name__ == "__main__":
    main()
