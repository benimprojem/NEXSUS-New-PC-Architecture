# NEXSUS CPU — Initial SPM/P0 Ablation Results

**Document ID:** NEXSUS-CPU-SPM-P0-ABLATION-RESULTS-001  
**Status:** Initial behavioral-model run; not calibrated hardware performance  
**Simulator commit:** `a3f7c7efa82f1108a16a49e5b724b15bfd79a9fd`  
**CI run:** [43489152343](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43489152343)

## 1. Experiment conditions

- Selected NEXSUS profile only: 128-entry modeled in-flight window.
- Eight active cores, one modeled hardware thread per core.
- 3.0 GHz normalized reference clock.
- Same workload graph and operation count in all four variants.
- Same cache groups, DRAM controller and 32 B/cycle aggregate DRAM assumption.
- N-FULL: SPM2 and P0 enabled.
- N-NO-SPM: SPM disabled, P0 enabled.
- N-NO-P0: SPM enabled, conventional instruction-cache path.
- N-BASE: both disabled.
- Workload scale 1. Reported total cycles are the sum of per-kernel elapsed cycles; inspect per-kernel values rather than treating the sum as one application runtime.

## 2. Aggregate results

| Variant | Total kernel cycles | Operations |
|---|---:|---:|
| N-FULL | 35,490 | 44,654 |
| N-NO-SPM | 57,954 | 44,654 |
| N-NO-P0 | 43,574 | 44,654 |
| N-BASE | 65,959 | 44,654 |

All four variants retired the same 44,654 operations.

| Effect | Cycles saved | Relative reduction vs disabled variant |
|---|---:|---:|
| SPM contribution with P0 on | 22,464 | 38.762% |
| P0 contribution with SPM on | 8,084 | 18.552% |
| Combined SPM+P0 vs N-BASE | 30,469 | 46.194% |
| Interaction vs sum of isolated gains | -79 | Slightly sub-additive |

Interaction is calculated as combined cycles saved minus the sum of the two isolated savings. The -79-cycle result means the combined gain is 79 cycles smaller than the arithmetic sum of the isolated gains in this run; it is not evidence of a general negative interaction.

## 3. Per-kernel results

| Kernel | N-FULL | N-NO-SPM | N-NO-P0 | N-BASE |
|---|---:|---:|---:|---:|
| scalar_control | 302 | 302 | 1,067 | 1,067 |
| pointer_graph | 8,649 | 8,649 | 8,673 | 8,673 |
| numeric_tile | 351 | 351 | 375 | 375 |
| streaming | 896 | 896 | 920 | 920 |
| parallel_tasks | 289 | 289 | 353 | 353 |
| integer_throughput | 74 | 74 | 266 | 266 |
| fp_throughput | 76 | 76 | 268 | 268 |
| vector_throughput | 41 | 41 | 137 | 137 |
| branch_stress | 52 | 52 | 136 | 136 |
| spm_hot_workset | 2,057 | 9,545 | 2,144 | 9,569 |
| spm_capacity_sweep | 17,033 | 32,009 | 17,073 | 32,033 |
| p0_sequential | 290 | 290 | 1,058 | 1,058 |
| p0_branch | 416 | 416 | 1,060 | 1,060 |
| p0_working_set | 354 | 354 | 1,122 | 1,122 |
| p0_starvation | 4,610 | 4,610 | 8,962 | 8,962 |

## 4. What this run tells us

1. **SPM2 is most visible on dependent memory chains.** The 4 KiB hot working set falls from 9,545 to 2,057 cycles with SPM2 enabled. The 16 KiB capacity sweep falls from 32,009 to 17,033 cycles because the in-range portion can use SPM2 while overflow follows the normal Data RAM/cache path.
2. **P0 improves command supply in this model.** Sequential, branch, repeated-working-set and starvation kernels all show lower cycle counts with P0 enabled. The 16 KiB command-loop test fits the two-buffer P0/P1 total while fitting the 32 KiB conventional I-cache, so capacity pressure is represented rather than assuming P0 always wins.
3. **The features affect different bottlenecks.** P0 has no visible effect on the SPM-only on/off comparison; SPM2 has no visible effect on the P0-only command kernels. The combined result is therefore close to the sum of isolated gains.
4. **Pointer chasing remains mostly latency-bound.** P0 changes only a small part of the total because the dependent Data RAM/DRAM chain dominates.

## 5. Assumptions and limitations

These are behavioral-model results, not measured silicon performance:

- P0/P1: 16 KiB total, two 8-KiB ping-pong buffers (1,024 64-bit command words each), one 8-KiB block refill engine/core; 128-cycle transfer assumption at 512-bit/cycle.
- P0-off: 32 KiB conventional instruction cache, 64-byte line, assumed 32-cycle refill.
- SPM2: 8 KiB addressable workspace, assumed 2-cycle access, one modeled port per core.
- Per-core command streams are rebased after dependency partitioning. The P0 starvation trace performs two passes over a 16 KiB command working set.
- Detailed branch-target redirect behavior, command refill queue arbitration, App RAM physical bank contention, SPM2 multi-bank behavior, SPM0, SPM1, SPM3–SPM7, task-context residency and exception entry are not yet modeled.
- No power or energy estimate is made.
- AMD/Intel front-end models do not yet include equivalent detailed command-cache simulation. These four-way results answer the internal NEXSUS ablation question only; they are not a fair cross-vendor P0 comparison.

## 6. Next validation steps

1. Sweep P0 refill latency and capacity; do not rely on the single 8-cycle assumption.
2. Sweep SPM2 latency and port count (at minimum 1/2/3-cycle and 1/2/4-port scenarios).
3. Add App RAM command-refill arbitration and redirect/refill overlap.
4. Add SPM1 OS exchange and SPM3–SPM6 resident context behavior.
5. Add SPM7 exception-entry behavior and protected Data RAM fallback.
6. Compare model outputs with a lower-level timing model before making physical performance claims.
