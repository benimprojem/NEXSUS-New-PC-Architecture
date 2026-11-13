# NEXSUS CPU — Full Architecture Benchmark and Comparative Workload

**Document ID:** NEXSUS-CPU-FULL-ARCHITECTURE-BENCHMARK-001  
**Status:** Benchmark specification; execution and calibration are separate milestones  
**Purpose:** One reproducible workload suite to compare NEXSUS against three conventional CPU core profiles, including the PX-fed double-bank SPM0 design.

## 1. Comparison targets

The first controlled comparison uses four architecture profiles, each configured as an 8-core homogeneous run:

| ID | Architecture profile | Controlled core count | Role |
|---|---|---:|---|
| AMD-Z5 | AMD Zen 5 / Ryzen 9 9950X Zen 5 core profile | 8 | Modern high-performance x86 reference |
| INTEL-P | Intel Arrow Lake Lion Cove P-core profile | 8 | Modern high-performance hybrid x86 P-core reference |
| INTEL-E | Intel Arrow Lake Skymont E-core profile | 8 | Modern efficiency-oriented x86 E-core reference |
| NEXSUS | Current NEXSUS CPU proposal | 8 | Candidate architecture under test |

The three reference profiles must remain separate. Do not average Intel P and E results. This controlled phase uses the same number of active cores and one hardware thread per core; SMT is disabled unless a separate explicitly labeled experiment enables it.

These are architectural simulation profiles, not cycle-accurate replicas of commercial silicon. Publicly documented or measured parameters must be distinguished from inferred assumptions. Each uncertain parameter receives low/base/high sensitivity values.

## 2. Fairness and workload contract

All targets receive:
- identical input data, seeds, task graph, output requirements, and synchronization;
- identical algorithmic operation graph and numerical precision;
- equivalent working-set sizes and memory-residency conditions;
- identical completion and correctness checks;
- disclosed compiler/backend transformations and instruction/operation counts.

A backend may map an operation to its legal scalar, SIMD, vector, or fused implementation. Such transformations must be counted and reported. Do not force a scalar implementation on a reference CPU when it has a legal vector path. Do not grant NEXSUS free data movement or unmodeled memory bandwidth.

The comparison has two modes:
1. **Architecture-neutral mode:** same operation graph and same input/output behavior, allowing each backend to use its native execution resources.
2. **Instruction/feature ablation mode:** turn one feature on/off while holding all other parameters constant, isolating the feature's contribution.

## 3. Master workload algorithm

Use one deterministic mixed workload composed of independently measurable kernels. The master job creates a fixed data set and task graph, runs every kernel, validates outputs, and records a common event stream.

### 3.1 Workload phases

1. Generate input arrays, matrices, pointer graph, task descriptors, and fixed random seeds.
2. Run scalar integer control and dependency chains.
3. Run independent integer throughput operations.
4. Run floating-point and vector transforms.
5. Run tiled matrix multiplication with explicit data reuse.
6. Run sequential streaming read-transform-write.
7. Run strided and random pointer-graph traversal.
8. Run mixed compute plus memory traffic.
9. Run producer/consumer tasks across cores.
10. Run task-switch stress with both warm and cold contexts.
11. Run IRQ/exception injection at deterministic operation points.
12. Run bulk memory transfer and synchronization.
13. Run mixed multi-task load with priority, fairness, and deadline classes.
14. Validate all outputs and emit per-kernel and aggregate reports.

The input generator must be deterministic. Each kernel has a small reference implementation or mathematical oracle independent of the CPU timing model.

## 4. Kernel suite

| ID | Kernel | Core behavior | Primary measurements |
|---|---|---|---|
| K01 | Scalar dependency chain | Serial integer recurrence | Dependency latency, ALU issue, front-end stalls |
| K02 | Integer throughput | Independent integer operations | ALU throughput and issue width |
| K03 | Branch stress | Predictable and unpredictable branches | Prediction accuracy, recovery penalty |
| K04 | FP scalar/vector | FP reductions and transforms | FP latency/throughput, vector mapping |
| K05 | Vector transform | 256/512-bit logical vector operations | SIMD/ME512 utilization, register pressure |
| K06 | Matrix tile | Tiled matrix multiplication | Compute throughput, reuse, load/store pressure |
| K07 | Sequential stream | Large sequential read-transform-write | Bandwidth, cache-line efficiency, write turnaround |
| K08 | Strided/random memory | Pointer graph and irregular access | Latency, bank conflicts, miss concurrency |
| K09 | Mixed compute-memory | Interleaved ALU/FP/memory operations | Overlap and bottleneck migration |
| K10 | Producer-consumer | Cross-core queues and synchronization | Coherence/visibility, inter-core latency |
| K11 | Task-switch stress | Many runnable tasks and frequent preemption | Context save/restore, SPM hit/spill, switch latency |
| K12 | IRQ/exception stress | Deterministic IRQ and fault injection | Interrupt latency, frame overhead, recovery |
| K13 | Bulk transfer | Large memory copy / MEMXFER-like workload | Transfer throughput, arbitration, CPU offload |
| K14 | Mixed system load | Concurrent compute, memory, tasks and events | Aggregate throughput, fairness, tail latency |
| K15 | Instruction-fetch stress | Small loops, large code, page boundaries and partial final pages | Front-end starvation, PX refill, SPM0 bank switching |

## 5. NEXSUS PX/SPM0-specific experiment

The current NEXSUS code path is modeled as:
- PX P0–P7: eight equal 2 KiB physical code-pool slots (16 KiB/core);
- SPM0: 4 KiB total, split into SPM0-A and SPM0-B, each 2 KiB;
- PX Manager fills the inactive SPM0 bank while CPU fetch consumes the active bank;
- full 2 KiB logical pages continue automatically;
- PX_NEXT and PX_END are PX Manager metadata only, not instructions and not copied into SPM0;
- PX_NEXT marks a partial intermediate code page; PX_END marks the partial final page;
- task data and RA/FA/DA/MA register images never enter SPM0 through PX.

### 5.1 PX/SPM0 ablation profiles

| Profile | Configuration | Question |
|---|---|---|
| PX-A | Single 2 KiB active code workspace, no overlap | Historical baseline |
| PX-B | 4 KiB SPM0 dual-bank, refill only after switch | Benefit of larger workspace alone |
| PX-C | 4 KiB dual-bank, one-page lookahead | Benefit of overlapped refill |
| PX-D | PX-C plus partial-page metadata | Correctness and efficiency for non-2-KiB code lengths |
| PX-E | PX-D under multi-task refill contention | Robustness under realistic competing demand |

These are NEXSUS internal ablations, not separate competitor architectures. Report them beside the four main architecture profiles.

### 5.2 Page-boundary test vectors

For every instruction-fetch test, include code lengths and boundary placements such as:
- 8 B, 2 KiB−8 B, exactly 2 KiB;
- 2 KiB+8 B, 4 KiB−8 B, exactly 4 KiB;
- 4 KiB+8 B, 4 KiB+partial-page;
- multiple full pages followed by a partial final page;
- partial intermediate page terminated by PX_NEXT followed by another page;
- partial final page terminated by PX_END;
- malformed, misaligned, stale-generation, and missing-continuation metadata.

Check that no marker bytes are counted as instructions, no padding is executed, no valid instruction is skipped or duplicated, and the logical PC remains correct across bank switches.

## 6. Timing model requirements

The cycle model must include, per target:
- fetch/decode/dispatch/issue/retire widths;
- dependency tracking and in-flight window;
- integer, FP, and vector pipeline count/latency/throughput;
- branch predictor and recovery penalty;
- load/store queues and memory ports;
- cache hierarchy, capacities, line sizes, latencies, and replacement policy;
- DRAM bandwidth, latency, bank count, queue depth, and arbitration;
- inter-core communication/coherence assumptions;
- task scheduling, context transfer, and interrupt handling.

NEXSUS-specific modeled resources include:
- 32-entry RA, FA, DA, and MA banks with their defined widths;
- 2 ALUs, 2 FPUs and one ME512/core as the current proposal;
- 4 KiB dual-bank SPM0;
- P0–P7 shared PX pool;
- SPM1–SPM7 roles and permissions;
- separate App RAM and Data RAM paths;
- proposed L1/L2/L3/L4 organization;
- task context residency and Data-RAM spill path.

The NEXSUS App-RAM refill target currently considered is 64 B/cycle. Reference profiles must use their own configured memory interfaces. Do not force equal bandwidth if the purpose is to compare the proposed systems; instead publish both native-profile results and a normalized-bandwidth sensitivity run.

For PX refill, model payload transfer, source latency, queueing, arbitration, bank-switch overhead, and contention separately. The ideal payload-only time for 2 KiB at 64 B/cycle is 32 cycles; this is not a guaranteed end-to-end refill time.

## 7. Metrics

Report every kernel separately and aggregate only after showing the component results.

### Performance
- total cycles and modeled time;
- operations/instructions completed, IPC, throughput;
- single-task latency and multi-task throughput;
- speedup against each reference profile;
- per-core utilization and execution-unit utilization.

### Front-end and PX/SPM0
- instruction-fetch stall cycles;
- PX pool hit/miss and refill bytes;
- SPM0 bank-switch count and switch bubbles;
- percentage of bank boundaries READY on time;
- refill overlap ratio and effective useful-byte bandwidth;
- useful bytes versus wasted bytes transferred;
- partial-page and metadata-fault counts.

### Memory
- bytes read/written at every modeled level;
- cache hit/miss rates;
- DRAM requests, bank conflicts, queue delay, and bandwidth utilization;
- load/store queue stalls and memory-level parallelism.

### Scheduling and system behavior
- task-switch count and latency distribution (mean, median, P95, P99);
- context SPM hit rate and Data-RAM spill rate;
- IRQ arrival-to-handler and handler-to-return latency;
- fairness, per-task wait time, starvation, and deadline misses.

### Correctness
- output hash/reference equality;
- numeric error within declared tolerance;
- no lost/duplicated operations;
- no invalid fetch, stale mapping, partial context, or permission violation.

Energy/power metrics are excluded until operation-level and memory-level energy parameters are calibrated. Uncalibrated energy estimates must not be presented as measured power.

## 8. Simulation algorithm (pseudocode)

```text
for architecture in [AMD_ZEN5, INTEL_ARROW_LAKE_P, INTEL_ARROW_LAKE_E, NEXSUS]:
    for scenario in configured_sensitivity_scenarios:
        cpu = build_cpu_model(architecture, scenario)
        for kernel in MASTER_WORKLOAD_SUITE:
            input = deterministic_input(kernel.seed)
            oracle = run_reference_oracle(kernel, input)
            graph = build_architecture_neutral_operation_graph(kernel, input)
            trace = cpu.backend_lower(graph)
            result = cpu.timing_engine.execute(trace)
            assert validate(result.output, oracle, kernel.tolerance)
            record(kernel, architecture, scenario, result.metrics, result.events)

run_nexsus_px_spm0_ablations(PX_A, PX_B, PX_C, PX_D, PX_E)
run_correctness_and_fault_injection_suite()
run_fairness_and_contention_suite()
emit_raw_csv_json_event_logs_and_summary_tables()
```

The functional model must validate outputs independently from the timing engine. Timing may change with a parameter sweep; functional results must not.

## 9. Required test matrix

At minimum, run:
- four architecture profiles × all 15 kernels;
- low/base/high sensitivity for unresolved parameters;
- cold-cache and warm-cache variants where relevant;
- single-core and 8-core variants;
- native bandwidth and normalized-bandwidth comparisons;
- NEXSUS PX-A through PX-E ablations;
- context-resident and context-spilled task-switch cases;
- low, medium, and high task-arrival pressure;
- branch-predictable and branch-randomized cases;
- code working sets below, at, and above PX capacity.

## 10. Validation gates

A result is publishable only when:
1. all architecture backends pass functional correctness;
2. deterministic seeds reproduce the same event traces;
3. no request or operation is lost or duplicated;
4. no partial page or context becomes visible as valid;
5. no illegal permission, ownership, or generation bypass occurs;
6. fairness tests meet their declared policy bounds;
7. all timing assumptions and profile parameters are included with the report.

A failed gate blocks comparative speedup claims for the affected workload.

## 11. Output artifacts

Each benchmark run produces:
- machine-readable configuration snapshot;
- workload and input seed manifest;
- per-kernel CSV metrics;
- event trace JSONL;
- correctness report;
- sensitivity/ablation tables;
- human-readable Markdown summary;
- plots generated from raw metrics.

Every report must label results as simulated, measured, or assumed. Never describe behavioral simulation output as physical silicon performance.

## 12. Implementation sequence

1. Update the existing simulator's NEXSUS configuration to 4 KiB dual-bank SPM0 and the PX P0–P7 pool.
2. Add PX metadata parsing and page-boundary correctness tests.
3. Add the cycle-level active-bank/inactive-bank refill engine.
4. Add instruction-fetch stress kernel K15 and PX metrics.
5. Integrate the existing AMD Zen 5, Intel P-core, and Intel E-core profiles into the same runner.
6. Run all four profiles on the shared workload suite.
7. Add ablations, sensitivity sweeps, and correctness/fault injection.
8. Publish results only after all validation gates pass.

## 13. Open parameters

The following are intentionally not frozen:
- exact SPM0 bank-switch latency and fetch granularity;
- PX pool-to-SPM0 transfer path bandwidth and arbitration;
- App-RAM source latency and contention;
- PX lookahead depth and refill queue policy;
- reference pipeline/cache/memory parameters where public measurements are unavailable;
- exact branch, exception, and context transfer cycle costs.

These parameters must remain configurable and visible in every result.
