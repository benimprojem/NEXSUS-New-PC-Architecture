#!/usr/bin/env python3
"""Combined cross-architecture workload + NEXSUS CodeFlow pipeline report.

The CPU execution model and CodeFlow front-end model are intentionally reported
as separate layers until a shared per-instruction fetch scheduler is implemented.
"""
import argparse
import json
import cpu_comparison_sim as cpu
import l0i_px_pipeline_sim as codeflow

def run(scale=1, pages=64, tasks=4):
    workloads=cpu.build_composite_workload(scale)
    arch={}
    for key in ("amd_9950x3d2","intel_xeon_698x","apple_m6","nexus_balanced_128"):
        arch[key]=cpu.simulate_cpu(workloads,cpu.PROFILES[key],
            8 if key=="nexus_balanced_128" else None,
            {"codeflow": True} if key=="nexus_balanced_128" else None)
    cf={}
    for beat in (1,2,4,8):
        cfg=codeflow.Config(app_beat_interval=beat)
        result=codeflow.Pipeline(cfg).run(codeflow.make_pages(pages,tasks))
        cf[str(beat)]={k:v for k,v in vars(result).items() if k!="timeline"}
    same_ops=len({v["total_ops"] for v in arch.values()})==1
    return {
      "model_notice":"Architectural simulation, not physical silicon measurements.",
      "execution_model":"same composite workload across AMD/Intel/ARM/NEXSUS profiles",
      "codeflow_model":"NEXSUS CPU cycles include dispatch gating on integrated AppRAM->C0->CS->EB page readiness; detailed queue/overlap pipeline sweep is supplementary and separately reported",
      "same_logical_ops_all_architectures":same_ops,
      "architecture_results":arch,
      "codeflow_beat_interval_sweep":cf,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scale",type=int,default=1)
    ap.add_argument("--pages",type=int,default=64)
    ap.add_argument("--tasks",type=int,default=4)
    ap.add_argument("--json",action="store_true")
    a=ap.parse_args()
    result=run(a.scale,a.pages,a.tasks)
    if not result["same_logical_ops_all_architectures"]:
        raise SystemExit("FAIL: architecture workloads did not preserve operation count")
    if len({r["pages_completed"] for r in result["codeflow_beat_interval_sweep"].values()})!=1:
        raise SystemExit("FAIL: CodeFlow page completion count differs across lane profiles")
    if a.json: print(json.dumps(result,indent=2))
    else:
        print("CROSS-ARCHITECTURE + CODEFLOW MODEL REPORT")
        for key,row in result["architecture_results"].items():
            print(f'{key}: cycles={row["total_cycles"]} ops={row["total_ops"]} IPC={row["aggregate_ipc"]:.3f}')
        print("CodeFlow AppRAM lane interval sweep:")
        for beat,row in result["codeflow_beat_interval_sweep"].items():
            print(f'  interval={beat}: cycles={row["cycles"]} pages={row["pages_completed"]} beats={row["app_beats"]}')
if __name__=="__main__": main()
