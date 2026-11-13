#!/usr/bin/env python3
"""NEXSUS CPU comparison simulator — controlled 8-core model v0.2.

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
    dram_bytes_per_cycle: int = 32
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
    "nexus_candidate": {
        "name": "NEXSUS CPU / configurable candidate",
        "core_count": 8, "core_type": "uniform", "frontend": 4,
        "dispatch": 4, "issue": 5, "retire": 4, "rob": 64,
        "units": {"INT": 2, "FP": 2, "VEC": 1, "LOAD": 2, "STORE": 1, "BR": 1, "CTX": 1, "ATOM": 1},
        "latency": {"INT": 1, "FP": 3, "VEC": 2, "LOAD": 4, "STORE": 1, "BR": 1, "ATOM": 8, "CTX": 4},
        "l1_kb": 128, "l2_kb": 1024, "l3_kb": 8192, "l4_kb": 65536,
        "l1_lat": 2, "l2_lat": 8, "l3_lat": 24, "l4_lat": 64, "dram_lat": 120,
        "branch_penalty": 10, "frequency_ghz": 3.0,
        "bank_hash": "folded", "dram_bytes_per_cycle": 32
    }
}

def add_op(ops: List[Op], kind: str, deps=(), address=0, width=8, label=""):
    seq = len(ops)
    ops.append(Op(seq, kind, tuple(dict.fromkeys(deps)), address, width, label))
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

    return result

class LRU:
    def __init__(self, capacity_bytes: int, line_bytes: int):
        self.capacity = max(1, capacity_bytes // line_bytes)
        self.lines = OrderedDict()
    def touch(self, line: int) -> bool:
        hit = line in self.lines
        if hit:
            self.lines.move_to_end(line)
        else:
            self.lines[line] = None
            if len(self.lines) > self.capacity:
                self.lines.popitem(last=False)
        return hit

class CacheHierarchy:
    def __init__(self, p: CoreProfile):
        self.line = p.line_bytes
        self.l1 = LRU(p.l1_kb*1024, self.line)
        self.l2 = LRU(p.l2_kb*1024, self.line)
        self.l3 = LRU(p.l3_kb*1024, self.line)
        self.l4 = LRU(p.l4_kb*1024, self.line) if p.l4_kb else None
        self.p = p
    def access(self, address: int) -> Tuple[int, str]:
        line = address // self.line
        if self.l1.touch(line):
            return self.p.l1_lat, "L1"
        if self.l2.touch(line):
            self.l1.touch(line)
            return self.p.l2_lat, "L2"
        if self.l3.touch(line):
            self.l2.touch(line); self.l1.touch(line)
            return self.p.l3_lat, "L3"
        if self.l4 and self.l4.touch(line):
            self.l3.touch(line); self.l2.touch(line); self.l1.touch(line)
            return self.p.l4_lat, "L4"
        if self.l4:
            self.l4.touch(line)
        self.l3.touch(line); self.l2.touch(line); self.l1.touch(line)
        return self.p.dram_lat, "DRAM"

def profile_from_dict(d: dict) -> CoreProfile:
    return CoreProfile(**d)

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

        # Select ready operations oldest-first; dependencies may execute out of order.
        issued_this_cycle = 0
        for seq in list(rob):
            if issued_this_cycle >= p.issue:
                break
            if issued[seq]:
                continue
            op = ops[seq]
            if any(not done[x] for x in op.deps):
                continue
            kind = op.kind
            resource = "LOAD" if kind == "LOAD" else ("STORE" if kind == "STORE" else kind)
            slots = unit_busy.get(resource, [])
            slot = next((i for i,t in enumerate(slots) if t <= cycle), None)
            if slot is None:
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
        "cache_accesses": hits
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
                            op.address, op.width, op.label))
        if shard:
            shards.append(shard)
    return shards

def simulate_cpu(workloads: Dict[str,List[Op]], profile_dict: dict, core_count=None) -> dict:
    p = profile_from_dict(profile_dict)
    cores = core_count or p.core_count
    results = {}
    for name, ops in workloads.items():
        shards = partition_dependency_components(ops, cores)
        per_core = [simulate_stream(shard, p) for shard in shards]
        elapsed_cycles = max((x["cycles"] for x in per_core), default=0)
        total_ops = sum(x["ops"] for x in per_core)
        summed_cycles = sum(x["cycles"] for x in per_core)
        cache_totals = {k: sum(x["cache_accesses"][k] for x in per_core)
                        for k in ("L1", "L2", "L3", "L4", "DRAM")}
        results[name] = {
            "cycles": elapsed_cycles, "ops": total_ops,
            "aggregate_ipc": round(total_ops/max(1, elapsed_cycles), 3),
            "core_cycles_sum": summed_cycles,
            "active_cores": len(per_core),
            "per_core_cycles": [x["cycles"] for x in per_core],
            "max_rob_occupancy": max((x["max_rob_occupancy"] for x in per_core), default=0),
            "branch_mispredicts": sum(x["branch_mispredicts"] for x in per_core),
            "cache_accesses": cache_totals,
            "parallel_model": "dependency-component multicore; private caches; shared-memory contention not yet modeled"
        }
    total_cycles = sum(v["cycles"] for v in results.values())
    total_ops = sum(v["ops"] for v in results.values())
    return {"cpu": p.name, "cores_configured": cores, "clock_ghz": p.frequency_ghz,
            "cpu_ram_reference_clock_ghz": p.frequency_ghz,
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
    profiles["nexus_candidate"] = simulate_cpu(workloads, PROFILES["nexus_candidate"], max(8, args.nexus_cores))
    if args.json:
        print(json.dumps(profiles, indent=2))
        return
    print("NEXSUS CPU COMPOSITE WORKLOAD — CONTROLLED 8-CORE MODEL v0.2")
    print("All targets: 8 cores, 3.0 GHz CPU/reference-memory clock, same DRAM latency/bandwidth assumptions.")
    print("Parallelism: dependency components distributed across cores; shared inter-core memory contention remains a known limitation.")
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
    print("*Time uses configured reference clock, not measured sustained turbo.")

if __name__ == "__main__":
    main()
