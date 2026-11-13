# NEXSUS CPU — Controlled Cross-Architecture Comparison Results

**Document ID:** NEXSUS-CPU-CROSS-ARCHITECTURE-RESULTS-001  
**Status:** First corrected 8-core model run; provisional behavioral results  
**Simulator:** v0.2.4-dev  
**CI run:** [43492093622](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43492093622) — successful  
**Purpose:** Record the same-workload comparison of AMD Zen 5, Intel Lion Cove P-core, Intel Skymont E-core and the selected NEXSUS 128-window profile.

## 1. Experimental controls

- Exactly 8 modeled cores per target.
- One hardware thread per core; SMT disabled.
- 3.0 GHz normalized reference clock.
- Same deterministic workload graphs and operation counts for every target.
- 120-cycle DRAM latency and 32 bytes/reference-cycle chip-wide DRAM ceiling.
- Lockstep multicore scheduling and one shared DRAM bank/bus controller.
- AMD, Intel P-core, Intel E-core and NEXSUS are separate profiles; Intel P/E results are not averaged.
- Each kernel is measured separately; the suite total is the sum of those independent kernel runs, not one monolithic application execution.

All four targets retired **44,654 operations** in the scale-1 suite.

## 2. Corrected command-fetch fairness

The first comparison run exposed a modeling asymmetry: NEXSUS paid explicit P0 refill stalls, while reference CPUs initially had no instruction-fetch miss delay. That comparison was not fair and is not used as the corrected baseline.

The current run gives AMD and Intel a conventional instruction-cache model:
- 32 KiB capacity per core;
- 64-byte line;
- provisional 32-cycle refill;
- one outstanding refill per core.

NEXSUS uses:
- 8 KiB P0 capacity;
- 64-byte refill line;
- provisional 8-cycle refill;
- one outstanding refill per core.

This is a symmetric *modeled path*, not an exact reconstruction of the vendors' instruction caches. Real L1I sizes, predecode/uop caches, refill bandwidth, miss concurrency, branch-target delivery and frontend queues still need calibration. The 32-cycle conventional refill and 8-cycle P0 refill are influential assumptions and must be sensitivity-tested before drawing silicon-level conclusions.

## 3. Aggregate result

| Architecture | Total modeled cycles | Aggregate IPC |
|---|---:|---:|
| AMD Ryzen 9 9950X / Zen 5 | 66,376 | 0.673 |
| Intel Core Ultra 9 285K / Lion Cove P | 65,785 | 0.679 |
| Intel Core Ultra 9 285K / Skymont E | 65,986 | 0.677 |
| NEXSUS CPU / 128-window, SPM+P0 | 35,490 | 1.258 |

The NEXSUS full-feature result is 46.5% fewer modeled cycles than AMD, 46.1% fewer than Intel P and 46.2% fewer than Intel E in this run. These percentages are **model outputs under the assumptions above**, not measured performance claims.

A useful control is the NEXSUS four-way ablation baseline:
- N-BASE (SPM off, P0 off): 65,959 cycles.
- AMD: 66,376 cycles.
- Intel P: 65,785 cycles.
- Intel E: 65,986 cycles.

The N-BASE result is within approximately 0.6% of the three reference totals. In this model, most of the full NEXSUS gap is therefore associated with the added SPM/P0 mechanisms rather than a large assumed advantage in the base pipeline.

## 4. Per-kernel cycle results

Lower is better. Each target completed the same operation count for each kernel.

| Kernel | AMD Zen 5 | Intel P | Intel E | NEXSUS 128 |
|---|---:|---:|---:|---:|
| scalar_control | 1,103 | 1,073 | 1,074 | 302 |
| pointer_graph | 8,673 | 8,673 | 8,673 | 8,649 |
| numeric_tile | 375 | 375 | 377 | 351 |
| streaming | 920 | 920 | 920 | 896 |
| parallel_tasks | 317 | 317 | 318 | 289 |
| integer_throughput | 273 | 266 | 266 | 74 |
| fp_throughput | 275 | 268 | 271 | 76 |
| vector_throughput | 141 | 138 | 139 | 41 |
| branch_stress | 143 | 140 | 140 | 52 |
| spm_hot_workset | 9,569 | 9,569 | 9,569 | 2,057 |
| spm_capacity_sweep | 32,033 | 32,033 | 32,033 | 17,033 |
| p0_sequential | 1,089 | 1,058 | 1,058 | 290 |
| p0_branch | 1,095 | 1,064 | 1,064 | 416 |
| p0_working_set | 1,153 | 1,100 | 1,122 | 354 |
| p0_starvation | 9,217 | 8,791 | 8,962 | 4,610 |

## 5. What the model currently suggests

### 5.1 SPM2 is the largest isolated contributor in the current workload suite

The SPM2 hot-workset and capacity-sweep kernels show large reductions because NEXSUS routes explicitly tagged, in-range task-local accesses through its modeled local workspace. The reference profiles do not have an equivalent SPM2 facility; their corresponding operations use the normal cache/Data RAM path.

This is the architectural difference the experiment is intended to expose, but it also means the result depends strongly on SPM2's assumed 2-cycle access, capacity and port behavior. These parameters need a sensitivity sweep and eventual physical validation.

### 5.2 P0 reduces command-supply delay under the current assumptions

The P0-targeted kernels improve against the conventional 32 KiB / 32-cycle modeled fetch path. This is not yet proof that P0 is faster than real AMD/Intel instruction frontends. The assumed refill latencies differ by 4×, and real frontend structures are much richer than this simplified model.

### 5.3 Compute throughput remains a model-specific result

The independent integer, FP and vector kernels currently favor the NEXSUS profile substantially. These results depend on modeled execution-unit counts, issue widths, front-end gating and the generic operation mapping. They are not yet calibrated against vendor micro-op decomposition or the NEXSUS ISA's actual instruction sequences.

### 5.4 Pointer chasing remains nearly tied

The pointer graph is dominated by dependent memory latency. The four profiles finish within 24 modeled cycles of one another, suggesting that widening issue resources or P0 alone does not remove the serial dependency/DRAM bottleneck.

## 6. SPM/P0 ablation cross-check

The NEXSUS four-way experiment ran on the same 44,654 operations:

| Variant | SPM | P0 | Total cycles |
|---|---|---|---:|
| N-FULL | On | On | 35,490 |
| N-NO-SPM | Off | On | 57,954 |
| N-NO-P0 | On | Off | 43,574 |
| N-BASE | Off | Off | 65,959 |

- SPM contribution with P0 enabled: 22,464 cycles saved (38.762% vs N-NO-SPM).
- P0 contribution with SPM enabled: 8,084 cycles saved (18.552% vs N-NO-P0).
- Combined reduction vs N-BASE: 30,469 cycles (46.194%).
- All four variants preserved the operation count.

## 7. P0 capacity sensitivity

The same scale-1 workload was run at four P0 capacities while holding refill latency at 8 cycles and keeping all other settings unchanged.

| P0 capacity | Total cycles | p0_starvation cycles |
|---|---:|---:|
| 4 KiB | 35,490 | 4,610 |
| 8 KiB | 35,490 | 4,610 |
| 16 KiB | 33,698 | 2,818 |
| 32 KiB | 33,698 | 2,818 |

In this particular trace, moving from 8 KiB to 16 KiB saves 1,792 cycles (about 5.05%) across the suite. Increasing to 32 KiB gives no further modeled benefit. **16 KiB is therefore a useful next candidate to investigate**, not a frozen architectural decision. Area, power, physical refill routing and a broader command working-set distribution have not been modeled.

## 8. Limitations and next validation steps

The results are not RTL, gem5, vendor benchmark or silicon measurements. Remaining important gaps:

1. Sweep conventional I-cache refill latency and P0 refill latency rather than relying on one 32-cycle vs 8-cycle pair.
2. Sweep SPM2 latency (1/2/3 cycles), port count and bank conflicts.
3. Model branch-target redirects, refill queue arbitration and App RAM command-path contention.
4. Improve vendor-specific frontend and cache details, including MSHRs and cache-line coalescing.
5. Map generic operation classes to vendor x86 micro-ops and to actual NEXSUS ISA instruction sequences.
6. Add SPM1 OS exchange, SPM3–SPM6 context residency, SPM7 exception entry and SPM0 CPU workspace.
7. Calibrate memory latency, bandwidth and execution resources against measured hardware counters before treating any result as predictive.

The current run is useful as a controlled design-space experiment: it shows where the proposed SPM/P0 architecture may create leverage, and which assumptions dominate the result. It does not establish a real-world performance lead.
