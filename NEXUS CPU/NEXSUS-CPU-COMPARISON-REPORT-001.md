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

## 7. Vector and ME512 arithmetic model update — 2026-11-16

The earlier `vector_throughput` stream represented generic 512-bit logical vector issue, while `me512_matrix` used one opaque accelerator operation per tile. Those kernels were insufficient to identify arithmetic-class and matrix-accumulation behavior.

The diagnostic workload has now been expanded:

- Vector issue classes: `VEC_ADD`, `VEC_MUL`, `VEC_FMA`, and `VEC_PERMUTE`, each modeled as a 512-bit operation and routed through the same VEC issue resource.
- The aggregate vector stream interleaves all four classes; individual per-class streams are also emitted.
- ME512 matrix work uses 16 output tiles, each with eight K-steps. Every K-step loads one A and one B tile and issues one dependent ME512 tile multiply-accumulate; the accumulated result is stored once per output tile.
- The same logical operation graph is used across NEXSUS, AMD, Intel, and Apple profiles. Reference profiles map the ME512-equivalent operation to their configured matrix/vector resource.

This remains an execution/issue timing model, not a numerical datapath simulator: vector opcodes currently share the profile's generic VEC latency, and ME512 MAC is one modeled tile operation. Arithmetic precision, lane-level element count, saturation/rounding, shuffle semantics, tile dimensions, accumulator format, operand banking, and numerical output validation remain open modeling work. The prior 66-cycle vector and 420-cycle ME512 results belong to the older generic/opaque workload and must not be treated as directly comparable with the expanded kernels.

Regression tests for opcode-to-resource mapping, 512-bit operation width, tiled accumulation dependencies, and cross-profile retirement pass in the latest test step. Full comparison CI is still running; new cycle results will be recorded only after its comparison output is available.

## 8. Separating backend arithmetic from instruction delivery — 2026-11-16

The first expanded VEC/ME512 run exposed a measurement confound. In the NEXSUS eight-core composite run, each isolated VEC opcode reported 826 cycles, while CodeFlow reported 4,744 aggregate wait cycles and 4,744 boundary-wait cycles. These values show that instruction delivery materially affects the observed kernel completion time; they do not establish the intrinsic VEC issue rate.

A new `--vec-me512-isolation` experiment has been added. It runs the same logical VEC and ME512 kernels on all four profiles at eight cores, first with normal instruction delivery and then with only instruction-fetch readiness bypassed. Per-core dispatch/issue limits, execution-unit counts, dependencies, Data RAM/cache timing, and retirement remain enabled. The second result is explicitly a backend-isolation upper bound, not a complete CPU performance result.

CI checks that operation counts remain identical and that isolated runs have zero instruction-fetch wait. The resulting artifact will be used to separate:
1. instruction delivery and frontend starvation;
2. vector/matrix execution-unit issue and dependency behavior;
3. data operand and result movement.

No VEC or ME512 unit-count change is authorized by the earlier 826-cycle result. The new isolation sweep must complete before drawing throughput conclusions.


### 8.1 First measured VEC / ME512 isolation results — CI 43792221933

The isolation sweep completed successfully on all four profiles with eight configured cores and identical logical operation counts. The full JSON is preserved in the `nexus-cpu-comparison-results` workflow artifact as `nexus-vec-me512-isolation.json`.

**NEXSUS VEC results (128 operations per opcode):**

| Kernel | Normal delivery | Fetch-bypassed backend | Normal fetch wait | Backend issue span |
|---|---:|---:|---:|---:|
| VEC_ADD | 826 cycles | 10 cycles | 4,744 | 8 cycles |
| VEC_SUB | 826 cycles | 10 cycles | 4,744 | 8 cycles |
| VEC_MUL | 826 cycles | 10 cycles | 4,744 | 8 cycles |
| VEC_FMA | 826 cycles | 10 cycles | 4,744 | 8 cycles |
| VEC_PERMUTE | 826 cycles | 10 cycles | 4,744 | 8 cycles |
| VEC_REDUCE | 826 cycles | 10 cycles | 4,744 | 8 cycles |
| Mixed vector throughput (256 ops) | 834 cycles | 18 cycles | 4,744 | 16 cycles |

The 10-cycle backend completion for 128 independent vector operations is consistent with the fixed two-VEC-unit-per-core topology across eight cores (16 aggregate issue slots/cycle), plus completion/retirement overhead. It does **not** measure dependent-chain latency. All six opcodes currently share the same generic VEC latency, so the equal values are expected and cannot justify opcode-specific latency claims.

For context, fetch-bypassed per-opcode completion was 11 cycles on AMD, 11 on Intel, and 16 on Apple in their current modeled profiles. These are simulator outputs, not silicon measurements.

**ME512 matrix workload:**

| Profile | Normal delivery | Fetch-bypassed backend | Backend issue span | Backend dependency-blocked op-cycles | Backend memory-latency exposure |
|---|---:|---:|---:|---:|---:|
| AMD 9950X3D2 model | 1,059 | 1,027 | 904 | 76,639 | 133,525 |
| Intel Xeon 698X model | 590 | 558 | 408 | 40,288 | 72,279 |
| Apple M6 model | 588 | 556 | 455 | 40,116 | 70,387 |
| NEXSUS Balanced 128 | 1,107 | 504 | 384 | 36,676 | 64,544 |

ME512's tiled workload contains operand loads, a dependent accumulator chain for each tile, and a result store. The remaining backend cost is therefore a mixture of operand delivery, memory service, and accumulator dependencies; it is not a pure ME512 arithmetic latency measurement. The bypassed mode changes when operations become eligible and consequently changes overlap/counter totals. Treat its cycle result as a controlled fetch-bypass run, not as a mathematically isolated arithmetic-unit latency.

**Next measurement refinement:** add separate operand-resident ME512 independent-throughput and dependent-accumulator-chain kernels, plus equivalent VEC dependency-chain kernels. Keep the existing tiled load/MAC/store workload as the end-to-end operand-feed case. This will separate (1) unit issue capacity, (2) result-forwarding latency, and (3) Data RAM/operand-feed pressure without changing the fixed VEC=2 or ME512=1 resource counts.


### 8.2 Operand-resident latency and mixed-resource validation — 2026-11-16

CI run [43793155027](https://github.com/benimprojem/NEXSUS-New-PC-Architecture/actions/runs/43793155027) passed all steps. Its artifact adds independent and dependent VEC/ME512 kernels. The following backend-isolation cycle counts are simulator results for eight configured cores:

| Profile | VEC dependent chain (64 ops) | Configured VEC latency | ME512 independent (128 ops) | ME512 dependent chain (128 ops) | Configured matrix-resource latency |
|---|---:|---:|---:|---:|---:|
| AMD 9950X3D2 model | 193 cycles | 3 | 11 cycles | 385 cycles | 3 (ME512 maps to VEC) |
| Intel Xeon 698X model | 193 cycles | 3 | 18 cycles | 257 cycles | 2 (ME512 maps to AMX) |
| Apple M6 model | 513 cycles | 8 (2 × 512/128 width factor) | 16 cycles | 1,025 cycles | 8 (ME512 maps to VEC) |
| NEXSUS Balanced 128 | 129 cycles | 2 | 20 cycles | 513 cycles | 4 |

**Interpretation limitation:** the dependent-chain results reproduce the latency values already configured in each simulator profile (plus pipeline/retirement boundary overhead). They validate that dependency readiness and completion timing honor those assumptions; they do not independently discover or prove the physical unit latencies. Likewise, independent-stream completion validates modeled issue capacity across eight cores, not silicon throughput. The VEC opcodes still share a common VEC latency assumption; no opcode-specific latency is established.

For NEXSUS, 128 independent VEC operations complete in 10 cycles, while 128 independent ME512 operations complete in 20 cycles. This is consistent with two VEC issue slots per core versus one ME512 slot per core, over eight cores. It is a useful topology sanity check, not a final performance claim.

**Next experiment:** the mixed `vec_me512_memory_overlap` kernel interleaves VEC arithmetic, ME512 MACs, Data RAM loads and stores in one stream. Its purpose is to verify that the separate execution resources and memory subsystem make progress concurrently, preserve all operations, and expose contention/stall counters. The experiment does not change the fixed resource counts.

### 8.3 Collaboration-scope cache residency — 2026-11-16

The cache hierarchy is not only a latency ladder. Each level is also the natural shared working-set home for a particular collaboration width:

| Collaborating cores | Working-set home |
|---|---|
| 1 | Private L1 |
| 2 | Pair-shared L2 |
| 3–4 | Four-core shared L3 |
| 5–8 | Eight-core shared L4 |
| More than 8 | Separate L4 homes per eight-core group; cross-group sharing is not implicit |

The simulator now supports an untimed, exact-level working-set prefill. It inserts each line once per distinct cache object at the selected home level; it does not replicate an L4-resident group working set into every private L1. Demand accesses then follow the normal probe path, and completed demand fills may populate lower levels according to the current inclusive-fill model.

The eight-core VEC/ME512 cache-resident sweep now homes its working set in shared L4. Regression coverage verifies that a prefilled line is visible at L1 only to its owner core, at L2 to its two-core pair, at L3 to its four-core group, and at L4 to its eight-core group—but not to the next group. This validates modeled sharing and placement, not cache bandwidth, coherence, or physical silicon timing.

The mixed kernel also has true data dependencies: LOAD feeds both VEC and ME512, and STORE waits for both results. The cold and cache-resident cases expose operand-feed delay without confusing independent arithmetic with unrelated memory traffic. The completed CI artifact provides the measurements in section 8.4.

---

## 8.4 Mixed VEC + ME512 + memory: cold versus cache-resident — CI 43796038337

CI [43796038337](https://github.com/benimprojem/NEXUS-New-PC-Architecture/actions/runs/43796038337) passed all regression, comparison, VEC/ME512 isolation, cross-architecture, and CodeFlow steps. The artifact's mixed kernel preserves 448 logical operations (128 VEC, 128 ME512, 128 LOAD, 64 STORE); the 192 memory operations are unchanged between paths. NEXSUS uses its eight-core L4 home; reference profiles use their modeled L3 home.

| Profile | Cold DRAM path | Cache-resident path | DRAM accesses (cold → resident) | Shared-home accesses (resident) |
|---|---:|---:|---:|---:|
| AMD 9950X3D2 model | 738 cycles | 114 cycles | 192 → 0 | 192 L3 |
| Intel Xeon 698X model | 462 cycles | 137 cycles | 192 → 0 | 192 L3 |
| Apple M6 model | 411 cycles | 95 cycles | 192 → 0 | 192 L3 |
| NEXSUS Balanced 128 | 1,078 cycles | 147 cycles | 192 → 0 | 192 L4 |

In this modeled workload, exact-level working-set prefill removes the 192 DRAM accesses and moves the data requests to the collaboration group's shared cache home. NEXSUS cold-to-resident completion changes from 1,078 to 147 cycles; this is a simulator workload result, **not** a silicon speedup claim or an isolated cache-latency measurement. The kernel still includes dependency stalls, execution-resource contention, memory/cache service, instruction delivery, and retirement. Reference CPU cache organizations are approximations and are not architecturally equivalent to NEXSUS L2/L3/L4 sharing.

**Next cache validation:** test home-level capacity/eviction and access visibility across group boundaries, then add explicit cache hit/miss latency and bandwidth/port models only after the relevant policy parameters are chosen. Coherence and cross-group transfer remain unmodeled.

## 9. Next engineering steps

1. Integrate the concurrent C0 → CS → EB scheduler into the main CPU fetch model without changing the 64-bit App RAM read lane.
2. Add stage-level queue, occupancy, overlap, and backpressure metrics to the normalized cross-architecture report.
3. Re-run the full kernel matrix with the integrated scheduler and compare it against both the current serial approximation and conventional I-cache profiles.
4. Tune general integer/FPU/vector issue throughput and the CS sequential/working-set refill path.
5. Keep every comparison operation-count-equivalent and publish the assumptions beside each result.
