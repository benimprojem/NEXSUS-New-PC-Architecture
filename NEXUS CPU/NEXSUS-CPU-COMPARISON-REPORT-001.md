# NEXSUS CPU Comparison Report 001

**Date:** 2026-11-14  
**Simulator revision:** `e947f2f5fceeb4e221aae3187b0c64ea11d73e98`  
**CI:** [Run 43602765784 — all checks passed](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43602765784)  
**Results artifact:** `nexus-cpu-comparison-results`

## 1. Executive summary

The normalized eight-core model gives NEXSUS Balanced 128 the lowest aggregate modeled cycle count and elapsed time among the four profiles. This is a positive architecture result, but it is not a claim that a physical NEXSUS processor is faster than shipping silicon. All four profiles are simulated approximations with explicit assumptions.

The strongest NEXSUS results are the Task Workspace hot-set and capacity workloads, branch stress, CS branch workload, and streaming. NEXSUS is not the fastest in scalar control, integer/floating-point/vector throughput, pointer graph, or the conventional sequential/working-set instruction-fetch workloads. Those losses are important optimization targets.

## 2. Normalized eight-core comparison

All four profiles run the same **20,846 logical operations** with exactly **8 configured active cores**.

| CPU profile | Modeled clock | Total cycles | Aggregate IPC | Modeled elapsed time |
|---|---:|---:|---:|---:|
| AMD Ryzen 9 9950X3D2 / Zen 5 | 4.3 GHz | 55,311 | 0.377 | 12.863 µs |
| Intel Xeon 698X / Redwood Cove+ | 2.0 GHz | 64,995 | 0.321 | 32.497 µs |
| Apple M6 / 12-core ARM SoC approximation | 3.0 GHz | 45,501 | 0.458 | 15.167 µs |
| **NEXSUS Balanced 128** | **3.0 GHz** | **31,359** | **0.665** | **10.453 µs** |

In this model, NEXSUS elapsed time is approximately **18.7% lower than AMD**, **67.8% lower than Intel**, and **31.1% lower than Apple**. Cycle count and elapsed time are both shown because the modeled clocks differ; cycle count alone is not a wall-clock comparison.

### Per-kernel cycle comparison

Each cell is the modeled cycle count for that kernel. Lower is better.

| Kernel | AMD | Intel | Apple | NEXSUS |
|---|---:|---:|---:|---:|
| scalar_control | **154** | **154** | **154** | 170 |
| pointer_graph | 8,673 | 10,833 | **7,233** | 8,689 |
| numeric_tile | 428 | 388 | **303** | 342 |
| streaming | 1,323 | 566 | 644 | **552** |
| parallel_tasks | 336 | 361 | **265** | 312 |
| integer_throughput | 49 | **44** | **44** | 81 |
| fp_throughput | **51** | 52 | **51** | 83 |
| vector_throughput | **51** | **51** | 56 | 66 |
| me512_matrix | 738 | 462 | **412** | 420 |
| atomic_contention | 250 | 214 | **175** | 200 |
| irq_exception_stress | 62 | 64 | **58** | 68 |
| branch_stress | 118 | 140 | 120 | **83** |
| tw_hot_workset | 9,697 | 11,425 | 8,289 | **2,097** |
| tw_capacity_sweep | 32,545 | 39,457 | 26,913 | **16,945** |
| cs_sequential | 97 | **87** | **87** | 177 |
| cs_branch | 289 | 289 | 289 | **208** |
| cs_working_set | 161 | **129** | **129** | 305 |
| cs_starvation | 289 | **279** | **279** | 561 |

## 3. What the comparison says

### NEXSUS strengths

- **Task Workspace hot set:** 2,097 cycles, versus 8,289 for the next-fastest reference profile (Apple).
- **Task Workspace capacity stress:** 16,945 cycles, versus 26,913 for Apple. The NEXSUS run still reports 256 TW overflows, so this is not a no-overflow result.
- **Branch stress:** 83 cycles, the best result among the four profiles.
- **CS branch workload:** 208 cycles, versus 289 for each reference profile.
- **Streaming:** 552 cycles, narrowly ahead of Intel at 566.

These results support the intended separation of task-local data workspace and the code-slot/EB execution path. The large TW gains should be treated as workload-specific until the model is calibrated against a real implementation.

### NEXSUS weaknesses

- Raw scalar, integer, floating-point, and vector throughput are behind the reference profiles.
- Pointer-graph and parallel-task workloads are not wins.
- The current CS path loses on sequential fetch, working-set fetch, and starvation workloads.

The next performance work should therefore focus on general execution throughput and reducing code-fetch refill/boundary cost, not merely increasing the already-strong TW benefit.

## 4. Sensitivity results

### CS pool capacity

Single-core, 8,192-operation sequential code-stream test. Only CS capacity changes.

| CS capacity | Total cycles |
|---:|---:|
| 4 KiB | 5,282 |
| 8 KiB | 5,202 |
| 16 KiB | 5,042 |
| 32 KiB | 4,722 |
| 64 KiB | 4,145 |

The 64 KiB case is approximately **21.5% lower in cycles than the 4 KiB case**. This is a capacity sensitivity result, not a recommendation to replace the current 8 × 2 KiB slot organization without area/latency analysis.

### Branch predictor sensitivity

The compact predictor reduces the deterministic misprediction count for predictable control cases, but this sweep does not show a cycle reduction in the tested kernels. The branch-stress workload remains at 136 mispredictions in both modes because its modeled branch stream is intentionally unpredictable (50% assumed rate). This confirms that predictor capacity alone does not solve an unpredictable branch stream.

## 5. Concurrent CodeFlow pipeline status

The standalone pipeline model now schedules the three transfer stages independently:

`App RAM → C0 → CS → EB`

It has separate bounded queues, queue high-water marks, stage busy-cycle counters, and backpressure counters. The regression suite verifies that stages overlap in time, that queue capacities are respected, and that the overlapped completion time is below the sum of the three stages' service times for the test stream.

**Important boundary:** this concurrent pipeline is currently a standalone event-level model. The main cross-architecture CPU simulator's integrated instruction-fetch path has not yet been replaced by this full concurrent scheduler. Therefore the normalized CPU table above must not be read as already including the full overlap benefit.

## 6. Model assumptions and limitations

- This is a deterministic cycle/event-level design-space model, not RTL, gem5, silicon, or a vendor-certified microarchitecture replica.
- Reference CPU profiles are approximations; vendor-private cache, predictor, scheduling, and execution details are not fully modeled.
- Apple M6 is represented by a weighted homogeneous approximation.
- The normalized run configures eight active cores for every profile and preserves the same logical operation count.
- NEXSUS uses the proposed 64 B/cycle aggregate DRAM bandwidth in this profile; reference profiles use their configured aggregate bandwidth assumptions.
- Cache coherence and several OS/workspace details remain abstracted.
- NEXSUS clock and transfer parameters are model inputs, not measured physical limits.

## 7. Next engineering steps

1. Integrate the concurrent C0 → CS → EB scheduler into the main CPU fetch model without changing the 64-bit App RAM read lane.
2. Add stage-level queue, occupancy, overlap, and backpressure metrics to the normalized cross-architecture report.
3. Re-run the full kernel matrix with the integrated scheduler and compare it against both the current serial approximation and conventional I-cache profiles.
4. Tune general integer/FPU/vector issue throughput and the CS sequential/working-set refill path.
5. Keep every comparison operation-count-equivalent and publish the assumptions beside each result.
