#!/usr/bin/env python3
"""Sensitivity sweep for configurable NEXSUS physical register sub-bank topology."""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cpu_comparison_sim", HERE / "cpu_comparison_sim.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load cpu_comparison_sim.py")
SIM = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SIM
SPEC.loader.exec_module(SIM)

CLASSES = ("RA", "FA", "DA", "MA")
BANK_COUNTS = (2, 4, 8, 16)
PORT_CONFIGS = ((1, 1), (2, 1), (2, 2), (4, 2))
PATTERNS = ("distributed", "concentrated")


def _scalar_index(seq, operand, bank_count, pattern):
    if pattern == "distributed":
        return (seq * 3 + operand) % 32
    lanes = max(1, 32 // bank_count)
    return (operand % bank_count) + bank_count * ((seq + operand) % lanes)


def _write_index(seq, bank_count, pattern):
    if pattern == "distributed":
        return (seq * 5 + 7) % 32
    lanes = max(1, 32 // bank_count)
    return bank_count * ((seq * 3) % lanes)


def _pair_entries(seq, pair_index, bank_count, pattern):
    if pattern == "distributed":
        start = 2 * ((seq + pair_index) % 16)
    else:
        start = 2 * (pair_index % max(1, bank_count // 2))
    return (start, start + 1)


def build_register_workload(bank_count, pattern, rounds=24):
    if bank_count not in BANK_COUNTS or pattern not in PATTERNS:
        raise ValueError("unsupported bank count or register-access pattern")
    ops = []
    for _ in range(rounds):
        for kind in ("INT", "FP", "FMA", "VEC", "ME512", "LOAD", "STORE"):
            seq = len(ops)
            if kind in ("INT", "FP", "FMA"):
                cls = "RA" if kind == "INT" else "FA"
                nread = 3 if kind == "FMA" else 2
                reads = tuple((cls, _scalar_index(seq, i, bank_count, pattern), 1)
                              for i in range(nread))
                writes = ((cls, _write_index(seq, bank_count, pattern), 1),)
                ops.append(SIM.Op(seq, kind, rac_reads=nread, rac_writes=1,
                                  rac_read_accesses=reads, rac_write_accesses=writes,
                                  label=f"subbank {pattern} {kind.lower()}"))
            elif kind in ("VEC", "ME512"):
                n_pairs = 1 if kind == "VEC" else 2
                reads = tuple(("MA", index, 4)
                              for pair in range(n_pairs)
                              for index in _pair_entries(seq, pair, bank_count, pattern))
                writes = tuple(("MA", index, 4)
                               for index in _pair_entries(seq + 1, 0, bank_count, pattern))
                ops.append(SIM.Op(seq, kind, exec_width_bits=512,
                                  rac_reads=4 * len(reads), rac_writes=4 * len(writes),
                                  rac_read_accesses=reads, rac_write_accesses=writes,
                                  label="MMUL" if kind == "ME512" else "subbank VEC512"))
            elif kind == "LOAD":
                dest = _write_index(seq, bank_count, pattern)
                ops.append(SIM.Op(seq, kind, address=0x1000, width=8,
                                  rac_reads=0, rac_writes=1, rac_read_accesses=(),
                                  rac_write_accesses=(("DA", dest, 1),),
                                  label="subbank DA load"))
            else:
                source = _scalar_index(seq, 0, bank_count, pattern)
                ops.append(SIM.Op(seq, kind, address=0x1000, width=8,
                                  rac_reads=1, rac_writes=0,
                                  rac_read_accesses=(("DA", source, 1),), rac_write_accesses=(),
                                  label="subbank DA store"))
    return ops


def run_sweep(rounds=24):
    if rounds < 1:
        raise ValueError("rounds must be >= 1")
    rows = []
    for pattern in PATTERNS:
        for banks in BANK_COUNTS:
            workload = build_register_workload(banks, pattern, rounds)
            for read_ports, write_ports in PORT_CONFIGS:
                p = SIM.profile_from_dict(SIM.PROFILES["nexus_balanced_128"])
                p.frontend = p.dispatch = p.issue = 16
                p.rac_physical_read_ports = p.rac_physical_write_ports = None
                p.rac_physical_bank_counts = {name: banks for name in CLASSES}
                p.rac_physical_read_ports_per_bank = {name: read_ports for name in CLASSES}
                p.rac_physical_write_ports_per_bank = {name: write_ports for name in CLASSES}
                row = {"pattern": pattern, "bank_count_per_class": banks,
                       "read_ports_per_bank": read_ports, "write_ports_per_bank": write_ports,
                       "logical_ops": len(workload), "status": None}
                try:
                    result = SIM.simulate_stream(workload, p)
                    row.update({
                        "cycles": result["cycles"], "retired_ops": result["retired_ops"],
                        "completed": result["completed"], "ipc": result["ipc"],
                        "issue_peak_ops_per_cycle": result["issue_peak_ops_per_cycle"],
                        "physical_read_port_stalls": result["stall_counters"]["rac_physical_read_port_blocked_op_cycles"],
                        "physical_write_port_stalls": result["stall_counters"]["rac_physical_write_port_blocked_op_cycles"],
                        "destination_conflict_stalls": result["stall_counters"]["rac_destination_conflict_op_cycles"],
                    })
                    row["status"] = "completed" if result["completed"] else "incomplete"
                except ValueError as exc:
                    row["status"] = "infeasible"
                    row["reason"] = str(exc)
                rows.append(row)
    return {
        "experiment": "NEXSUS physical register sub-bank topology sensitivity",
        "model_only": True, "architecture_defaults_selected": False,
        "logical_rac_budget_per_core": {"reads": 80, "writes": 64, "slot_bits": 64},
        "bank_counts_tested_per_register_class": list(BANK_COUNTS),
        "per_bank_port_configurations": [{"read_ports": r, "write_ports": w} for r,w in PORT_CONFIGS],
        "access_patterns": list(PATTERNS), "rounds": rounds,
        "operations_per_case": rounds * 7, "result_count": len(rows), "results": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=24)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = run_sweep(args.rounds)
    rendered = json.dumps(data, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.json or not args.output:
        print(rendered)


if __name__ == "__main__":
    main()
